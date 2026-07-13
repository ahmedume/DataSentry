import uuid

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)

CSV = "age,income,name\n30,50000,alice\nNone,60000,bob\n40,55000,carol\n"


def _reg():
    email = f"u_{uuid.uuid4().hex[:10]}@example.com"
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "U"},
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    uid = me.json()["id"]
    return token, uid, email  # noqa: E501


def _owned_dataset(token):
    res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("people.csv", CSV.encode(), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    return res.json()["dataset_id"]


def _make_admin(token):
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    uid = me.json()["id"]
    db = SessionLocal()
    try:
        from app.db.models import User

        u = db.query(User).filter(User.id == uuid.UUID(uid)).first()
        u.is_admin = True
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# v3 — Teams & RBAC
# ---------------------------------------------------------------------------
def test_team_lifecycle_and_rbac():
    tok_a, uid_a, _ = _reg()
    tok_b, uid_b, email_b = _reg()

    r = client.post("/api/v1/teams", json={"name": "ACME"}, headers={"Authorization": f"Bearer {tok_a}"})
    assert r.status_code == 201, r.text
    team_id = r.json()["id"]

    # B is not a member -> cannot see the team
    mine = client.get("/api/v1/teams", headers={"Authorization": f"Bearer {tok_b}"})
    assert all(t["id"] != team_id for t in mine.json())

    hdr = {"Authorization": f"Bearer {tok_a}", "X-Team-Id": team_id}

    # A adds B as a viewer
    r = client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"email": email_b, "role": "viewer"},
        headers=hdr,
    )
    assert r.status_code == 201, r.text

    # B (viewer) cannot manage membership
    r = client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"email": email_b, "role": "admin"},
        headers={"Authorization": f"Bearer {tok_b}", "X-Team-Id": team_id},
    )
    assert r.status_code == 403, r.text

    # B now sees the team
    mine = client.get("/api/v1/teams", headers={"Authorization": f"Bearer {tok_b}"})
    assert any(t["id"] == team_id for t in mine.json())

    # A removes B
    r = client.delete(
        f"/api/v1/teams/{team_id}/members/{uid_b}",
        headers=hdr,
    )
    assert r.status_code == 204, r.text


def test_annotation_forbidden_on_others_dataset():
    tok_a, _, _ = _reg()
    tok_b, _, _ = _reg()
    ds_id = _owned_dataset(tok_a)

    r = client.post(
        f"/api/v1/datasets/{ds_id}/annotations",
        json={"body": "mine", "column_name": "age"},
        headers={"Authorization": f"Bearer {tok_b}"},
    )
    assert r.status_code == 403, r.text


# ---------------------------------------------------------------------------
# v3 — Annotations (dataset-scoped)
# ---------------------------------------------------------------------------
def test_annotation_crud():
    tok, _, _ = _reg()
    ds_id = _owned_dataset(tok)
    h = {"Authorization": f"Bearer {tok}"}

    r = client.post(
        f"/api/v1/datasets/{ds_id}/annotations",
        json={"body": "suspicious", "column_name": "income"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    ann = r.json()
    assert ann["body"] == "suspicious" and ann["column_name"] == "income"

    lst = client.get(f"/api/v1/datasets/{ds_id}/annotations", headers=h)
    assert lst.status_code == 200 and len(lst.json()) >= 1


# ---------------------------------------------------------------------------
# v3 — Webhooks
# ---------------------------------------------------------------------------
def test_webhook_crud_and_secret_masked():
    tok, _, _ = _reg()
    h = {"Authorization": f"Bearer {tok}"}
    r = client.post(
        "/api/v1/webhooks",
        json={"name": "wh", "url": "https://example.com/hook", "events": ["alert.triggered"]},
        headers=h,
    )
    assert r.status_code == 201, r.text
    full = r.json()["full_secret"]
    assert full and len(full) >= 16
    wh_id = r.json()["id"]

    # listing masks the secret
    lst = client.get("/api/v1/webhooks", headers=h)
    assert lst.status_code == 200
    listed = next(w for w in lst.json() if w["id"] == wh_id)
    assert listed.get("full_secret") is None

    dele = client.delete(f"/api/v1/webhooks/{wh_id}", headers=h)
    assert dele.status_code == 204, dele.text


# ---------------------------------------------------------------------------
# v4 — Model registry
# ---------------------------------------------------------------------------
def _done_job(uid):
    db = SessionLocal()
    try:
        from app.db.models import TrainingJob

        job = TrainingJob(owner_id=uuid.UUID(uid), status="DONE", task="classification", target="income")
        db.add(job)
        db.commit()
        db.refresh(job)
        return str(job.id)
    finally:
        db.close()


def test_model_registry_promote_and_predict():
    tok, uid, _ = _reg()
    h = {"Authorization": f"Bearer {tok}"}
    job_id = _done_job(uid)

    # promote
    r = client.post(f"/api/v1/models/{job_id}/promote", json={"stage": "production"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == "production"

    # registry lists it and marks it current
    reg = client.get("/api/v1/models/registry", headers=h)
    assert reg.status_code == 200
    entry = next((m for m in reg.json() if m["id"] == job_id), None)
    assert entry is not None and entry["current"] is True

    # predict requires a READY model -> graceful 409
    pr = client.post(
        f"/api/v1/models/{job_id}/predict",
        json={"instances": [{"age": 30}]},
        headers=h,
    )
    assert pr.status_code == 409, pr.text


# ---------------------------------------------------------------------------
# Auditing + usage metering (admin visibility)
# ---------------------------------------------------------------------------
def test_audit_log_written_and_visible_to_admin():
    tok, _, _ = _reg()
    _make_admin(tok)

    client.post("/api/v1/teams", json={"name": "AuditCo"}, headers={"Authorization": f"Bearer {tok}"})

    r = client.get("/api/v1/audit", params={"action": "team.create"}, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200, r.text
    assert len(r.json()) >= 1


def test_api_usage_metered_and_visible_to_admin():
    tok, _, _ = _reg()
    _make_admin(tok)

    client.get("/api/v1/teams", headers={"Authorization": f"Bearer {tok}"})

    r = client.get("/api/v1/usage", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200, r.text
    total = sum(u["count"] for u in r.json())
    assert total >= 1
