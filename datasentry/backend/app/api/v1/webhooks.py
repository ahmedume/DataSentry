from __future__ import annotations

import json
import secrets
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import _http, get_current_user, get_team_id_header
from app.core.rbac import membership_for
from app.db.models import User, Webhook
from app.db.session import get_db
from app.schemas.v34 import WebhookCreate, WebhookOut

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _out(w: Webhook, full_secret: str | None = None) -> WebhookOut:
    return WebhookOut(
        id=str(w.id),
        url=w.url,
        events=json.loads(w.events or "[]"),
        active=w.active == "true",
        full_secret=full_secret,
        created_at=w.created_at.isoformat() if w.created_at else None,
    )


def _resolve_team(db: Session, user: User, request: Request):
    tid = get_team_id_header(request)
    if not tid:
        return None, None
    try:
        tid = uuid.UUID(tid)
    except ValueError:
        raise _http(400, "BAD_TEAM", "Invalid team id.")
    if not membership_for(db, user, tid):
        raise _http(403, "FORBIDDEN", "Not a member of that team.")
    return tid, tid


@router.post("", response_model=WebhookOut, status_code=201)
def create_webhook(body: WebhookCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db), request: Request = None):
    if not body.url or not body.url.startswith("http"):
        raise _http(400, "BAD_URL", "A valid http(s) URL is required.")
    if not body.events:
        raise _http(400, "NO_EVENTS", "At least one event must be selected.")
    secret = body.secret or secrets.token_hex(24)
    team_id, _ = _resolve_team(db, user, request)
    wh = Webhook(
        owner_id=user.id,
        team_id=team_id,
        url=body.url,
        secret=secret,
        events=json.dumps(body.events),
    )
    db.add(wh)
    db.commit()
    return _out(wh, full_secret=secret)


@router.get("", response_model=list[WebhookOut])
def list_webhooks(user: User = Depends(get_current_user), db: Session = Depends(get_db), request: Request = None):
    team_id, _ = _resolve_team(db, user, request)
    q = db.query(Webhook)
    if team_id:
        q = q.filter(Webhook.team_id == team_id)
    else:
        q = q.filter(Webhook.owner_id == user.id)
    return [_out(w) for w in q.all()]


@router.post("/{webhook_id}/toggle", response_model=WebhookOut)
def toggle_webhook(webhook_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        wid = uuid.UUID(webhook_id)
    except ValueError:
        raise _http(400, "BAD_ID", "Invalid webhook id.")
    wh = db.query(Webhook).filter(Webhook.id == wid, Webhook.owner_id == user.id).first()
    if not wh:
        raise _http(404, "NOT_FOUND", "Webhook not found.")
    wh.active = "false" if wh.active == "true" else "true"
    db.commit()
    return _out(wh)


@router.delete("/{webhook_id}", status_code=204)
def delete_webhook(webhook_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        wid = uuid.UUID(webhook_id)
    except ValueError:
        raise _http(400, "BAD_ID", "Invalid webhook id.")
    wh = db.query(Webhook).filter(Webhook.id == wid, Webhook.owner_id == user.id).first()
    if not wh:
        raise _http(404, "NOT_FOUND", "Webhook not found.")
    db.delete(wh)
    db.commit()
