from __future__ import annotations

from pydantic import BaseModel


class StartTrainingRequest(BaseModel):
    target: str
    task: str = "auto"  # auto | classification | regression
    source_type: str = "dataset"  # dataset | connector
    source_id: str


class TrainingJobOut(BaseModel):
    id: str
    dataset_id: str | None = None
    connector_id: str | None = None
    target: str
    task: str
    status: str
    metrics: dict | None = None
    feature_importances: dict | None = None
    model_path: str | None = None
    error_message: str | None = None
    created_at: str | None = None
