from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Uuid

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MonitorSchedule(Base):
    """Recurring profiling + drift check against a dataset or connector."""

    __tablename__ = "monitor_schedules"

    id = Column(Uuid, primary_key=True, default=_uuid)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    team_id = Column(Uuid, ForeignKey("teams.id"), nullable=True)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # dataset | connector
    source_id = Column(Uuid, nullable=False)
    cadence_minutes = Column(String, nullable=False, default="1440")
    enabled = Column(String, nullable=False, default="true")
    baseline_snapshot_id = Column(Uuid, ForeignKey("drift_snapshots.id"), nullable=True)
    drift_threshold = Column(String, nullable=False, default="0.2")  # PSI alert threshold
    last_run_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=_now)


class MonitorRun(Base):
    __tablename__ = "monitor_runs"

    id = Column(Uuid, primary_key=True, default=_uuid)
    schedule_id = Column(Uuid, ForeignKey("monitor_schedules.id"), nullable=False)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False, default="RUNNING")  # RUNNING | READY | FAILED
    started_at = Column(DateTime(timezone=True), default=_now)
    finished_at = Column(DateTime(timezone=True))
    rows_processed = Column(String, nullable=True)
    drift_status = Column(String, nullable=True)  # STABLE | WARNING | ALERT
    drift_summary_json = Column(Text, nullable=False, default="{}")
    snapshot_id = Column(Uuid, ForeignKey("drift_snapshots.id"), nullable=True)
    alert_event_id = Column(Uuid, nullable=True)
