from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import Request, Response
from sqlalchemy.orm import Session

from app.core.security import decode_jwt
from app.db.models import ApiUsage
from app.db.session import SessionLocal


class UsageMiddleware:
    """Counts API requests per actor/day/endpoint for metering.

    Actor is derived from the bearer token subject when present; anonymous
    requests are counted under a null user. Failures are swallowed so metering
    never breaks the request path.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path
        actor_id = None
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            try:
                payload = decode_jwt(auth.split(" ", 1)[1].strip())
                actor_id = payload.get("sub")
            except Exception:
                actor_id = None

        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            db: Session = SessionLocal()
            try:
                row = (
                    db.query(ApiUsage)
                    .filter(ApiUsage.user_id == (actor_id), ApiUsage.endpoint == path, ApiUsage.day == day)
                    .first()
                )
                if row:
                    row.count = (row.count or 0) + 1
                else:
                    db.add(ApiUsage(user_id=actor_id, endpoint=path, day=day, count=1))
                db.commit()
            finally:
                db.close()
        except Exception:
            pass

        await self.app(scope, receive, send)
