import pandas as pd

from app.services import quality_checks as qc


def test_numeric_outliers_iqr():
    s = pd.Series([1, 2, 3, 4, 5, 100])
    count, stats = qc.numeric_outliers(s)
    assert count == 1
    assert stats["median"] == 3.5


def test_duplicate_row_count():
    df = pd.DataFrame({"a": [1, 1, 2], "b": [1, 1, 2]})
    assert qc.duplicate_row_count(df) == 1


def test_column_profile_missing_pct_and_high_flag():
    s = pd.Series([1, None, None, 4])
    prof = qc.column_profile("x", s)
    assert prof["missing_count"] == 2
    assert round(prof["missing_pct"], 4) == 0.5
    assert prof["high_missing"] is True
    assert prof["is_numeric"] is True


def test_is_numeric_series_string_numbers():
    s = pd.Series(["1", "2", "3", "4"])
    # fully parseable -> considered numeric
    assert qc.is_numeric_series(s) is True
    mixed = pd.Series(["1", "2", "3", "x"])
    # below the 0.9 parseable threshold -> not numeric
    assert qc.is_numeric_series(mixed) is False
