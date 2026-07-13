from __future__ import annotations

from pydantic import BaseModel


class DatasetOut(BaseModel):
    id: str
    original_filename: str
    status: str
    row_count: int | None = None
    column_count: int | None = None
    byte_size: int | None = None
    error_message: str | None = None


class UploadResponse(BaseModel):
    dataset_id: str
    status: str
