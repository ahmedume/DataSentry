from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import relationship

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Uuid, primary_key=True, default=_uuid)
    key_id = Column(String, unique=True, index=True, nullable=False)
    key_hash = Column(String, nullable=False)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False, default="default")
    scopes = Column(Text, nullable=False, default="[]")  # JSON list, e.g. ["datasets:read"]
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    last_used_at = Column(DateTime(timezone=True))

    owner = relationship("User", back_populates="api_keys")
