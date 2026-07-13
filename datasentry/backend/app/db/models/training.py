from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Uuid

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id = Column(Uuid, primary_key=True, default=_uuid)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    team_id = Column(Uuid, ForeignKey("teams.id"), nullable=True)
    dataset_id = Column(Uuid, ForeignKey("datasets.id"), nullable=True)
    connector_id = Column(Uuid, ForeignKey("connectors.id"), nullable=True)
    target = Column(String, nullable=False)
    task = Column(String, nullable=False, default="auto")  # auto | classification | regression
    status = Column(String, nullable=False, default="QUEUED")  # QUEUED | RUNNING | READY | FAILED
    metrics_json = Column(Text, nullable=False, default="{}")
    feature_importances_json = Column(Text, nullable=False, default="{}")
    model_path = Column(String, nullable=True)
    stage = Column(String, nullable=False, default="dev")  # dev | staging | production
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)
    finished_at = Column(DateTime(timezone=True))
