from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import _http, get_current_user, require_dataset_access
from app.db.models import CleaningRecommendation, Dataset, User
from app.db.session import get_db
from app.schemas.cleaning import (
    ApplyCleaningRequest,
    CleaningStatusOut,
    DiffSummary,
    RecommendationOut,
)
from app.workers.tasks import apply_cleaning, generate_cleaning_recommendations

router = APIRouter(prefix="/datasets", tags=["cleaning"])


@router.get("/{dataset_id}/recommendations", response_model=list[RecommendationOut])
def get_recommendations(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = require_dataset_access(dataset_id, user, db)
    recs = db.query(CleaningRecommendation).filter_by(dataset_id=ds.id).all()
    return [
        RecommendationOut(
            id=str(r.id),
            column_name=r.column_name,
            issue_type=r.issue_type,
            stat_reference=r.stat_reference,
            recommendation=r.recommendation,
            rationale=r.rationale,
            accepted=r.accepted if r.accepted is not None else False,
        )
        for r in recs
    ]


@router.post("/{dataset_id}/recommendations", response_model=dict)
def trigger_recommendations(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = require_dataset_access(dataset_id, user, db)
    generate_cleaning_recommendations.delay(dataset_id)
    return {"dataset_id": dataset_id, "status": "QUEUED"}


@router.post("/{dataset_id}/cleaning/apply", response_model=CleaningStatusOut)
def apply_cleaning_endpoint(dataset_id: str, body: ApplyCleaningRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = require_dataset_access(dataset_id, user, db)
    apply_cleaning.delay(dataset_id, body.accepted_recommendation_ids)
    return CleaningStatusOut(dataset_id=dataset_id, cleaning_available=True, cleaned_exists=False)


@router.get("/{dataset_id}/cleaning/status", response_model=CleaningStatusOut)
def cleaning_status(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.core.storage import storage

    ds = require_dataset_access(dataset_id, user, db)
    return CleaningStatusOut(
        dataset_id=dataset_id,
        cleaning_available=bool(ds.cleaned),
        cleaned_exists=storage.cleaned_exists(dataset_id),
    )


@router.get("/{dataset_id}/cleaning/diff", response_model=DiffSummary)
def cleaning_diff(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = require_dataset_access(dataset_id, user, db)
    if not ds.cleaned:
        raise _http(409, "NO_CLEANING", "No cleaning has been applied yet.")
    d = ds.cleaned.diff_summary
    return DiffSummary(**d)
