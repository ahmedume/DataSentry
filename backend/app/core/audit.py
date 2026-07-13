from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import AuditLog


def record_audit(
    db: Session,
    action: str,
    actor_id=None,
    team_id=None,
    target_type: str | None = None,
    target_id: str | None = None,
    meta: dict | None = None,
) -> None:
    """Append an immutable audit entry. Best-effort: never raises."""
    try:
        db.add(
            AuditLog(
                actor_id=str(actor_id) if actor_id is not None else None,
                team_id=str(team_id) if team_id is not None else None,
                action=action,
                target_type=target_type,
                target_id=str(target_id) if target_id is not None else None,
                meta_json=json.dumps(meta or {}),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
