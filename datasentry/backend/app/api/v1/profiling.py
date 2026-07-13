from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import _http, get_current_user, require_dataset_access
from app.db.models import Dataset, ProfilingResult, User
from app.db.session import get_db
from app.schemas.profiling import ColumnProfile, ProfilingOut

router = APIRouter(prefix="/datasets", tags=["profiling"])


@router.get("/{dataset_id}/profile", response_model=ProfilingOut)
def get_profile(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = require_dataset_access(dataset_id, user, db)
    prof = db.query(ProfilingResult).filter_by(dataset_id=ds.id).first()
    if not prof:
        raise _http(409, "NOT_READY", "Profiling result is not available yet.")
    columns = [ColumnProfile(**c) for c in prof.column_profiles]
    return ProfilingOut(
        dataset_id=dataset_id,
        row_count=ds.row_count or 0,
        column_count=ds.column_count or 0,
        byte_size=ds.byte_size or 0,
        duplicate_row_count=prof.duplicate_row_count,
        columns=columns,
    )
