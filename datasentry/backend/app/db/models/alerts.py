from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Uuid

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Uuid, primary_key=True, default=_uuid)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    scope_type = Column(String, nullable=False)  # monitor | dataset
    scope_id = Column(Uuid, nullable=False)
    metric = Column(String, nullable=False, default="drift_psi")  # drift_psi | drift_status
    operator = Column(String, nullable=False, default=">=")
    threshold = Column(String, nullable=False, default="0.2")
    channels_json = Column(Text, nullable=False, default='["slack"]')
    enabled = Column(String, nullable=False, default="true")
    created_at = Column(DateTime(timezone=True), default=_now)


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Uuid, primary_key=True, default=_uuid)
    rule_id = Column(Uuid, ForeignKey("alert_rules.id"), nullable=False)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False, default="")
    payload_json = Column(Text, nullable=False, default="{}")
    delivered = Column(String, nullable=False, default="false")
    created_at = Column(DateTime(timezone=True), default=_now)
