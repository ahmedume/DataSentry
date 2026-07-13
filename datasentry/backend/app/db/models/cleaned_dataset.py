from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, Column, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import relationship

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CleanedDataset(Base):
    __tablename__ = "cleaned_datasets"

    id = Column(Uuid, primary_key=True, default=_uuid)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String, nullable=False)
    applied_recommendation_ids = Column(JSON, nullable=False)
    row_count_before = Column(BigInteger, nullable=False)
    row_count_after = Column(BigInteger, nullable=False)
    diff_summary = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    dataset = relationship("Dataset", back_populates="cleaned")
