from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import relationship

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Connector(Base):
    """A registered data source (local file drop, database, or object store)."""

    __tablename__ = "connectors"

    id = Column(Uuid, primary_key=True, default=_uuid)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    team_id = Column(Uuid, ForeignKey("teams.id"), nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # local | postgres | s3
    config = Column(Text, nullable=False, default="{}")  # JSON (secrets redacted at read time)
    enabled = Column(String, nullable=False, default="true")
    last_tested_at = Column(DateTime(timezone=True))
    last_error = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)
