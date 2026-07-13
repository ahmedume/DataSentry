from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import (
    encode_jwt,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)
from app.db.models import ApiKey, User
from app.db.session import get_db
from app.schemas.auth import (
    ApiKeyCreate,
    ApiKeyOut,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    validate_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _http(status: int, code: str, message: str):
    return HTTPException(status_code=status, detail={"error_code": code, "message": message})


def _user_out(u: User) -> UserOut:
    return UserOut(id=str(u.id), email=u.email, display_name=u.display_name, is_active=u.is_active)


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if not settings.ALLOW_SIGNUP:
        raise _http(403, "SIGNUP_DISABLED", "Registration is disabled.")
    try:
        email = validate_email(body.email)
    except ValueError:
        raise _http(400, "INVALID_EMAIL", "Invalid email address.")
    if len(body.password) < 8:
        raise _http(400, "WEAK_PASSWORD", "Password must be at least 8 characters.")
    if db.query(User).filter(User.email == email).first():
        raise _http(409, "EMAIL_TAKEN", "An account with this email already exists.")
    user = User(
        email=email,
        display_name=body.display_name or email.split("@")[0],
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = encode_jwt({"sub": str(user.id), "email": user.email})
    return TokenResponse(access_token=token, user=_user_out(user))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    try:
        email = validate_email(body.email)
    except ValueError:
        raise _http(400, "INVALID_EMAIL", "Invalid email address.")
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise _http(401, "BAD_CREDENTIALS", "Incorrect email or password.")
    if not user.is_active:
        raise _http(403, "INACTIVE", "Account is inactive.")
    token = encode_jwt({"sub": str(user.id), "email": user.email})
    return TokenResponse(access_token=token, user=_user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.get("/api-keys", response_model=list[ApiKeyOut])
def list_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    keys = db.query(ApiKey).filter(ApiKey.owner_id == user.id).all()
    return [
        ApiKeyOut(
            id=str(k.id),
            key_id=k.key_id,
            name=k.name,
            scopes=json.loads(k.scopes or "[]"),
            active=k.active,
            created_at=k.created_at.isoformat() if k.created_at else None,
            full_key=None,
        )
        for k in keys
    ]


@router.post("/api-keys", response_model=ApiKeyOut, status_code=201)
def create_key(body: ApiKeyCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    key_id, full = generate_api_key()
    api_key = ApiKey(
        key_id=key_id,
        key_hash=hash_api_key(full),
        owner_id=user.id,
        name=body.name or "default",
        scopes=json.dumps(body.scopes or []),
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return ApiKeyOut(
        id=str(api_key.id),
        key_id=api_key.key_id,
        name=api_key.name,
        scopes=body.scopes or [],
        full_key=full,
        active=api_key.active,
    )


@router.delete("/api-keys/{key_id}", status_code=204)
def revoke_key(key_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    k = db.query(ApiKey).filter(ApiKey.key_id == key_id, ApiKey.owner_id == user.id).first()
    if not k:
        raise _http(404, "NOT_FOUND", "API key not found.")
    db.delete(k)
    db.commit()
