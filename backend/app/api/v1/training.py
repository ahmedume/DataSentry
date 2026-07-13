from __future__ import annotations

import json
import uuid

from app.core.ids import _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_team_id_header
from app.core.rbac import membership_for, teams_for_user
from app.db.models import Connector, Dataset, TrainingJob, User
from app.db.session import get_db
from app.schemas.training import StartTrainingRequest, TrainingJobOut
from app.workers import tasks

router = APIRouter(prefix="/training", tags=["training"])


def _http(status: int, code: str, message: str):
    return HTTPException(status_code=status, detail={"error_code": code, "message": message})


def _team_ids(db: Session, user: User) -> list:
    return [t.id for t in teams_for_user(db, user)]


def _job_filter(db: Session, user: User):
    tids = _team_ids(db, user)
    q = db.query(TrainingJob)
    if tids:
        return q.filter((TrainingJob.owner_id == user.id) | (TrainingJob.team_id.in_(tids)))
    return q.filter(TrainingJob.owner_id == user.id)


def _out(j: TrainingJob) -> TrainingJobOut:
    return TrainingJobOut(
        id=str(j.id),
        dataset_id=str(j.dataset_id) if j.dataset_id else None,
        connector_id=str(j.connector_id) if j.connector_id else None,
        target=j.target,
        task=j.task,
        status=j.status,
        metrics=json.loads(j.metrics_json) if j.metrics_json and j.metrics_json != "{}" else None,
        feature_importances=json.loads(j.feature_importances_json) if j.feature_importances_json and j.feature_importances_json != "{}" else None,
        model_path=j.model_path,
        error_message=j.error_message,
        created_at=j.created_at.isoformat() if j.created_at else None,
    )


@router.post("", response_model=TrainingJobOut, status_code=201)
def start_training(body: StartTrainingRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db), request: Request = None):
    team_id = None
    raw = get_team_id_header(request) if request else None
    if raw:
        try:
            tid = _uuid(raw)
            if membership_for(db, user, tid):
                team_id = tid
        except ValueError:
            pass

    if body.source_type == "dataset":
        ds = db.query(Dataset).filter(Dataset.id == _uuid(body.source_id)).first()
        if not ds:
            raise _http(404, "NOT_FOUND", "Dataset not found.")
        if ds.owner_id and ds.owner_id != user.id and not (ds.team_id and membership_for(db, user, ds.team_id)):
            raise _http(403, "FORBIDDEN", "Not your dataset.")
    elif body.source_type == "connector":
        c = db.query(Connector).filter(Connector.id == _uuid(body.source_id)).first()
        if not c:
            raise _http(404, "NOT_FOUND", "Connector not found or not owned.")
        if c.owner_id and c.owner_id != user.id and not (c.team_id and membership_for(db, user, c.team_id)):
            raise _http(403, "FORBIDDEN", "Not your connector.")
    else:
        raise _http(400, "BAD_SOURCE", "source_type must be dataset or connector.")

    job = TrainingJob(
        owner_id=user.id,
        team_id=team_id,
        dataset_id=_uuid(body.source_id) if body.source_type == "dataset" else None,
        connector_id=_uuid(body.source_id) if body.source_type == "connector" else None,
        target=body.target,
        task=body.task,
        status="QUEUED",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = str(job.id)
    tasks.train_model.delay(job_id, body.source_type, body.source_id, body.target, body.task)
    return _out(job)


@router.get("", response_model=list[TrainingJobOut])
def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = _job_filter(db, user).order_by(TrainingJob.created_at.desc()).all()
    return [_out(j) for j in rows]


@router.get("/{job_id}", response_model=TrainingJobOut)
def get_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    j = _job_filter(db, user).filter(TrainingJob.id == _uuid(job_id)).first()
    if not j:
        raise _http(404, "NOT_FOUND", "Training job not found.")
    return _out(j)


@router.get("/{job_id}/download")
def download_model(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse

    from app.core.storage import storage

    j = _job_filter(db, user).filter(TrainingJob.id == _uuid(job_id)).first()
    if not j:
        raise _http(404, "NOT_FOUND", "Training job not found.")
    if not storage.model_exists(job_id):
        raise _http(404, "NO_MODEL", "Model artifact not available.")
    return FileResponse(str(storage.model_path(job_id)), filename=f"model_{job_id}.pkl")
