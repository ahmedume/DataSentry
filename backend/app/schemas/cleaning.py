from __future__ import annotations

from pydantic import BaseModel


class RecommendationOut(BaseModel):
    id: str
    column_name: str | None
    issue_type: str
    stat_reference: str
    recommendation: str
    rationale: str
    accepted: bool = False


class ApplyCleaningRequest(BaseModel):
    accepted_recommendation_ids: list[str]


class DiffSummary(BaseModel):
    row_count_before: int
    row_count_after: int
    row_count_change: int
    column_count_before: int
    column_count_after: int
    per_column_missing: list[dict]


class CleaningStatusOut(BaseModel):
    dataset_id: str
    cleaning_available: bool
    cleaned_exists: bool
