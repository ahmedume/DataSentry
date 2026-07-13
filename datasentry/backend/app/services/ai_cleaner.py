from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import settings
from app.services import llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a data-cleaning assistant. You receive a dataset profiling summary with computed statistics. "
    "For each detected issue (missing values, duplicates, outliers, type mismatches) produce exactly one "
    "recommendation. "
    "STRICT RULES: "
    "1. The 'stat_reference' field MUST contain a real number from the profiling (e.g. '18.4% missing'). "
    "2. The 'rationale' field MUST restate that same number and explain the suggested method. "
    "3. Do NOT recommend anything without a traceable statistic. "
    "Respond with ONLY a JSON array of objects: "
    '[{"column":str|null,"issue_type":str,"stat_reference":str,"recommendation":str,"rationale":str}, ...]. '
    "issue_type is one of: missing_values, duplicates, outliers, type_mismatch. "
    "recommendation is one of: median_imputation, mean_imputation, mode_imputation, drop_column, "
    "drop_duplicates, cap_outliers, remove_outliers, type_coercion."
)


def build_recommendations(profile: dict) -> list[dict]:
    """Return a list of recommendation dicts, each with a traceable stat_reference (SRS-4.2)."""
    if settings.has_llm:
        user = "PROFILING:\n" + json.dumps(profile, default=str)
        result = llm.call_llm_json(SYSTEM_PROMPT, user, max_tokens=3000)
        if isinstance(result, list):
            recs = [r for r in result if _validate(r, profile)]
            if recs:
                return recs
    return _heuristic_recommendations(profile)


def _validate(r: dict, profile: dict) -> bool:
    required = {"issue_type", "stat_reference", "recommendation", "rationale"}
    if not required.issubset(r.keys()):
        return False
    # SRS-4.2: rationale must reference the same stat_reference value.
    if r["stat_reference"] not in r.get("rationale", ""):
        return False
    return True


def _heuristic_recommendations(profile: dict) -> list[dict]:
    cols = profile.get("columns", [])
    recs: list[dict] = []
    for c in cols:
        name = c["name"]
        missing_pct = c.get("missing_pct", 0.0)
        if missing_pct == 0:
            continue
        missing_pct_str = f"{missing_pct*100:.1f}% missing"
        if missing_pct > 0.5:
            recs.append({
                "column_name": name,
                "issue_type": "missing_values",
                "stat_reference": missing_pct_str,
                "recommendation": "drop_column",
                "rationale": f"{name} is {missing_pct_str}; dropping the column is recommended over imputing >50% of its values.",
            })
        elif c.get("is_numeric"):
            skew = c.get("skew")
            method = "median_imputation" if (skew is not None and abs(skew) > 0.5) else "mean_imputation"
            recs.append({
                "column_name": name,
                "issue_type": "missing_values",
                "stat_reference": missing_pct_str,
                "recommendation": method,
                "rationale": f"{name} is {missing_pct_str}; {method.replace('_',' ')} is recommended"
                + (f" because the distribution is skewed (skew={skew:.2f})." if skew is not None else "."),
            })
        else:
            recs.append({
                "column_name": name,
                "issue_type": "missing_values",
                "stat_reference": missing_pct_str,
                "recommendation": "mode_imputation",
                "rationale": f"{name} is {missing_pct_str}; mode imputation is recommended for this categorical column.",
            })

    if profile.get("duplicate_row_count", 0) > 0:
        recs.append({
            "column_name": None,
            "issue_type": "duplicates",
            "stat_reference": f"{profile['duplicate_row_count']} duplicate rows",
            "recommendation": "drop_duplicates",
            "rationale": f"{profile['duplicate_row_count']} duplicate rows detected; removing exact duplicates is recommended to avoid bias.",
        })

    for c in cols:
        name = c["name"]
        if c.get("outlier_count", 0) > 0 and c.get("is_numeric"):
            recs.append({
                "column_name": name,
                "issue_type": "outliers",
                "stat_reference": f"{c['outlier_count']} outliers",
                "recommendation": "cap_outliers",
                "rationale": f"{name} has {c['outlier_count']} outliers (IQR method); capping them is recommended to reduce distortion.",
            })
    return recs
