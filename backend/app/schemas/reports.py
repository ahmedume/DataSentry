from __future__ import annotations

from pydantic import BaseModel


class ReportStatusOut(BaseModel):
    dataset_id: str
    status: str
    error_message: str | None = None
    download_ready: bool = False
