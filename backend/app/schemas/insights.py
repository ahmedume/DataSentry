from __future__ import annotations

from pydantic import BaseModel


class ColumnExplanation(BaseModel):
    column: str
    explanation: str


class AiInsightOut(BaseModel):
    dataset_id: str
    column_explanations: list[ColumnExplanation]
    candidate_targets: list[str]
    possible_tasks: list[str]
    risks_and_assumptions: list[str]
    available: bool = True
