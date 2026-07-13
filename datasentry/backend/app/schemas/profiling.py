from __future__ import annotations

from pydantic import BaseModel


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    count: int
    missing_count: int
    missing_pct: float
    high_missing: bool
    unique_count: int
    is_numeric: bool
    is_categorical: bool
    mean: float | None = None
    std: float | None = None
    min: float | None = None
    q1: float | None = None
    median: float | None = None
    q3: float | None = None
    max: float | None = None
    skew: float | None = None
    outlier_count: int = 0
    cardinality: int = 0


class ProfilingOut(BaseModel):
    dataset_id: str
    row_count: int
    column_count: int
    byte_size: int
    duplicate_row_count: int
    columns: list[ColumnProfile]
