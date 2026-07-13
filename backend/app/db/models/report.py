from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.schema import CheckConstraint

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Report(Base):
    __tablename__ = "reports"

    id = Column(Uuid, primary_key=True, default=_uuid)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String, nullable=True)
    status = Column(String, nullable=False, default="QUEUED")
    error_message = Column(String)
    created_at = Column(DateTime(timezone=True), default=_now)

    dataset = relationship("Dataset", back_populates="report")


Report.__table__.append_constraint(
    CheckConstraint(
        "status IN ('QUEUED','GENERATING','READY','FAILED')",
        name="ck_reports_status",
    )
)
