from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_team_id_header
from app.core.rbac import membership_for
from app.db.models import ApiUsage, User
from app.db.session import get_db
from app.schemas.v34 import UsageOut

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("", response_model=list[UsageOut])
def get_usage(user: User = Depends(get_current_user), db: Session = Depends(get_db), request: Request = None):
    team_id = get_team_id_header(request) if request else None
    q = db.query(ApiUsage)
    if team_id:
        try:
            tid = uuid.UUID(team_id)
        except ValueError:
            tid = None
        if tid and membership_for(db, user, tid):
            q = q.filter(ApiUsage.team_id == str(tid))
        else:
            q = q.filter(ApiUsage.user_id == str(user.id))
    else:
        q = q.filter(ApiUsage.user_id == str(user.id))
    rows = q.order_by(ApiUsage.day.desc(), ApiUsage.endpoint).all()
    return [UsageOut(endpoint=r.endpoint, day=r.day, count=int(r.count or 0)) for r in rows]
