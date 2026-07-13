from __future__ import annotations

from pydantic import BaseModel


class ConnectorCreate(BaseModel):
    name: str
    type: str  # local | postgres | s3
    config: dict


class ConnectorOut(BaseModel):
    id: str
    name: str
    type: str
    config: dict
    enabled: bool
    last_tested_at: str | None = None
    last_error: str | None = None
    created_at: str | None = None


class ConnectorTestResult(BaseModel):
    ok: bool
    error: str | None = None


class ConnectorIngestResult(BaseModel):
    dataset_id: str | None = None
    status: str
