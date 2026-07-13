from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import _http, get_current_user, get_team_id_header
from app.core.rbac import membership_for
from app.db.models import AuditLog, User
from app.db.session import get_db
from app.schemas.v34 import AuditOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
def list_audit(user: User = Depends(get_current_user), db: Session = Depends(get_db), request: Request = None, limit: int = 100):
    team_id = get_team_id_header(request) if request else None
    q = db.query(AuditLog)
    if team_id:
        try:
            tid = uuid.UUID(team_id)
        except ValueError:
            raise _http(400, "BAD_TEAM", "Invalid team id.")
        if not membership_for(db, user, tid):
            raise _http(403, "FORBIDDEN", "Not a member of that team.")
        q = q.filter(AuditLog.team_id == str(tid))
    else:
        q = q.filter(AuditLog.actor_id == str(user.id))
    rows = q.order_by(AuditLog.created_at.desc()).limit(min(limit, 500)).all()
    return [
        AuditOut(
            id=str(r.id),
            actor_id=str(r.actor_id) if r.actor_id else None,
            team_id=str(r.team_id) if r.team_id else None,
            action=r.action,
            target_type=r.target_type,
            target_id=r.target_id,
            meta=json.loads(r.meta_json or "{}"),
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]
