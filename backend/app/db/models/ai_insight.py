from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AiInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(Uuid, primary_key=True, default=_uuid)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    column_explanations = Column(JSON, nullable=False)
    candidate_targets = Column(JSON, nullable=False)
    possible_tasks = Column(JSON, nullable=False)
    risks_and_assumptions = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    dataset = relationship("Dataset", back_populates="insights")
