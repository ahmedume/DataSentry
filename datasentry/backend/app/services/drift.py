from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from app.services import profiler


# --------------------------------------------------------------------------
# Distribution-distance metrics (pure numpy/pandas — no scipy dependency)
# --------------------------------------------------------------------------
def psi(expected: list[float], actual: list[float], n_bins: int = 10) -> float:
    """Population Stability Index between two numeric samples."""
    exp = np.asarray(expected, dtype=float)
    act = np.asarray(actual, dtype=float)
    if exp.size == 0 or act.size == 0:
        return 0.0
    q = np.quantile(exp, np.linspace(0, 1, n_bins + 1))
    q = np.unique(q)
    if q.size < 2:
        return 0.0
    edges = q.copy()
    edges[0], edges[-1] = -np.inf, np.inf
    exp_perc = np.histogram(exp, bins=edges)[0] / len(exp)
    act_perc = np.histogram(act, bins=edges)[0] / len(act)
    exp_perc = np.clip(exp_perc, 1e-4, None)
    act_perc = np.clip(act_perc, 1e-4, None)
    return float(np.sum((act_perc - exp_perc) * np.log(act_perc / exp_perc)))


def ks_statistic(a: list[float], b: list[float]) -> float:
    """Two-sample Kolmogorov-Smirnov D statistic (manual, no scipy)."""
    x = np.sort(np.asarray(a, dtype=float))
    y = np.sort(np.asarray(b, dtype=float))
    if x.size == 0 or y.size == 0:
        return 0.0
    grid = np.concatenate([x, y])
    cdf_x = np.searchsorted(x, grid, side="right") / len(x)
    cdf_y = np.searchsorted(y, grid, side="right") / len(y)
    return float(np.max(np.abs(cdf_x - cdf_y)))


def categorical_drift(a: list[Any], b: list[Any]) -> float:
    """Total Variation Distance between two categorical samples."""
    sa = pd.Series(a)
    sb = pd.Series(b)
    va = sa.value_counts(normalize=True)
    vb = sb.value_counts(normalize=True)
    cats = set(va.index) | set(vb.index)
    tvd = sum(abs(va.get(c, 0.0) - vb.get(c, 0.0)) for c in cats)
    return float(0.5 * tvd)


# --------------------------------------------------------------------------
# Snapshot helpers
# --------------------------------------------------------------------------
def build_profile_json(df: pd.DataFrame, byte_size: int) -> dict:
    profile = profiler.profile_dataframe(df, byte_size)
    return {
        "row_count": profile["row_count"],
        "column_count": profile["column_count"],
        "duplicate_row_count": profile["duplicate_row_count"],
        "columns": profile["columns"],
    }


def compare_dataframes(
    baseline: pd.DataFrame,
    current: pd.DataFrame,
    threshold: float = 0.2,
) -> dict:
    """Compare two DataFrames column-by-column and return a drift report."""
    alert_threshold = max(threshold * 2.0, 0.5)
    columns: list[dict] = []
    max_drift = 0.0
    for col in baseline.columns:
        if col not in current.columns:
            continue
        b = baseline[col].dropna()
        c = current[col].dropna()
        if b.shape[0] < 2 or c.shape[0] < 2:
            continue
        numeric = pd.api.types.is_numeric_dtype(b) and pd.api.types.is_numeric_dtype(c)
        if numeric:
            score = max(psi(b.tolist(), c.tolist()), ks_statistic(b.tolist(), c.tolist()))
            method = "psi+ks"
        else:
            score = categorical_drift(b.tolist(), c.tolist())
            method = "categorical_tvd"
        status = "STABLE"
        if score > alert_threshold:
            status = "ALERT"
        elif score > threshold:
            status = "WARNING"
        columns.append({"name": col, "type": method, "drift_score": round(score, 4), "status": status})
        max_drift = max(max_drift, score)

    overall = "STABLE"
    if max_drift > alert_threshold:
        overall = "ALERT"
    elif max_drift > threshold:
        overall = "WARNING"
    return {
        "columns": columns,
        "max_drift": round(max_drift, 4),
        "status": overall,
        "threshold": threshold,
        "alert_threshold": alert_threshold,
    }
