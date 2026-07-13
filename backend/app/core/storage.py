from __future__ import annotations

import os
from pathlib import Path

from app.core.config import settings


class LocalStorage:
    """Local-disk storage behind a stable interface.

    Paths mirror a future MinIO/S3 bucket+key layout so v2 can swap the
    implementation without touching callers (per SDS.md Section 1/8).
    """

    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.STORAGE_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)

    def dataset_dir(self, dataset_id: str) -> Path:
        d = self.root / dataset_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def raw_path(self, dataset_id: str) -> Path:
        return self.dataset_dir(dataset_id) / "raw.csv"

    def cleaned_path(self, dataset_id: str) -> Path:
        return self.dataset_dir(dataset_id) / "cleaned.csv"

    def report_path(self, dataset_id: str) -> Path:
        return self.dataset_dir(dataset_id) / "report.pdf"

    def chart_dir(self, dataset_id: str) -> Path:
        d = self.dataset_dir(dataset_id) / "charts"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_raw(self, dataset_id: str, data: bytes) -> Path:
        p = self.raw_path(dataset_id)
        p.write_bytes(data)
        return p

    def write_cleaned(self, dataset_id: str, df) -> Path:
        p = self.cleaned_path(dataset_id)
        df.to_csv(p, index=False)
        return p

    def write_report(self, dataset_id: str, data: bytes) -> Path:
        p = self.report_path(dataset_id)
        p.write_bytes(data)
        return p

    def report_exists(self, dataset_id: str) -> bool:
        return self.report_path(dataset_id).exists()

    def cleaned_exists(self, dataset_id: str) -> bool:
        return self.cleaned_path(dataset_id).exists()

    def snapshot_path(self, snapshot_id: str) -> Path:
        return self.root / "snapshots" / f"{snapshot_id}.csv"

    def save_snapshot(self, snapshot_id: str, df) -> Path:
        p = self.snapshot_path(snapshot_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(p, index=False)
        return p

    def read_snapshot(self, snapshot_id: str):
        from app.services import profiler

        return profiler.read_csv(self.snapshot_path(snapshot_id))

    def model_path(self, job_id: str) -> Path:
        return self.root / "models" / f"{job_id}.pkl"

    def save_model(self, job_id: str, data: bytes) -> Path:
        p = self.model_path(job_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def model_exists(self, job_id: str) -> bool:
        return self.model_path(job_id).exists()


storage = LocalStorage()
