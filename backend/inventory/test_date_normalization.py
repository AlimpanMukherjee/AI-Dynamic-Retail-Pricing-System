import pandas as pd
import pytest
from backend.data_ingestion.validators import normalize_date_column as norm_ingestion
from backend.onboarding.validators import normalize_date_column as norm_onboarding

def test_string_date_normalization():
    # Test normalization of different string formats
    df1 = pd.DataFrame({"date": ["2025-11-20", "11/21/2025", "2025/11/22"]})
    
    # Test backend data_ingestion normalizer
    df1_norm = norm_ingestion(df1.copy(), "date")
    assert list(df1_norm["date"]) == ["2025-11-20", "2025-11-21", "2025-11-22"]
    assert df1_norm["date"].dtype == "object"

    # Test backend onboarding normalizer
    df1_norm_onb = norm_onboarding(df1.copy(), "date")
    assert list(df1_norm_onb["date"]) == ["2025-11-20", "2025-11-21", "2025-11-22"]
    assert df1_norm_onb["date"].dtype == "object"


def test_excel_datetime_normalization():
    # Excel reader often produces datetime64[ns] series
    dt_series = pd.to_datetime(["2025-11-20 00:00:00", "2025-11-21 00:00:00"])
    df = pd.DataFrame({"date": dt_series})
    assert df["date"].dtype == "datetime64[ns]"

    df_norm = norm_ingestion(df, "date")
    assert list(df_norm["date"]) == ["2025-11-20", "2025-11-21"]
    # Should convert it to string object type
    assert df_norm["date"].dtype == "object"


def test_invalid_date_normalization():
    # Check that invalid date format raises ValueError
    df = pd.DataFrame({"date": ["2025-11-20", "not-a-date"]})
    with pytest.raises(ValueError, match="Invalid date format"):
        norm_ingestion(df, "date")


def test_merge_type_safety():
    # Simulate Excel upload (datetime64[ns])
    df_excel = pd.DataFrame({
        "date": pd.to_datetime(["2025-11-20"]),
        "product_id": ["SKU_1000"],
        "units_sold": [5]
    })

    # Simulate CSV database (object string)
    df_csv = pd.DataFrame({
        "date": ["2025-11-20"],
        "product_id": ["SKU_1000"],
        "units_sold": [5]
    })

    # Assert raw merge fails with ValueError/TypeError on type mismatch
    # (Since date is in keys and they are different types)
    with pytest.raises(ValueError, match="You are trying to merge on datetime64.*and object.*"):
        df_excel.merge(df_csv, on=["date", "product_id"])

    # Normalize both
    df_excel_norm = norm_ingestion(df_excel, "date")
    df_csv_norm = norm_ingestion(df_csv, "date")

    # Verify merge succeeds without any errors
    merged = df_excel_norm.merge(df_csv_norm, on=["date", "product_id"])
    assert len(merged) == 1
    assert merged["date"].iloc[0] == "2025-11-20"
