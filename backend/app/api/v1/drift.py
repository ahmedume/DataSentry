from __future__ import annotations

import json
import uuid

from app.core.ids import _uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.storage import storage
from app.db.models import Dataset, DriftComparison, DriftSnapshot, User
from app.db.session import get_db
from app.schemas.drift import (
    CreateSnapshotRequest,
    DriftComparisonOut,
    DriftCompareDatasetRequest,
    DriftCompareRequest,
    DriftSnapshotOut,
)
from app.services import drift as drift_svc
from app.services import profiler

router = APIRouter(prefix="/drift", tags=["drift"])


def _http(status: int, code: str, message: str):
    return HTTPException(status_code=status, detail={"error_code": code, "message": message})


def _snap_out(s: DriftSnapshot) -> DriftSnapshotOut:
    return DriftSnapshotOut(
        id=str(s.id),
        dataset_id=str(s.dataset_id),
        label=s.label,
        row_count=int(s.row_count) if s.row_count and str(s.row_count).isdigit() else None,
        created_at=s.created_at.isoformat() if s.created_at else None,
    )


def _require_dataset(dataset_id: str, user: User, db: Session) -> Dataset:
    ds = db.query(Dataset).filter(Dataset.id == _uuid(dataset_id)).first()
    if not ds:
        raise _http(404, "NOT_FOUND", "Dataset not found.")
    if ds.owner_id and ds.owner_id != user.id:
        raise _http(403, "FORBIDDEN", "Not your dataset.")
    return ds


@router.post("/snapshots", response_model=DriftSnapshotOut, status_code=201)
def create_snapshot(
    dataset_id: str,
    body: CreateSnapshotRequest = CreateSnapshotRequest(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ds = _require_dataset(dataset_id, user, db)
    if not storage.raw_path(dataset_id).exists():
        raise _http(400, "NO_DATA", "Dataset has no raw data to snapshot.")
    df = profiler.read_csv(storage.raw_path(dataset_id))
    sample = df.head(5000)
    snap_id = str(uuid.uuid4())
    storage.save_snapshot(snap_id, sample)
    profile = drift_svc.build_profile_json(df, storage.raw_path(dataset_id).stat().st_size)
    snap = DriftSnapshot(
        id=_uuid(snap_id),
        owner_id=user.id,
        dataset_id=_uuid(dataset_id),
        label=body.label or f"snapshot {snap_id[:8]}",
        profile_json=json.dumps(profile),
        sample_path=str(storage.snapshot_path(snap_id)),
        row_count=str(df.shape[0]),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return _snap_out(snap)


@router.get("/snapshots", response_model=list[DriftSnapshotOut])
def list_snapshots(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(DriftSnapshot).filter(DriftSnapshot.owner_id == user.id).all()
    return [_snap_out(s) for s in rows]


@router.post("/compare", response_model=DriftComparisonOut)
def compare_snapshots(body: DriftCompareRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    base = db.query(DriftSnapshot).filter(DriftSnapshot.id == _uuid(body.baseline_id), DriftSnapshot.owner_id == user.id).first()
    curr = db.query(DriftSnapshot).filter(DriftSnapshot.id == _uuid(body.current_id), DriftSnapshot.owner_id == user.id).first()
    if not base or not curr:
        raise _http(404, "NOT_FOUND", "Snapshot not found.")
    if not base.sample_path or not curr.sample_path:
        raise _http(400, "NO_SAMPLE", "Snapshot has no stored sample.")
    b_df = profiler.read_csv(base.sample_path)
    c_df = profiler.read_csv(curr.sample_path)
    results = drift_svc.compare_dataframes(b_df, c_df)
    comp = DriftComparison(
        owner_id=user.id,
        baseline_id=_uuid(body.baseline_id),
        current_id=_uuid(body.current_id),
        results_json=json.dumps(results),
        status=results["status"],
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return DriftComparisonOut(
        id=str(comp.id),
        baseline_id=body.baseline_id,
        current_id=body.current_id,
        status=comp.status,
        results=results,
        created_at=comp.created_at.isoformat() if comp.created_at else None,
    )


@router.post("/compare-dataset", response_model=DriftComparisonOut)
def compare_dataset(body: DriftCompareDatasetRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    snap = db.query(DriftSnapshot).filter(DriftSnapshot.id == _uuid(body.snapshot_id), DriftSnapshot.owner_id == user.id).first()
    if not snap:
        raise _http(404, "NOT_FOUND", "Snapshot not found.")
    ds = _require_dataset(body.dataset_id, user, db)
    if not snap.sample_path or not storage.raw_path(body.dataset_id).exists():
        raise _http(400, "NO_DATA", "Missing sample or dataset data.")
    b_df = profiler.read_csv(snap.sample_path)
    c_df = profiler.read_csv(storage.raw_path(body.dataset_id))
    results = drift_svc.compare_dataframes(b_df, c_df)
    comp = DriftComparison(
        owner_id=user.id,
        baseline_id=_uuid(body.snapshot_id),
        current_id=_uuid(body.dataset_id),
        results_json=json.dumps(results),
        status=results["status"],
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return DriftComparisonOut(
        id=str(comp.id),
        baseline_id=body.snapshot_id,
        current_id=body.dataset_id,
        status=comp.status,
        results=results,
        created_at=comp.created_at.isoformat() if comp.created_at else None,
    )
