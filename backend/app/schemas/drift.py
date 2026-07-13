from __future__ import annotations

from pydantic import BaseModel


class CreateSnapshotRequest(BaseModel):
    label: str | None = None


class DriftSnapshotOut(BaseModel):
    id: str
    dataset_id: str
    label: str
    row_count: int | None = None
    created_at: str | None = None


class DriftCompareRequest(BaseModel):
    baseline_id: str
    current_id: str


class DriftCompareDatasetRequest(BaseModel):
    snapshot_id: str
    dataset_id: str


class DriftComparisonOut(BaseModel):
    id: str
    baseline_id: str
    current_id: str
    status: str
    results: dict
    created_at: str | None = None
