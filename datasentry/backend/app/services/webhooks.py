from __future__ import annotations

import hashlib
import hmac
import json
import logging
import urllib.request

from sqlalchemy.orm import Session

from app.db.models import TeamMembership, User, Webhook

logger = logging.getLogger(__name__)


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def fire_event(db: Session, event_type: str, payload: dict, owner_id=None, team_id=None) -> int:
    """Deliver event_type to all matching active webhooks. Returns count delivered."""
    hooks = db.query(Webhook).filter(Webhook.active == "true")
    if team_id:
        hooks = hooks.filter(Webhook.team_id == team_id)
    else:
        hooks = hooks.filter(Webhook.owner_id == owner_id)
    hooks = hooks.all()

    delivered = 0
    for wh in hooks:
        try:
            events = json.loads(wh.events or "[]")
        except json.JSONDecodeError:
            events = []
        if event_type not in events and "*" not in events:
            continue
        body = json.dumps({"event": event_type, "payload": payload}).encode("utf-8")
        req = urllib.request.Request(
            wh.url,
            data=body,
            headers={"Content-Type": "application/json", "X-DataSentry-Signature": _sign(wh.secret, body)},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status < 400:
                    delivered += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Webhook %s delivery failed: %s", wh.id, exc)
    return delivered


def send_for_user(db: Session, event_type: str, payload: dict, user: User, team_id=None) -> int:
    return fire_event(db, event_type, payload, owner_id=user.id, team_id=team_id)
