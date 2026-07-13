from __future__ import annotations

from pydantic import BaseModel


class NumericHistogram(BaseModel):
    column: str
    bins: list[float]
    counts: list[int]
    omitted: bool = False


class CategoricalBars(BaseModel):
    column: str
    categories: list[str]
    counts: list[int]
    omitted: bool = False
    reason: str | None = None


class MissingnessBars(BaseModel):
    columns: list[str]
    missing_pct: list[float]
