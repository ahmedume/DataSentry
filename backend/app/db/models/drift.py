from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Uuid

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DriftSnapshot(Base):
    """A stored profile snapshot of a dataset, used as a drift baseline/comparison."""

    __tablename__ = "drift_snapshots"

    id = Column(Uuid, primary_key=True, default=_uuid)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    dataset_id = Column(Uuid, ForeignKey("datasets.id"), nullable=False)
    label = Column(String, nullable=False, default="")
    profile_json = Column(Text, nullable=False, default="{}")
    sample_path = Column(String, nullable=True)  # CSV sample of the data at snapshot time
    row_count = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)


class DriftComparison(Base):
    """Result of comparing a baseline snapshot against a current snapshot."""

    __tablename__ = "drift_comparisons"

    id = Column(Uuid, primary_key=True, default=_uuid)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    baseline_id = Column(Uuid, ForeignKey("drift_snapshots.id"), nullable=False)
    current_id = Column(Uuid, ForeignKey("drift_snapshots.id"), nullable=False)
    results_json = Column(Text, nullable=False, default="{}")
    status = Column(String, nullable=False, default="UNKNOWN")  # STABLE | WARNING | ALERT
    created_at = Column(DateTime(timezone=True), default=_now)
