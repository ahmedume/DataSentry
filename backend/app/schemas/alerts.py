from __future__ import annotations

from pydantic import BaseModel


class AlertRuleCreate(BaseModel):
    name: str
    scope_type: str  # monitor | dataset
    scope_id: str
    metric: str = "drift_psi"  # drift_psi | drift_status
    operator: str = ">="
    threshold: str = "0.2"
    channels: list[str] = ["slack"]
    enabled: bool = True


class AlertRuleOut(BaseModel):
    id: str
    name: str
    scope_type: str
    scope_id: str
    metric: str
    operator: str
    threshold: str
    channels: list[str]
    enabled: bool
    created_at: str | None = None


class AlertEventOut(BaseModel):
    id: str
    rule_id: str
    message: str
    delivered: bool
    payload: dict
    created_at: str | None = None
