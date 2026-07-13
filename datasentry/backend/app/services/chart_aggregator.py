from __future__ import annotations

import pandas as pd

from app.services import quality_checks as qc

HIST_BINS = 10
CATEGORICAL_TOP_N = 10


def numeric_histogram(df: pd.DataFrame, column: str, bins: int = HIST_BINS) -> dict:
    if column not in df.columns or not qc.is_numeric_series(df[column]):
        return {"column": column, "bins": [], "counts": [], "omitted": True}
    vals = pd.to_numeric(df[column], errors="coerce").dropna()
    if len(vals) == 0:
        return {"column": column, "bins": [], "counts": [], "omitted": True}
    counts, edges = np_histogram_safe(vals, bins)
    return {
        "column": column,
        "bins": [round(float(e), 4) for e in edges],
        "counts": [int(c) for c in counts],
        "omitted": False,
    }


def np_histogram_safe(vals, bins: int):
    try:
        counts, edges = pd.cut(vals, bins=bins, include_lowest=True, retbins=True)
        # pd.cut returns IntervalIndex; recompute counts via value_counts
        counts = vals.groupby(pd.cut(vals, bins=bins, include_lowest=True), observed=False).count()
        return list(counts.values), list(edges)
    except Exception:
        import numpy as np

        counts, edges = np.histogram(vals, bins=bins)
        return list(counts), list(edges)


def categorical_bars(df: pd.DataFrame, column: str, top_n: int = CATEGORICAL_TOP_N) -> dict:
    if column not in df.columns:
        return {"column": column, "categories": [], "counts": [], "omitted": True, "reason": "column not found"}
    unique = df[column].nunique(dropna=True)
    if unique > qc.CATEGORICAL_MAX_CARDINALITY:
        return {
            "column": column,
            "categories": [],
            "counts": [],
            "omitted": True,
            "reason": "high cardinality (>{}) — chart omitted".format(qc.CATEGORICAL_MAX_CARDINALITY),
        }
    vc = df[column].value_counts(dropna=True).head(top_n)
    return {
        "column": column,
        "categories": [str(i) for i in vc.index.tolist()],
        "counts": [int(v) for v in vc.values.tolist()],
        "omitted": False,
        "reason": None,
    }


def missingness(df: pd.DataFrame) -> dict:
    cols = list(df.columns)
    pcts = [round(float(df[c].isna().sum()) / len(df), 4) if len(df) else 0.0 for c in cols]
    return {"columns": cols, "missing_pct": pcts}
