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


class CleaningRecommendation(Base):
    __tablename__ = "cleaning_recommendations"

    id = Column(Uuid, primary_key=True, default=_uuid)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    column_name = Column(String)  # NULL for dataset-level issues (e.g. duplicates)
    issue_type = Column(String, nullable=False)
    stat_reference = Column(String, nullable=False)
    recommendation = Column(String, nullable=False)
    rationale = Column(Text, nullable=False)
    accepted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    dataset = relationship("Dataset", back_populates="recommendations")
