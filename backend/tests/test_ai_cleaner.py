from app.services import ai_cleaner


def test_validate_rejects_missing_stat_reference():
    bad = {
        "issue_type": "missing_values",
        "stat_reference": "18.4% missing",
        "recommendation": "median_imputation",
        "rationale": "imputation recommended",
    }
    assert ai_cleaner._validate(bad, {}) is False


def test_validate_accepts_traceable_rationale():
    good = {
        "issue_type": "missing_values",
        "stat_reference": "18.4% missing",
        "recommendation": "median_imputation",
        "rationale": "18.4% missing; median imputation recommended.",
    }
    assert ai_cleaner._validate(good, {}) is True


def test_heuristic_recommendation_traceable():
    profile = {
        "row_count": 4,
        "column_count": 1,
        "duplicate_row_count": 0,
        "columns": [
            {"name": "age", "missing_pct": 0.6, "is_numeric": True, "skew": 1.2, "outlier_count": 0}
        ],
    }
    recs = ai_cleaner._heuristic_recommendations(profile)
    assert any(r["recommendation"] == "drop_column" for r in recs)
    for r in recs:
        assert r["stat_reference"] in r["rationale"]
