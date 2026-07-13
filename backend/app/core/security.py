from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from app.core.config import settings


class JWTError(Exception):
    pass


# --------------------------------------------------------------------------
# Password hashing (stdlib scrypt — no third-party dependency required)
# --------------------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=64)
    return base64.b64encode(salt + dk).decode("ascii")


def verify_password(password: str, stored: str) -> bool:
    try:
        raw = base64.b64decode(stored)
    except Exception:
        return False
    if len(raw) < 16:
        return False
    salt, dk = raw[:16], raw[16:]
    try:
        candidate = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=64)
    except Exception:
        return False
    return hmac.compare_digest(candidate, dk)


# --------------------------------------------------------------------------
# JWT (HMAC-SHA256, stdlib only)
# --------------------------------------------------------------------------
def _b64url(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def encode_jwt(payload: dict[str, Any], expires_minutes: int | None = None) -> str:
    secret = settings.JWT_SECRET
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    exp = now + (expires_minutes if expires_minutes is not None else settings.JWT_EXPIRE_MINUTES) * 60
    body = {**payload, "iat": now, "exp": exp}
    signing_input = _b64url(json.dumps(header, separators=(",", ":")).encode()) + b"." + _b64url(
        json.dumps(body, separators=(",", ":")).encode()
    )
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return (signing_input + b"." + _b64url(sig)).decode("ascii")


def decode_jwt(token: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        raise JWTError("Malformed token")
    signing_input = (header_b64 + "." + payload_b64).encode("utf-8")
    expected = _b64url(
        hmac.new(settings.JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    ).decode("ascii")
    if not hmac.compare_digest(expected, sig_b64):
        raise JWTError("Invalid signature")
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        raise JWTError("Invalid payload")
    if payload.get("exp", 0) < time.time():
        raise JWTError("Token expired")
    return payload


# --------------------------------------------------------------------------
# API keys (public id + hashed secret)
# --------------------------------------------------------------------------
def generate_api_key() -> tuple[str, str]:
    """Returns (key_id, full_key). Store only a hash of full_key."""
    key_id = secrets.token_hex(8)
    secret = secrets.token_urlsafe(32)
    return key_id, f"dsk_{key_id}_{secret}"


def hash_api_key(full_key: str) -> str:
    return hashlib.sha256(full_key.encode("utf-8")).hexdigest()


def verify_api_key(full_key: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_api_key(full_key), stored_hash)
