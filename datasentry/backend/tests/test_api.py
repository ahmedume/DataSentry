import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CSV = "age,income,name\n30,50000,alice\n,None,bob\n40,60000,carol\n30,50000,alice\n"


def _auth_header():
    email = f"t_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_full_flow():
    h = _auth_header()

    res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("people.csv", CSV.encode(), "text/csv")},
    )
    assert res.status_code == 200, res.text
    dataset_id = res.json()["dataset_id"]

    prof = client.get(f"/api/v1/datasets/{dataset_id}/profile", headers=h).json()
    assert prof["row_count"] == 4
    assert prof["duplicate_row_count"] == 1

    client.post(f"/api/v1/datasets/{dataset_id}/insights", headers=h)
    insights = client.get(f"/api/v1/datasets/{dataset_id}/insights", headers=h).json()
    assert insights["available"] is True

    client.post(f"/api/v1/datasets/{dataset_id}/recommendations", headers=h)
    recs = client.get(f"/api/v1/datasets/{dataset_id}/recommendations", headers=h).json()
    assert len(recs) >= 1
    for r in recs:
        assert r["stat_reference"] in r["rationale"]

    ids = [r["id"] for r in recs]
    client.post(
        f"/api/v1/datasets/{dataset_id}/cleaning/apply",
        json={"accepted_recommendation_ids": ids},
        headers=h,
    )
    diff = client.get(f"/api/v1/datasets/{dataset_id}/cleaning/diff", headers=h).json()
    assert diff["row_count_before"] == 4

    dl = client.get(f"/api/v1/datasets/{dataset_id}/download/cleaned", headers=h)
    assert dl.status_code == 200
    assert b"age" in dl.content

    miss = client.get(f"/api/v1/datasets/{dataset_id}/charts/missingness", headers=h).json()
    assert "age" in miss["columns"]

    client.post(f"/api/v1/datasets/{dataset_id}/report", headers=h)
    status = client.get(f"/api/v1/datasets/{dataset_id}/report/status", headers=h).json()
    assert status["status"] == "READY"
    rep = client.get(f"/api/v1/datasets/{dataset_id}/report/download", headers=h)
    assert rep.status_code == 200
    assert rep.content[:4] == b"%PDF"


def test_upload_rejects_non_csv():
    res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("x.txt", b"a,b\n1,2\n", "text/plain")},
    )
    assert res.status_code == 400
    assert res.json()["error_code"] == "INVALID_TYPE"


def test_upload_rejects_oversize():
    big = b"a,b\n" + b"1,2\n" * 10
    res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("big.csv", big, "text/csv")},
    )
    assert res.status_code == 200
