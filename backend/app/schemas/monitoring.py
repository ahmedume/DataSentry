from __future__ import annotations

from pydantic import BaseModel


class MonitorScheduleCreate(BaseModel):
    name: str
    source_type: str  # dataset | connector
    source_id: str
    cadence_minutes: int = 1440
    baseline_snapshot_id: str | None = None
    drift_threshold: float = 0.2


class MonitorScheduleOut(BaseModel):
    id: str
    name: str
    source_type: str
    source_id: str
    cadence_minutes: int
    enabled: bool
    baseline_snapshot_id: str | None = None
    drift_threshold: float
    last_run_at: str | None = None


class MonitorRunOut(BaseModel):
    id: str
    schedule_id: str
    status: str
    drift_status: str | None = None
    rows_processed: int | None = None
    drift_summary: dict | None = None
    snapshot_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
