from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.deps import get_optional_user
from app.core.storage import storage
from app.db.models import Dataset, ProfilingResult, User
from app.db.session import get_db
from app.schemas.common import ErrorResponse
from app.schemas.dataset import DatasetOut, UploadResponse
from app.services import profiler
from app.workers.tasks import profile_dataset


router = APIRouter(prefix="/datasets", tags=["datasets"])


def _http(status: int, code: str, message: str):
    return HTTPException(status_code=status, detail={"error_code": code, "message": message})


def _find_dataset(dataset_id: str, db: Session) -> Dataset | None:
    try:
        return db.get(Dataset, uuid.UUID(dataset_id))
    except ValueError:
        return None


@router.post("/upload", response_model=UploadResponse)
def upload_dataset(file: UploadFile, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    name = file.filename or ""
    if not name.lower().endswith(".csv"):
        raise _http(400, "INVALID_TYPE", "Only .csv files are accepted in v1.")
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

    # Validate UTF-8 + parseability + non-empty (SRS-1.3/1.4).
    try:
        df = profiler.read_csv(storage.raw_path(dataset_id))
    except UnicodeDecodeError:
        raise _http(400, "ENCODING_ERROR", "File is not valid UTF-8. Please re-save as UTF-8 CSV.")
    except Exception:
        raise _http(400, "PARSE_ERROR", "File could not be parsed as CSV.")
    if df.shape[0] == 0 or df.shape[1] == 0:
        raise _http(400, "EMPTY_DATA", "File has 0 rows or 0 columns.")

    ds = Dataset(
        id=uuid.UUID(dataset_id),
        owner_id=user.id if user else None,
        original_filename=name,
        status="QUEUED",
        file_path=str(storage.raw_path(dataset_id)),
    )
    db.add(ds)
    db.commit()

    profile_dataset.delay(dataset_id)

    return UploadResponse(dataset_id=dataset_id, status=ds.status)


@router.get("", response_model=list[DatasetOut])
def list_datasets(db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    q = db.query(Dataset)
    if user:
        q = q.filter(Dataset.owner_id == user.id)
    datasets = q.order_by(Dataset.created_at.desc()).all()
    return [
        DatasetOut(
            id=str(ds.id),
            original_filename=ds.original_filename,
            status=ds.status,
            row_count=ds.row_count,
            column_count=ds.column_count,
            byte_size=ds.byte_size,
            error_message=ds.error_message,
        )
        for ds in datasets
    ]


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: str, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    ds = _find_dataset(dataset_id, db)
    if not ds:
        raise _http(404, "NOT_FOUND", "Dataset not found.")
    if ds.owner_id is not None and (not user or ds.owner_id != user.id):
        raise _http(403, "FORBIDDEN", "You do not own this dataset.")
    return DatasetOut(
        id=str(ds.id),
        original_filename=ds.original_filename,
        status=ds.status,
        row_count=ds.row_count,
        column_count=ds.column_count,
        byte_size=ds.byte_size,
        error_message=ds.error_message,
    )


@router.get("/{dataset_id}/status", response_model=DatasetOut)
def get_status(dataset_id: str, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    return get_dataset(dataset_id, db, user)
