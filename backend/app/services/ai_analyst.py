from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import settings
from app.services import llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a meticulous data analyst. You are given a dataset profiling summary "
    "(computed statistics, types, missingness, outliers, duplicates) and a small sample of rows. "
    "Explain the dataset in plain English. "
    "STRICT RULES: "
    "1. Never invent a column meaning that is not inferable from its name, dtype, sample values, or stats. "
    "2. If a column's meaning is unclear from the data, say 'unclear from data' for it. "
    "3. Every claim must be traceable to a computed statistic. "
    "4. Respond with ONLY a JSON object matching this schema: "
    '{"column_explanations":[{"column":str,"explanation":str}],'
    '"candidate_targets":[str],"possible_tasks":[str],"risks_and_assumptions":[str]}.'
)


def _sample_rows(df, n: int = 50) -> list[dict]:
    return df.head(n).where(df.notna(), None).to_dict(orient="records")


def build_insights(profile: dict, sample_rows: list[dict]) -> dict:
    """Return insights dict. Uses the LLM when available, else deterministic heuristics."""
    if settings.has_llm:
        user = (
            "PROFILING:\n" + json.dumps(profile, default=str) + "\n\nSAMPLE ROWS (<=50):\n"
            + json.dumps(sample_rows, default=str)
        )
        result = llm.call_llm_json(SYSTEM_PROMPT, user)
        if result and _validate(result):
            result["generated_by"] = "llm"
            return result

    return _heuristic_insights(profile)


def _validate(result: dict) -> bool:
    required = {"column_explanations", "candidate_targets", "possible_tasks", "risks_and_assumptions"}
    if not required.issubset(result.keys()):
        return False
    if not isinstance(result["column_explanations"], list):
        return False
    return True


def _heuristic_insights(profile: dict) -> dict:
    cols = profile.get("columns", [])
    explanations = []
    targets = []
    risks = []
    for c in cols:
        if c.get("high_missing"):
            risks.append(f"{c['name']} has {c['missing_pct']*100:.1f}% missing values — imputation or removal advised.")
        if c.get("outlier_count", 0) > 0:
            risks.append(f"{c['name']} has {c['outlier_count']} outliers (IQR method) that may skew models.")
        if c.get("is_numeric"):
            explanations.append({"column": c["name"], "explanation": f"Numeric column ({c.get('dtype')}) with mean {c.get('mean')}."})
            targets.append(c["name"])
        else:
            explanations.append({"column": c["name"], "explanation": f"Categorical/text column with {c.get('cardinality')} unique values."})
    if profile.get("duplicate_row_count", 0) > 0:
        risks.append(f"Dataset contains {profile['duplicate_row_count']} exact duplicate rows.")
    return {
        "column_explanations": explanations,
        "candidate_targets": targets[:5],
        "possible_tasks": ["Regression" if targets else "Classification", "Clustering", "Data quality review"],
        "risks_and_assumptions": risks or ["No major quality risks detected from profiling."],
        "generated_by": "heuristic",
    }
