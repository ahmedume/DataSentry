from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str
    message: str


class JobStatus(BaseModel):
    dataset_id: str
    status: str
    error_message: str | None = None
