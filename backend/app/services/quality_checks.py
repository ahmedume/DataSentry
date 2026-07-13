from __future__ import annotations

import math

import numpy as np
import pandas as pd


HIGH_MISSING_THRESHOLD = 0.05
OUTLIER_IQR_K = 1.5
CATEGORICAL_MAX_CARDINALITY = 50


def is_numeric_series(s: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(s):
        return True
    # A string/object column that is mostly parseable numbers counts as numeric.
    coerced = pd.to_numeric(s, errors="coerce")
    non_null = s.dropna()
    if len(non_null) == 0:
        return False
    parsed_ratio = coerced.notna().sum() / len(non_null)
    return bool(parsed_ratio >= 0.9)


def numeric_outliers(s: pd.Series) -> tuple[int, dict]:
    """Return (outlier_count, stats_dict) for a numeric series using IQR method.

    An outlier is a value < Q1 - 1.5*IQR or > Q3 + 1.5*IQR.
    """
    vals = pd.to_numeric(s, errors="coerce").dropna()
    if len(vals) < 4:
        return 0, {}
    q1 = float(vals.quantile(0.25))
    q3 = float(vals.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - OUTLIER_IQR_K * iqr
    upper = q3 + OUTLIER_IQR_K * iqr
    outliers = vals[(vals < lower) | (vals > upper)]
    stats = {
        "mean": float(vals.mean()),
        "std": float(vals.std()),
        "min": float(vals.min()),
        "q1": q1,
        "median": float(vals.median()),
        "q3": q3,
        "max": float(vals.max()),
        "skew": float(vals.skew()) if len(vals) > 2 else 0.0,
    }
    return int(outliers.shape[0]), stats


def duplicate_row_count(df: pd.DataFrame) -> int:
    """Exact full-row duplicates only (per SRS-2.4)."""
    return int(df.duplicated().sum())


def column_profile(name: str, s: pd.Series) -> dict:
    count = int(len(s))
    missing = int(s.isna().sum())
    missing_pct = missing / count if count else 0.0
    unique = int(s.nunique(dropna=True))
    numeric = is_numeric_series(s)
    categorical = (not numeric) and (unique <= CATEGORICAL_MAX_CARDINALITY) and (unique > 1)

    prof: dict = {
        "name": name,
        "dtype": str(s.dtype),
        "count": int(count),
        "missing_count": int(missing),
        "missing_pct": round(float(missing_pct), 4),
        "high_missing": bool(missing_pct > HIGH_MISSING_THRESHOLD),
        "unique_count": int(unique),
        "is_numeric": bool(numeric),
        "is_categorical": bool(categorical),
        "outlier_count": 0,
        "cardinality": int(unique),
    }
    if numeric:
        outlier_count, stats = numeric_outliers(s)
        prof["outlier_count"] = outlier_count
        prof.update(stats)
    return prof
