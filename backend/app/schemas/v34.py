from __future__ import annotations

from pydantic import BaseModel


# ---- Teams -----------------------------------------------------------------
class TeamCreate(BaseModel):
    name: str


class TeamMemberAdd(BaseModel):
    email: str
    role: str = "member"  # owner | admin | member | viewer


class TeamMemberUpdate(BaseModel):
    role: str


class TeamOut(BaseModel):
    id: str
    name: str
    owner_id: str
    created_at: str | None = None


class TeamMemberOut(BaseModel):
    user_id: str
    email: str
    display_name: str
    role: str


# ---- Annotations -----------------------------------------------------------
class AnnotationCreate(BaseModel):
    body: str
    column_name: str | None = None


class AnnotationOut(BaseModel):
    id: str
    dataset_id: str
    author_id: str
    column_name: str | None
    body: str
    created_at: str | None = None


# ---- Webhooks --------------------------------------------------------------
class WebhookCreate(BaseModel):
    url: str
    events: list[str]
    secret: str | None = None


class WebhookOut(BaseModel):
    id: str
    url: str
    events: list[str]
    active: bool
    full_secret: str | None = None  # returned only on creation
    created_at: str | None = None


# ---- Models / registry -----------------------------------------------------
class ModelPromote(BaseModel):
    stage: str  # dev | staging | production


class PredictRequest(BaseModel):
    instances: list[dict]


class PredictResponse(BaseModel):
    predictions: list
    probabilities: list[list[float]] | None = None
    task: str | None = None


class ModelOut(BaseModel):
    id: str
    target: str
    task: str
    status: str
    stage: str
    metrics: dict
    feature_importances: dict
    current: bool = False
    created_at: str | None = None


# ---- Audit / usage ---------------------------------------------------------
class AuditOut(BaseModel):
    id: str
    actor_id: str | None
    team_id: str | None
    action: str
    target_type: str | None
    target_id: str | None
    meta: dict
    created_at: str | None = None


class UsageOut(BaseModel):
    endpoint: str
    day: str
    count: int
