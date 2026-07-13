import pandas as pd

from app.services import profiler
from app.services import quality_checks as qc


def test_profile_dataframe_counts():
    df = pd.DataFrame({"a": [1, 2, None], "b": ["x", "x", "y"]})
    prof = profiler.profile_dataframe(df, byte_size=42)
    assert prof["row_count"] == 3
    assert prof["column_count"] == 2
    assert prof["byte_size"] == 42
    a = next(c for c in prof["columns"] if c["name"] == "a")
    assert a["missing_count"] == 1
    assert a["is_numeric"] is True


def test_column_profile_outlier_count():
    s = pd.Series([1, 2, 3, 4, 5, 100])
    prof = qc.column_profile("n", s)
    assert prof["outlier_count"] == 1
    assert prof["skew"] is not None
