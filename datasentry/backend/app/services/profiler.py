from __future__ import annotations

import pandas as pd

from app.services import quality_checks as qc


def profile_dataframe(df: pd.DataFrame, byte_size: int) -> dict:
    """Compute the full profiling payload (SRS-2.1)."""
    columns = [qc.column_profile(name, df[name]) for name in df.columns]
    return {
        "row_count": int(len(df)),
        "column_count": int(df.shape[1]),
        "byte_size": int(byte_size),
        "duplicate_row_count": qc.duplicate_row_count(df),
        "columns": columns,
    }


def read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8")


def validate_csv_readable(path: str) -> None:
    """Raise on encoding/parse failure so callers can set FAILED (SRS-1.3/2.6)."""
    pd.read_csv(path, encoding="utf-8")
