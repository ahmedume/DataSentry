from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import _http, get_current_user, require_dataset_access
from app.core.storage import storage
from app.db.models import Dataset, ProfilingResult, User
from app.db.session import get_db
from app.schemas.charts import CategoricalBars, MissingnessBars, NumericHistogram
from app.services import chart_aggregator, profiler

router = APIRouter(prefix="/datasets", tags=["charts"])


def _load_df(dataset_id: str, user: User, db: Session):
    require_dataset_access(dataset_id, user, db)
    if not storage.raw_path(dataset_id).exists():
        raise _http(409, "NOT_READY", "Raw file not available.")
    return profiler.read_csv(storage.raw_path(dataset_id))


@router.get("/{dataset_id}/charts/numeric/{column}", response_model=NumericHistogram)
def numeric_chart(dataset_id: str, column: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    df = _load_df(dataset_id, user, db)
    return NumericHistogram(**chart_aggregator.numeric_histogram(df, column))


@router.get("/{dataset_id}/charts/categorical/{column}", response_model=CategoricalBars)
def categorical_chart(dataset_id: str, column: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    df = _load_df(dataset_id, user, db)
    return CategoricalBars(**chart_aggregator.categorical_bars(df, column))


@router.get("/{dataset_id}/charts/missingness", response_model=MissingnessBars)
def missingness_chart(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    df = _load_df(dataset_id, user, db)
    return MissingnessBars(**chart_aggregator.missingness(df))
