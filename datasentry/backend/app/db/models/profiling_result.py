from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, Column, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ProfilingResult(Base):
    __tablename__ = "profiling_results"

    id = Column(Uuid, primary_key=True, default=_uuid)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    column_profiles = Column(JSON, nullable=False)
    duplicate_row_count = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    dataset = relationship("Dataset", back_populates="profiling")
