import pandas as pd

from app.services import cleaning_engine


def test_median_imputation():
    df = pd.DataFrame({"a": [1.0, 2.0, None, 4.0]})
    recs = [{"column_name": "a", "issue_type": "missing_values", "recommendation": "median_imputation"}]
    out, diff = cleaning_engine.apply_transforms(df, recs)
    assert out["a"].isna().sum() == 0
    # median of [1,2,4] = 2
    assert out["a"].iloc[2] == 2.0


def test_drop_duplicates():
    df = pd.DataFrame({"a": [1, 1, 2]})
    recs = [{"column_name": None, "issue_type": "duplicates", "recommendation": "drop_duplicates"}]
    out, diff = cleaning_engine.apply_transforms(df, recs)
    assert len(out) == 2
    assert diff["row_count_change"] == -1


def test_cap_outliers():
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]})
    recs = [{"column_name": "a", "issue_type": "outliers", "recommendation": "cap_outliers"}]
    out, diff = cleaning_engine.apply_transforms(df, recs)
    # 100 should be capped to upper bound (~8.5)
    assert out["a"].max() < 50


def test_drop_column_high_missing():
    df = pd.DataFrame({"a": [1.0, None, None, None], "b": [1, 2, 3, 4]})
    recs = [{"column_name": "a", "issue_type": "missing_values", "recommendation": "drop_column"}]
    out, diff = cleaning_engine.apply_transforms(df, recs)
    assert "a" not in out.columns
    assert diff["column_count_after"] == 1


def test_diff_summary_contents():
    df = pd.DataFrame({"a": [1, 1, 2]})
    recs = [{"column_name": None, "issue_type": "duplicates", "recommendation": "drop_duplicates"}]
    out, diff = cleaning_engine.apply_transforms(df, recs)
    assert "per_column_missing" in diff
    assert diff["row_count_before"] == 3
    assert diff["row_count_after"] == 2
