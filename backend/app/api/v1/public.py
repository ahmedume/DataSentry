from __future__ import annotations

import json
import uuid

from app.core.ids import _uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_api_key, require_scopes
from app.core.storage import storage
from app.db.models import Dataset, DriftSnapshot, ProfilingResult
from app.db.session import get_db
from app.schemas.dataset import DatasetOut
from app.services import drift as drift_svc
from app.services import profiler
from app.workers import tasks

router = APIRouter(prefix="/public", tags=["public"])


def _http(status: int, code: str, message: str):
    return HTTPException(status_code=status, detail={"error_code": code, "message": message})


@router.post("/upload", response_model=DatasetOut, dependencies=[Depends(require_scopes(["datasets:write"]))])
def upload(file: UploadFile, auth: tuple = Depends(get_current_api_key), db: Session = Depends(get_db)):
    owner, _ = auth
    name = file.filename or ""
    if not name.lower().endswith(".csv"):
        raise _http(400, "INVALID_TYPE", "Only .csv files are accepted.")
    content = file.file.read()
    if len(content) > settings.max_upload_bytes:
        raise _http(413, "FILE_TOO_LARGE", "File exceeds 200MB limit.")
    if len(content) == 0:
        raise _http(400, "EMPTY_FILE", "Uploaded file is empty.")
    dataset_id = str(uuid.uuid4())
    try:
        storage.save_raw(dataset_id, content)
    except Exception:
        raise _http(500, "STORAGE_ERROR", "Could not store the uploaded file.")
    try:
        profiler.read_csv(storage.raw_path(dataset_id))
    except Exception:
        raise _http(400, "PARSE_ERROR", "File could not be parsed as CSV.")
    ds = Dataset(
        id=_uuid(dataset_id),
        original_filename=name,
        status="QUEUED",
        file_path=str(storage.raw_path(dataset_id)),
        owner_id=owner.id,
    )
    db.add(ds)
    db.commit()
    tasks.profile_dataset.delay(dataset_id)
    tasks.generate_ai_insights.delay(dataset_id)
    tasks.generate_cleaning_recommendations.delay(dataset_id)
    return DatasetOut(
        id=str(ds.id),
        original_filename=ds.original_filename,
        status=ds.status,
        row_count=ds.row_count,
        column_count=ds.column_count,
        byte_size=ds.byte_size,
        error_message=ds.error_message,
    )


@router.get("/datasets/{dataset_id}", response_model=DatasetOut, dependencies=[Depends(require_scopes(["datasets:read"]))])
def get_dataset(dataset_id: str, auth: tuple = Depends(get_current_api_key), db: Session = Depends(get_db)):
    ds = db.query(Dataset).filter(Dataset.id == _uuid(dataset_id)).first()
    if not ds:
        raise _http(404, "NOT_FOUND", "Dataset not found.")
    return DatasetOut(
        id=str(ds.id),
        original_filename=ds.original_filename,
        status=ds.status,
        row_count=ds.row_count,
        column_count=ds.column_count,
        byte_size=ds.byte_size,
        error_message=ds.error_message,
    )


@router.get("/datasets/{dataset_id}/profile", dependencies=[Depends(require_scopes(["datasets:read"]))])
def get_profile(dataset_id: str, auth: tuple = Depends(get_current_api_key), db: Session = Depends(get_db)):
    prof = db.query(ProfilingResult).filter(ProfilingResult.dataset_id == _uuid(dataset_id)).first()
    if not prof:
        raise _http(404, "NOT_PROFILED", "Dataset not profiled yet.")
    return {"row_count": prof.dataset.row_count, "columns": prof.column_profiles}


@router.post("/drift/compare-dataset", dependencies=[Depends(require_scopes(["drift:read"]))])
def drift_compare_dataset(body: dict, auth: tuple = Depends(get_current_api_key), db: Session = Depends(get_db)):
    snapshot_id = body.get("snapshot_id")
    dataset_id = body.get("dataset_id")
    if not snapshot_id or not dataset_id:
        raise _http(400, "BAD_REQUEST", "snapshot_id and dataset_id required.")
    snap = db.query(DriftSnapshot).filter(DriftSnapshot.id == _uuid(snapshot_id)).first()
    if not snap or not snap.sample_path:
        raise _http(404, "NO_SNAPSHOT", "Snapshot not found.")
    if not storage.raw_path(dataset_id).exists():
        raise _http(404, "NO_DATA", "Dataset data not found.")
    b_df = profiler.read_csv(snap.sample_path)
    c_df = profiler.read_csv(storage.raw_path(dataset_id))
    return drift_svc.compare_dataframes(b_df, c_df)


@router.post(
    "/models/{job_id}/predict",
    dependencies=[Depends(require_scopes(["models:read"]))],
)
def public_model_predict(
    job_id: str,
    body: dict,
    auth: tuple = Depends(get_current_api_key),
    db: Session = Depends(get_db),
):
    from app.api.v1.models_v4 import _predict
    from app.core.ids import _uuid
    from app.db.models import TrainingJob

    job = db.query(TrainingJob).filter(TrainingJob.id == _uuid(job_id)).first()
    if not job:
        raise _http(404, "NOT_FOUND", "Model not found.")
    return _predict(job, body["instances"])
