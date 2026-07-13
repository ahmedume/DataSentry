from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.schema import CheckConstraint

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Uuid, primary_key=True, default=_uuid)
    original_filename = Column(String, nullable=False)
    status = Column(String, nullable=False, default="UPLOADED")
    file_path = Column(String, nullable=False)
    row_count = Column(BigInteger)
    column_count = Column(BigInteger)
    byte_size = Column(BigInteger)
    error_message = Column(Text)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=True)
    team_id = Column(Uuid, ForeignKey("teams.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    profiling = relationship("ProfilingResult", back_populates="dataset", uselist=False, cascade="all, delete-orphan")
    insights = relationship("AiInsight", back_populates="dataset", uselist=False, cascade="all, delete-orphan")
    recommendations = relationship("CleaningRecommendation", back_populates="dataset", cascade="all, delete-orphan")
    cleaned = relationship("CleanedDataset", back_populates="dataset", uselist=False, cascade="all, delete-orphan")
    report = relationship("Report", back_populates="dataset", uselist=False, cascade="all, delete-orphan")


Dataset.__table__.append_constraint(
    CheckConstraint(
        "status IN ('UPLOADED','QUEUED','PROFILING','READY','FAILED')",
        name="ck_datasets_status",
    )
)
