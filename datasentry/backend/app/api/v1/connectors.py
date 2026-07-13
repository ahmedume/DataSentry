from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from app.core.ids import _uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_team_id_header
from app.core.rbac import membership_for, teams_for_user
from app.core.storage import storage
from app.db.models import Connector, Dataset, TeamMembership, User
from app.db.session import get_db
from app.schemas.connectors import (
    ConnectorCreate,
    ConnectorOut,
    ConnectorIngestResult,
    ConnectorTestResult,
)
from app.services import connectors as connector_svc
from app.workers import tasks

router = APIRouter(prefix="/connectors", tags=["connectors"])


def _http(status: int, code: str, message: str):
    return HTTPException(status_code=status, detail={"error_code": code, "message": message})


def _team_ids(db: Session, user: User) -> list:
    return [t.id for t in teams_for_user(db, user)]


def _access_filter(db: Session, user: User):
    """Return connectors owned by the user OR shared with a team they belong to."""
    tids = _team_ids(db, user)
    q = db.query(Connector)
    if tids:
        return q.filter((Connector.owner_id == user.id) | (Connector.team_id.in_(tids)))
    return q.filter(Connector.owner_id == user.id)


def _out(c: Connector) -> ConnectorOut:
    return ConnectorOut(
        id=str(c.id),
        name=c.name,
        type=c.type,
        config=connector_svc.redact_config(connector_svc.parse_config(c.config)),
        enabled=c.enabled == "true",
        last_tested_at=c.last_tested_at.isoformat() if c.last_tested_at else None,
        last_error=c.last_error,
        created_at=c.created_at.isoformat() if c.created_at else None,
    )


@router.get("", response_model=list[ConnectorOut])
def list_connectors(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = _access_filter(db, user).all()
    return [_out(c) for c in rows]


@router.post("", response_model=ConnectorOut, status_code=201)
def create_connector(body: ConnectorCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db), request: Request = None):
    if body.type not in (connector_svc.LOCAL, connector_svc.POSTGRES, connector_svc.S3):
        raise _http(400, "BAD_TYPE", "type must be local, postgres, or s3.")
    team_id = None
    raw = get_team_id_header(request) if request else None
    if raw:
        try:
            tid = _uuid(raw)
            if membership_for(db, user, tid):
                team_id = tid
        except ValueError:
            pass
    c = Connector(
        owner_id=user.id,
        team_id=team_id,
        name=body.name,
        type=body.type,
        config=json.dumps(body.config or {}),
        enabled="true",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _out(c)


@router.get("/{connector_id}", response_model=ConnectorOut)
def get_connector(connector_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _access_filter(db, user).filter(Connector.id == _uuid(connector_id)).first()
    if not c:
        raise _http(404, "NOT_FOUND", "Connector not found.")
    return _out(c)


@router.delete("/{connector_id}", status_code=204)
def delete_connector(connector_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _access_filter(db, user).filter(Connector.id == _uuid(connector_id)).first()
    if not c:
        raise _http(404, "NOT_FOUND", "Connector not found.")
    db.delete(c)
    db.commit()


@router.post("/{connector_id}/test", response_model=ConnectorTestResult)
def test_connector(connector_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _access_filter(db, user).filter(Connector.id == _uuid(connector_id)).first()
    if not c:
        raise _http(404, "NOT_FOUND", "Connector not found.")
    try:
        svc = connector_svc.build_connector(c.type, connector_svc.parse_config(c.config))
        ok = svc.test()
        c.last_tested_at = datetime.now(timezone.utc)
        c.last_error = None if ok else "Connection test returned false."
        db.commit()
        return ConnectorTestResult(ok=ok, error=c.last_error)
    except Exception as e:
        c.last_error = str(e)
        db.commit()
        return ConnectorTestResult(ok=False, error=str(e))


@router.post("/{connector_id}/ingest", response_model=ConnectorIngestResult)
def ingest_connector(connector_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _access_filter(db, user).filter(Connector.id == _uuid(connector_id)).first()
    if not c:
        raise _http(404, "NOT_FOUND", "Connector not found.")
    dataset_id = str(uuid.uuid4())
    ds = Dataset(
        id=_uuid(dataset_id),
        original_filename=f"{c.name} (pending)",
        status="QUEUED",
        file_path=str(storage.raw_path(dataset_id)),
        owner_id=user.id,
        team_id=c.team_id,
    )
    db.add(ds)
    db.commit()
    tasks.ingest_connector.delay(connector_id, dataset_id)
    return ConnectorIngestResult(dataset_id=dataset_id, status="QUEUED")
