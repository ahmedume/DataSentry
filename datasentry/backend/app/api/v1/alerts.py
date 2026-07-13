from __future__ import annotations

import json
import uuid

from app.core.ids import _uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.models import AlertEvent, AlertRule, User
from app.db.session import get_db
from app.schemas.alerts import AlertRuleCreate, AlertRuleOut, AlertEventOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _http(status: int, code: str, message: str):
    return HTTPException(status_code=status, detail={"error_code": code, "message": message})


def _rule_out(r: AlertRule) -> AlertRuleOut:
    return AlertRuleOut(
        id=str(r.id),
        name=r.name,
        scope_type=r.scope_type,
        scope_id=r.scope_id,
        metric=r.metric,
        operator=r.operator,
        threshold=r.threshold,
        channels=json.loads(r.channels_json or '["slack"]'),
        enabled=r.enabled == "true",
        created_at=r.created_at.isoformat() if r.created_at else None,
    )


@router.get("/rules", response_model=list[AlertRuleOut])
def list_rules(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(AlertRule).filter(AlertRule.owner_id == user.id).all()
    return [_rule_out(r) for r in rows]


@router.post("/rules", response_model=AlertRuleOut, status_code=201)
def create_rule(body: AlertRuleCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = AlertRule(
        owner_id=user.id,
        name=body.name,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        metric=body.metric,
        operator=body.operator,
        threshold=body.threshold,
        channels_json=json.dumps(body.channels),
        enabled="true" if body.enabled else "false",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return _rule_out(r)


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(AlertRule).filter(AlertRule.id == _uuid(rule_id), AlertRule.owner_id == user.id).first()
    if not r:
        raise _http(404, "NOT_FOUND", "Rule not found.")
    db.delete(r)
    db.commit()


@router.get("/events", response_model=list[AlertEventOut])
def list_events(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(AlertEvent).filter(AlertEvent.owner_id == user.id).order_by(AlertEvent.created_at.desc()).all()
    return [
        AlertEventOut(
            id=str(e.id),
            rule_id=str(e.rule_id),
            message=e.message,
            delivered=e.delivered == "true",
            payload=json.loads(e.payload_json or "{}"),
            created_at=e.created_at.isoformat() if e.created_at else None,
        )
        for e in rows
    ]
