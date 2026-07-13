from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import _http, get_current_user, require_dataset_access
from app.db.models import AiInsight, Dataset, User
from app.db.session import get_db
from app.schemas.insights import AiInsightOut
from app.workers.tasks import generate_ai_insights

router = APIRouter(prefix="/datasets", tags=["insights"])


@router.post("/{dataset_id}/insights", response_model=AiInsightOut)
def trigger_insights(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = require_dataset_access(dataset_id, user, db)
    generate_ai_insights.delay(dataset_id)
    return get_insights(dataset_id, db, user)


@router.get("/{dataset_id}/insights", response_model=AiInsightOut)
def get_insights(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = require_dataset_access(dataset_id, user, db)
    row = db.query(AiInsight).filter_by(dataset_id=ds.id).first()
    if not row:
        return AiInsightOut(
            dataset_id=dataset_id,
            column_explanations=[],
            candidate_targets=[],
            possible_tasks=[],
            risks_and_assumptions=["AI explanation unavailable — profiling data is still shown below."],
            available=False,
        )
    return AiInsightOut(
        dataset_id=dataset_id,
        column_explanations=row.column_explanations,
        candidate_targets=row.candidate_targets,
        possible_tasks=row.possible_tasks,
        risks_and_assumptions=row.risks_and_assumptions,
        available=True,
    )
