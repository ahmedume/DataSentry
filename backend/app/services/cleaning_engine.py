from __future__ import annotations

import pandas as pd

from app.services import quality_checks as qc


def _missing_pct(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns or len(df) == 0:
        return 0.0
    return round(float(df[col].isna().sum()) / len(df), 4)


def apply_transforms(df: pd.DataFrame, recs: list[dict]) -> tuple[pd.DataFrame, dict]:
    """Apply accepted cleaning recommendations in the fixed order from SRS-4.5:

    imputation -> duplicate removal -> outlier handling -> type coercion.
    `recs` is a list of dicts with keys: column_name, issue_type, recommendation.
    """
    df_out = df.copy()
    row_before = len(df_out)
    col_before = df_out.shape[1]

    impute = [r for r in recs if r.get("issue_type") == "missing_values"]
    dups = [r for r in recs if r.get("issue_type") == "duplicates"]
    outliers = [r for r in recs if r.get("issue_type") == "outliers"]
    types = [r for r in recs if r.get("issue_type") == "type_mismatch"]

    # 1) Imputation / drop-column for missing values
    for r in impute:
        col = r.get("column_name")
        if not col or col not in df_out.columns:
            continue
        method = r.get("recommendation")
        if method == "drop_column":
            df_out = df_out.drop(columns=[col])
        elif method == "median_imputation":
            med = pd.to_numeric(df_out[col], errors="coerce").median()
            df_out[col] = pd.to_numeric(df_out[col], errors="coerce").fillna(med)
        elif method == "mean_imputation":
            mean = pd.to_numeric(df_out[col], errors="coerce").mean()
            df_out[col] = pd.to_numeric(df_out[col], errors="coerce").fillna(mean)
        elif method == "mode_imputation":
            mode = df_out[col].mode()
            if not mode.empty:
                df_out[col] = df_out[col].fillna(mode.iloc[0])

    # 2) Duplicate removal (dataset-level)
    if dups:
        df_out = df_out.drop_duplicates()

    # 3) Outlier handling
    for r in outliers:
        col = r.get("column_name")
        if not col or col not in df_out.columns or not qc.is_numeric_series(df_out[col]):
            continue
        vals = pd.to_numeric(df_out[col], errors="coerce")
        q1 = vals.quantile(0.25)
        q3 = vals.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        if r.get("recommendation") == "cap_outliers":
            df_out[col] = df_out[col].clip(lower=lower, upper=upper)
        elif r.get("recommendation") == "remove_outliers":
            mask = (vals >= lower) & (vals <= upper)
            df_out = df_out[mask]

    # 4) Type coercion
    for r in types:
        col = r.get("column_name")
        if not col or col not in df_out.columns:
            continue
        df_out[col] = pd.to_numeric(df_out[col], errors="coerce")

    row_after = len(df_out)
    col_after = df_out.shape[1]

    columns_before = list(df.columns)
    columns_after = list(df_out.columns)
    per_column_missing = [
        {
            "column": c,
            "missing_pct_before": _missing_pct(df, c),
            "missing_pct_after": _missing_pct(df_out, c),
        }
        for c in columns_after
    ]

    diff = {
        "row_count_before": row_before,
        "row_count_after": row_after,
        "row_count_change": row_after - row_before,
        "column_count_before": col_before,
        "column_count_after": col_after,
        "per_column_missing": per_column_missing,
    }
    return df_out, diff
