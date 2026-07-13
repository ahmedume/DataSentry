from __future__ import annotations

import re

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(email: str) -> str:
    if not _EMAIL_RE.match(email or ""):
        raise ValueError("Invalid email address.")
    return email.lower().strip()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    is_active: bool


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = []


class ApiKeyOut(BaseModel):
    id: str
    key_id: str
    name: str
    scopes: list[str]
    full_key: str | None = None  # only returned on creation
    active: bool
    created_at: str | None = None


# avoid importing EmailStr at module top if not present; pydantic v2 ships it.
UserOut.model_rebuild()
