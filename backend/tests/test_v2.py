import io
import json
import os
import tempfile
import uuid

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.main import app
from app.services import connectors as connector_svc
from app.services import drift as drift_svc

client = TestClient(app)

CSV = "age,income,name\n30,50000,alice\nNone,60000,bob\n40,55000,carol\n30,50000,alice\n"


# --------------------------------------------------------------------------
# Security primitives (stdlib-only)
# --------------------------------------------------------------------------
def test_password_hashing():
    h = security.hash_password("supersecret")
    assert security.verify_password("supersecret", h)
    assert not security.verify_password("wrong", h)


def test_jwt_roundtrip():
    tok = security.encode_jwt({"sub": "123", "email": "a@b.com"})
    payload = security.decode_jwt(tok)
    assert payload["sub"] == "123"
    with pytest.raises(security.JWTError):
        security.decode_jwt(tok + "x")


def test_api_key_hashing():
    _, full = security.generate_api_key()
    h = security.hash_api_key(full)
    assert security.verify_api_key(full, h)
    assert not security.verify_api_key("dsk_wrong", h)


# --------------------------------------------------------------------------
# Connectors
# --------------------------------------------------------------------------
def test_local_connector_pull():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "data.csv")
    with open(p, "w") as f:
        f.write(CSV)
    c = connector_svc.build_connector("local", {"path": p})
    data, name = c.pull()
    assert b"age" in data
    assert name == "data.csv"


def test_local_connector_directory():
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "a.csv"), "w") as f:
        f.write(CSV)
    c = connector_svc.build_connector("local", {"path": d})
    assert c.test() is True


def test_redact_config_masks_secrets():
    cfg = {"host": "db", "password": "hunter2", "user": "u"}
    red = connector_svc.redact_config(cfg)
    assert red["password"] == "********"
    assert red["host"] == "db"


# --------------------------------------------------------------------------
# Drift detection
# --------------------------------------------------------------------------
def test_drift_same_data_is_stable():
    df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "c": ["a", "b", "a", "b", "a"]})
    report = drift_svc.compare_dataframes(df, df.copy())
    assert report["status"] == "STABLE"
    assert report["max_drift"] == 0.0


def test_drift_detects_shift():
    base = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] * 10})
    shifted = pd.DataFrame({"x": [50, 60, 70, 80, 90, 100, 110, 120, 130, 140] * 10})
    report = drift_svc.compare_dataframes(base, shifted)
    assert report["max_drift"] > 0.2
    assert report["status"] in ("WARNING", "ALERT")


def test_categorical_drift():
    a = pd.Series(["a"] * 90 + ["b"] * 10)
    b = pd.Series(["a"] * 10 + ["b"] * 90)
    assert drift_svc.categorical_drift(a, b) > 0.5


# --------------------------------------------------------------------------
# Auth API flow
# --------------------------------------------------------------------------
def _register():
    email = f"user_{uuid.uuid4().hex[:10]}@example.com"
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "U"},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"], email


def test_register_login_me():
    tok, email = _register()
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200
    assert me.json()["email"] == email

    # duplicate email
    dup = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    assert dup.status_code == 409

    # bad login
    bad = client.post("/api/v1/auth/login", json={"email": email, "password": "nope"})
    assert bad.status_code == 401


def test_api_key_lifecycle():
    tok, _ = _register()
    created = client.post(
        "/api/v1/auth/api-keys",
        json={"name": "ci", "scopes": ["datasets:read", "datasets:write", "drift:read"]},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert created.status_code == 201
    full = created.json()["full_key"]
    assert full.startswith("dsk_")
    listing = client.get("/api/v1/auth/api-keys", headers={"Authorization": f"Bearer {tok}"})
    assert len(listing.json()) == 1
    # the stored key must NOT expose the secret after creation
    assert listing.json()[0].get("full_key") is None


# --------------------------------------------------------------------------
# Drift + Monitoring API (authenticated, owned dataset via public upload)
# --------------------------------------------------------------------------
def _owned_dataset(token=None, api_key=None):
    if api_key:
        res = client.post(
            "/api/v1/public/upload",
            files={"file": ("people.csv", CSV.encode(), "text/csv")},
            headers={"X-API-Key": api_key},
        )
    else:
        res = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("people.csv", CSV.encode(), "text/csv")},
        )
    assert res.status_code == 200, res.text
    return res.json()["dataset_id"]


def _auth_header():
    return {"Authorization": f"Bearer {_register()[0]}"}


def test_drift_snapshot_and_compare():
    hdr = _auth_header()
    ds_id = _owned_dataset()
    s1 = client.post(f"/api/v1/drift/snapshots?dataset_id={ds_id}", headers=hdr)
    assert s1.status_code == 201, s1.text
    s1_id = s1.json()["id"]
    s2 = client.post(f"/api/v1/drift/snapshots?dataset_id={ds_id}", headers=hdr)
    s2_id = s2.json()["id"]
    comp = client.post(
        "/api/v1/drift/compare",
        json={"baseline_id": s1_id, "current_id": s2_id},
        headers=hdr,
    )
    assert comp.status_code == 200, comp.text
    assert comp.json()["status"] == "STABLE"


def test_monitor_run_now():
    hdr = _auth_header()
    ds_id = _owned_dataset()
    sched = client.post(
        "/api/v1/monitors",
        json={"name": "nightly", "source_type": "dataset", "source_id": ds_id, "cadence_minutes": 1440},
        headers=hdr,
    )
    assert sched.status_code == 201, sched.text
    sched_id = sched.json()["id"]
    run = client.post(f"/api/v1/monitors/{sched_id}/run", headers=hdr)
    assert run.status_code == 200, run.text
    # eager mode -> run already completed
    runs = client.get(f"/api/v1/monitors/{sched_id}/runs", headers=hdr).json()
    assert runs[0]["status"] == "READY"
    assert runs[0]["drift_status"] == "STABLE"


def test_connector_create_and_ingest():
    hdr = _auth_header()
    d = tempfile.mkdtemp()
    p = os.path.join(d, "src.csv")
    with open(p, "w") as f:
        f.write(CSV)
    c = client.post(
        "/api/v1/connectors",
        json={"name": "local-src", "type": "local", "config": {"path": p}},
        headers=hdr,
    )
    assert c.status_code == 201, c.text
    cid = c.json()["id"]
    # secrets must be redacted in responses
    assert c.json()["config"].get("path") == p  # path is not a secret key
    test = client.post(f"/api/v1/connectors/{cid}/test", headers=hdr)
    assert test.json()["ok"] is True
    ingest = client.post(f"/api/v1/connectors/{cid}/ingest", headers=hdr)
    assert ingest.status_code == 200, ingest.text
    assert ingest.json()["dataset_id"]


# --------------------------------------------------------------------------
# Training (sklearn optional)
# --------------------------------------------------------------------------
def test_training_pipeline():
    try:
        import sklearn  # noqa: F401
    except ImportError:
        pytest.skip("scikit-learn not installed")
    hdr = _auth_header()
    rows = [f"{i%5},{i%3},{i%2}" for i in range(60)]
    train_csv = "f1,f2,target\n" + "\n".join(rows) + "\n"
    ds_id = _owned_dataset()
    # overwrite raw with a trainable file via public upload path is heavier; instead use connector
    d = tempfile.mkdtemp()
    p = os.path.join(d, "train.csv")
    with open(p, "w") as f:
        f.write(train_csv)
    c = client.post(
        "/api/v1/connectors",
        json={"name": "train-src", "type": "local", "config": {"path": p}},
        headers=hdr,
    )
    cid = c.json()["id"]
    job = client.post(
        "/api/v1/training",
        json={"target": "target", "task": "classification", "source_type": "connector", "source_id": cid},
        headers=hdr,
    )
    assert job.status_code == 201, job.text
    jid = job.json()["id"]
    got = client.get(f"/api/v1/training/{jid}", headers=hdr).json()
    assert got["status"] == "READY", got
    assert got["metrics"]["accuracy"] >= 0.0
    assert "target" in got["feature_importances"] or len(got["feature_importances"]) >= 1


# --------------------------------------------------------------------------
# Public API (API-key auth + scopes)
# --------------------------------------------------------------------------
def test_public_api_key_auth():
    tok, _ = _register()
    created = client.post(
        "/api/v1/auth/api-keys",
        json={"name": "ext", "scopes": ["datasets:read", "datasets:write", "drift:read"]},
        headers={"Authorization": f"Bearer {tok}"},
    )
    api_key = created.json()["full_key"]

    # missing key -> 401
    no_key = client.post(
        "/api/v1/public/upload",
        files={"file": ("p.csv", CSV.encode(), "text/csv")},
    )
    assert no_key.status_code == 401

    # valid key -> upload + read
    up = client.post(
        "/api/v1/public/upload",
        files={"file": ("p.csv", CSV.encode(), "text/csv")},
        headers={"X-API-Key": api_key},
    )
    assert up.status_code == 200, up.text
    ds_id = up.json()["id"]
    prof = client.get(f"/api/v1/public/datasets/{ds_id}/profile", headers={"X-API-Key": api_key})
    assert prof.status_code == 200
    assert prof.json()["row_count"] == 4
