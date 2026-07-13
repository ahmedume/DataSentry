from __future__ import annotations

import json
import uuid

from app.core.ids import _uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_team_id_header
from app.core.rbac import membership_for, teams_for_user
from app.db.models import Connector, Dataset, MonitorRun, MonitorSchedule, User
from app.db.session import get_db
from app.schemas.monitoring import MonitorScheduleCreate, MonitorScheduleOut, MonitorRunOut
from app.workers import tasks

router = APIRouter(prefix="/monitors", tags=["monitors"])


def _http(status: int, code: str, message: str):
    return HTTPException(status_code=status, detail={"error_code": code, "message": message})


def _team_ids(db: Session, user: User) -> list:
    return [t.id for t in teams_for_user(db, user)]


def _sched_filter(db: Session, user: User):
    tids = _team_ids(db, user)
    q = db.query(MonitorSchedule)
    if tids:
        return q.filter((MonitorSchedule.owner_id == user.id) | (MonitorSchedule.team_id.in_(tids)))
    return q.filter(MonitorSchedule.owner_id == user.id)


def _run_filter(db: Session, user: User):
    tids = _team_ids(db, user)
    q = db.query(MonitorRun)
    if tids:
        return q.join(MonitorSchedule, MonitorSchedule.id == MonitorRun.schedule_id).filter(
            (MonitorSchedule.owner_id == user.id) | (MonitorSchedule.team_id.in_(tids))
        )
    return q.filter(MonitorRun.owner_id == user.id)


def _sched_out(s: MonitorSchedule) -> MonitorScheduleOut:
    return MonitorScheduleOut(
        id=str(s.id),
        name=s.name,
        source_type=s.source_type,
        source_id=str(s.source_id),
        cadence_minutes=int(s.cadence_minutes),
        enabled=s.enabled == "true",
        baseline_snapshot_id=str(s.baseline_snapshot_id) if s.baseline_snapshot_id else None,
        drift_threshold=float(s.drift_threshold),
        last_run_at=s.last_run_at.isoformat() if s.last_run_at else None,
    )


def _run_out(r: MonitorRun) -> MonitorRunOut:
    return MonitorRunOut(
        id=str(r.id),
        schedule_id=str(r.schedule_id),
        status=r.status,
        drift_status=r.drift_status,
        rows_processed=int(r.rows_processed) if r.rows_processed and str(r.rows_processed).isdigit() else None,
        drift_summary=json.loads(r.drift_summary_json) if r.drift_summary_json and r.drift_summary_json != "{}" else None,
        snapshot_id=str(r.snapshot_id) if r.snapshot_id else None,
        started_at=r.started_at.isoformat() if r.started_at else None,
        finished_at=r.finished_at.isoformat() if r.finished_at else None,
    )


@router.post("", response_model=MonitorScheduleOut, status_code=201)
def create_schedule(body: MonitorScheduleCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db), request: Request = None):
    if body.source_type == "dataset":
        src = db.query(Dataset).filter(Dataset.id == _uuid(body.source_id)).first()
    elif body.source_type == "connector":
        src = db.query(Connector).filter(Connector.id == _uuid(body.source_id)).first()
    else:
        raise _http(400, "BAD_SOURCE", "source_type must be dataset or connector.")
    if not src:
        raise _http(404, "NOT_FOUND", "Source not found.")
    if src.owner_id and src.owner_id != user.id and not (src.team_id and membership_for(db, user, src.team_id)):
        raise _http(403, "FORBIDDEN", "Not your source.")

    team_id = None
    raw = get_team_id_header(request) if request else None
    if raw:
        try:
            tid = _uuid(raw)
            if membership_for(db, user, tid):
                team_id = tid
        except ValueError:
            pass

    s = MonitorSchedule(
        owner_id=user.id,
        team_id=team_id,
        name=body.name,
        source_type=body.source_type,
        source_id=_uuid(body.source_id),
        cadence_minutes=str(body.cadence_minutes),
        enabled="true",
        baseline_snapshot_id=_uuid(body.baseline_snapshot_id) if body.baseline_snapshot_id else None,
        drift_threshold=str(body.drift_threshold),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _sched_out(s)


@router.get("", response_model=list[MonitorScheduleOut])
def list_schedules(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = _sched_filter(db, user).all()
    return [_sched_out(s) for s in rows]


@router.get("/{schedule_id}", response_model=MonitorScheduleOut)
def get_schedule(schedule_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _sched_filter(db, user).filter(MonitorSchedule.id == _uuid(schedule_id)).first()
    if not s:
        raise _http(404, "NOT_FOUND", "Schedule not found.")
    return _sched_out(s)


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _sched_filter(db, user).filter(MonitorSchedule.id == _uuid(schedule_id)).first()
    if not s:
        raise _http(404, "NOT_FOUND", "Schedule not found.")
    db.delete(s)
    db.commit()


@router.post("/{schedule_id}/run", response_model=MonitorRunOut)
def run_now(schedule_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _sched_filter(db, user).filter(MonitorSchedule.id == _uuid(schedule_id)).first()
    if not s:
        raise _http(404, "NOT_FOUND", "Schedule not found.")
    tasks.run_monitor.delay(schedule_id)
    run = (
        db.query(MonitorRun)
        .filter(MonitorRun.schedule_id == _uuid(schedule_id))
        .order_by(MonitorRun.started_at.desc())
        .first()
    )
    if not run:
        raise _http(404, "NOT_FOUND", "Run not created.")
    return _run_out(run)


@router.get("/{schedule_id}/runs", response_model=list[MonitorRunOut])
def list_runs(schedule_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        _run_filter(db, user)
        .filter(MonitorRun.schedule_id == _uuid(schedule_id))
        .order_by(MonitorRun.started_at.desc())
        .all()
    )
    return [_run_out(r) for r in rows]


@router.get("/runs/all", response_model=list[MonitorRunOut])
def list_all_runs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = _run_filter(db, user).order_by(MonitorRun.started_at.desc()).all()
    return [_run_out(r) for r in rows]
