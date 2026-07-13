from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Uuid

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Annotation(Base):
    """A user comment pinned to a dataset or a specific column."""

    __tablename__ = "annotations"

    id = Column(Uuid, primary_key=True, default=_uuid)
    dataset_id = Column(Uuid, ForeignKey("datasets.id"), nullable=False)
    author_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    column_name = Column(String, nullable=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)


class Webhook(Base):
    """Outbound webhook fired when a subscribed event occurs."""

    __tablename__ = "webhooks"

    id = Column(Uuid, primary_key=True, default=_uuid)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    team_id = Column(Uuid, ForeignKey("teams.id"), nullable=True)
    url = Column(String, nullable=False)
    secret = Column(String, nullable=False)
    events = Column(Text, nullable=False, default="[]")  # JSON list of event types
    active = Column(String, nullable=False, default="true")
    created_at = Column(DateTime(timezone=True), default=_now)


class AuditLog(Base):
    """Append-only record of significant actions for compliance."""

    __tablename__ = "audit_logs"

    id = Column(Uuid, primary_key=True, default=_uuid)
    actor_id = Column(String, nullable=True)
    team_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    target_type = Column(String, nullable=True)
    target_id = Column(String, nullable=True)
    meta_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), default=_now)


class ApiUsage(Base):
    """Daily per-actor request counters used for metering/billing."""

    __tablename__ = "api_usage"

    id = Column(Uuid, primary_key=True, default=_uuid)
    team_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    endpoint = Column(String, nullable=False)
    day = Column(String, nullable=False)  # YYYY-MM-DD
    count = Column("count", Integer, nullable=False, default=0)
