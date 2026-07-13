from __future__ import annotations

import json
import pickle

import pandas as pd
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import _http, get_current_user
from app.core.ids import _uuid
from app.db.models import TrainingJob, User
from app.db.session import get_db
from app.schemas.v34 import ModelOut, ModelPromote, PredictRequest, PredictResponse

router = APIRouter(prefix="/models", tags=["models"])


def _out(job: TrainingJob, current: bool = False) -> ModelOut:
    return ModelOut(
        id=str(job.id),
        target=job.target,
        task=job.task,
        status=job.status,
        stage=job.stage,
        metrics=json.loads(job.metrics_json or "{}"),
        feature_importances=json.loads(job.feature_importances_json or "{}"),
        current=current,
        created_at=job.created_at.isoformat() if job.created_at else None,
    )


_STAGE_RANK = {"production": 3, "staging": 2, "dev": 1}


@router.get("/registry", response_model=list[ModelOut])
def registry(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = (
        db.query(TrainingJob)
        .filter(TrainingJob.owner_id == user.id, TrainingJob.stage.in_(list(_STAGE_RANK)))
        .order_by(TrainingJob.created_at.desc())
        .all()
    )
    best: dict = {}
    for j in jobs:
        key = j.dataset_id or j.id
        rank = _STAGE_RANK.get(j.stage or "", 0)
        if key not in best or rank > best[key][0]:
            best[key] = (rank, j.id)
    current_ids = {v[1] for v in best.values()}
    return [_out(j, current=(j.id in current_ids)) for j in jobs]


def _load_model(job: TrainingJob):
    from app.core.storage import storage

    path = storage.model_path(str(job.id))
    if not path.exists():
        raise _http(404, "NO_MODEL", "Model artifact not found.")
    with open(path, "rb") as f:
        return pickle.load(f)


@router.get("", response_model=list[ModelOut])
def list_models(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = db.query(TrainingJob).filter(TrainingJob.owner_id == user.id).order_by(TrainingJob.created_at.desc()).all()
    return [_out(j) for j in jobs]


@router.get("/{job_id}", response_model=ModelOut)
def get_model(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(TrainingJob).filter(TrainingJob.id == _uuid(job_id), TrainingJob.owner_id == user.id).first()
    if not job:
        raise _http(404, "NOT_FOUND", "Model not found.")
    return _out(job)


@router.post("/{job_id}/promote", response_model=ModelOut)
def promote(job_id: str, body: ModelPromote, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.stage not in ("dev", "staging", "production"):
        raise _http(400, "BAD_STAGE", "stage must be dev | staging | production.")
    job = db.query(TrainingJob).filter(TrainingJob.id == _uuid(job_id), TrainingJob.owner_id == user.id).first()
    if not job:
        raise _http(404, "NOT_FOUND", "Model not found.")
    job.stage = body.stage
    db.commit()
    return _out(job)


def _predict(job: TrainingJob, instances: list[dict]) -> PredictResponse:
    if job.status != "READY":
        raise _http(409, "NOT_READY", "Model is not ready for inference.")
    model = _load_model(job)
    df = pd.DataFrame(instances)
    preds = model.predict(df)
    probabilities = None
    if hasattr(model, "predict_proba"):
        try:
            probabilities = model.predict_proba(df).tolist()
        except Exception:
            probabilities = None
    return PredictResponse(predictions=preds.tolist(), probabilities=probabilities, task=job.task)


@router.post("/{job_id}/predict", response_model=PredictResponse)
def predict(job_id: str, body: PredictRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(TrainingJob).filter(TrainingJob.id == _uuid(job_id), TrainingJob.owner_id == user.id).first()
    if not job:
        raise _http(404, "NOT_FOUND", "Model not found.")
    return _predict(job, body.instances)
