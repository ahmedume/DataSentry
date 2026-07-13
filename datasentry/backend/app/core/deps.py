from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.rbac import has_team_role
from app.core.security import decode_jwt
from app.db.models import ApiKey, Team, TeamMembership, User
from app.db.session import get_db


def _http(status: int, code: str, message: str):
    return HTTPException(status_code=status, detail={"error_code": code, "message": message})


def get_team_id_header(request: Request) -> str | None:
    raw = request.headers.get("x-team-id")
    return raw.strip() if raw else None


def require_team_role(min_role: str):
    """Dependency: the user must be a member of the team in X-Team-Id with >= min_role."""

    def checker(
        request: Request,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> TeamMembership:
        team_id = get_team_id_header(request)
        if not team_id:
            raise _http(400, "TEAM_REQUIRED", "X-Team-Id header is required.")
        try:
            tid = uuid.UUID(team_id)
        except ValueError:
            raise _http(400, "BAD_TEAM", "Invalid team id.")
        m = db.query(TeamMembership).filter(TeamMembership.user_id == user.id, TeamMembership.team_id == tid).first()
        if not m:
            raise _http(403, "FORBIDDEN", "You are not a member of this team.")
        if not has_team_role(db, user, tid, min_role):
            raise _http(403, "FORBIDDEN", f"Requires team role >= {min_role}.")
        return m

    return checker


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise _http(401, "UNAUTHORIZED", "Missing bearer token.")
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = decode_jwt(token)
    except Exception:
        raise _http(401, "UNAUTHORIZED", "Invalid or expired token.")
    user_id = payload.get("sub")
    if not user_id:
        raise _http(401, "UNAUTHORIZED", "Invalid token subject.")
    try:
        user = db.get(User, uuid.UUID(user_id))
    except ValueError:
        raise _http(401, "UNAUTHORIZED", "Invalid token subject.")
    if not user or not user.is_active:
        raise _http(401, "UNAUTHORIZED", "User not found or inactive.")
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = decode_jwt(token)
        user = db.get(User, uuid.UUID(payload["sub"]))
        return user if user and user.is_active else None
    except Exception:
        return None


def get_current_api_key(request: Request, db: Session = Depends(get_db)) -> tuple[User, ApiKey]:
    key = request.headers.get("x-api-key", "")
    if not key:
        raise _http(401, "UNAUTHORIZED", "Missing X-API-Key header.")
    h = hashlib.sha256(key.encode()).hexdigest()
    api_key = db.query(ApiKey).filter(ApiKey.key_hash == h, ApiKey.active.is_(True)).first()
    if not api_key:
        raise _http(401, "UNAUTHORIZED", "Invalid API key.")
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    owner = db.get(User, api_key.owner_id)
    if not owner or not owner.is_active:
        raise _http(401, "UNAUTHORIZED", "API key owner inactive.")
    return owner, api_key


def require_dataset_access(dataset_id: str, user: User, db: Session) -> Dataset:
    """Fetch a dataset and verify the user is allowed to access it (owner or unowned)."""
    from app.db.models import Dataset as _Dataset

    try:
        uid = uuid.UUID(dataset_id)
    except ValueError:
        raise _http(404, "NOT_FOUND", "Dataset not found.")
    ds = db.get(_Dataset, uid)
    if not ds:
        raise _http(404, "NOT_FOUND", "Dataset not found.")
    if ds.owner_id is not None and ds.owner_id != user.id:
        raise _http(403, "FORBIDDEN", "You do not own this dataset.")
    return ds


def require_scopes(required: list[str]):
    def checker(request: Request, auth: tuple[User, ApiKey] = Depends(get_current_api_key)) -> tuple[User, ApiKey]:
        owner, api_key = auth
        scopes = json.loads(api_key.scopes or "[]")
        if "*" not in scopes and not all(s in scopes for s in required):
            raise _http(403, "FORBIDDEN", "API key lacks required scope.")
        return auth

    return checker
