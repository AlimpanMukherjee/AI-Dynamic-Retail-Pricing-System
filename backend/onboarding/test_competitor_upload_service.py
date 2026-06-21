import pytest
import pandas as pd
from frontend.services.competitor_service import _validate_schema, _merge_data

def test_validate_schema_success():
    df = pd.DataFrame({
        "product_id": ["SKU_1000", "SKU_1001"],
        "product_name": ["Product A", "Product B"],
        "competitor_name": ["Blinkit", "BigBasket"],
        "competitor_price": [14.17, 20.56],
        "market_region": ["Kolkata", "Kolkata"],
        "promotion_active": [True, False],
        "rating": [4.3, 3.9]
    })
    is_valid, errors = _validate_schema(df)
    assert is_valid is True
    assert not errors

def test_validate_schema_missing_columns():
    df = pd.DataFrame({
        "product_id": ["SKU_1000"],
        "competitor_name": ["Blinkit"],
        "competitor_price": [14.17]
    })
    is_valid, errors = _validate_schema(df)
    assert is_valid is False
    assert "missing_columns" in errors

def test_validate_schema_duplicates():
    df = pd.DataFrame({
        "product_id": ["SKU_1000", "SKU_1000"],
        "product_name": ["Product A", "Product A"],
        "competitor_name": ["Blinkit", "Blinkit"],  # Duplicate composite key
        "competitor_price": [14.17, 13.90],
        "market_region": ["Kolkata", "Kolkata"],
        "promotion_active": [True, False],
        "rating": [4.3, 4.0]
    })
    is_valid, errors = _validate_schema(df)
    assert is_valid is False
    assert "duplicate_rows" in errors

def test_validate_schema_invalid_fields():
    df = pd.DataFrame({
        "product_id": ["", "SKU_1001"],
        "product_name": ["Product A", "Product B"],
        "competitor_name": ["Blinkit", "BigBasket"],
        "competitor_price": [-5.0, 20.56],  # Price must be > 0
        "market_region": ["Kolkata", "Kolkata"],
        "promotion_active": ["invalid_promo", False],  # String promo must be true/false
        "rating": [6.0, 3.9]  # Rating must be 0-5
    })
    is_valid, errors = _validate_schema(df)
    assert is_valid is False
    assert "row_errors" in errors
    assert len(errors["row_errors"]) == 1  # Only row 0 has errors

def test_merge_data_logic():
    current_df = pd.DataFrame({
        "product_id": ["SKU_1000", "SKU_1000", "SKU_1001"],
        "product_name": ["Cola", "Cola", "Milk"],
        "competitor_name": ["Blinkit", "Zepto", "Blinkit"],
        "competitor_price": [14.17, 14.50, 20.00],
        "market_region": ["Kolkata", "Kolkata", "Kolkata"],
        "promotion_active": [True, False, False],
        "rating": [4.3, 4.5, 4.1]
    })
    
    upload_df = pd.DataFrame({
        "product_id": ["SKU_1000", "SKU_1002"],
        "product_name": ["Cola", "Bread"],
        "competitor_name": ["Blinkit", "Blinkit"],
        "competitor_price": [13.90, 15.00],  # SKU_1000 Blinkit price updated
        "market_region": ["Kolkata", "Kolkata"],
        "promotion_active": [False, True],
        "rating": [4.2, 4.0]
    })
    
    merged, summary = _merge_data(current_df, upload_df)
    
    assert summary["updated"] == 1  # SKU_1000 + Blinkit
    assert summary["inserted"] == 1  # SKU_1002 + Blinkit
    
    # Check that SKU_1000 + Zepto and SKU_1001 + Blinkit are preserved
    assert len(merged) == 4
    
    row_zepto = merged[(merged["product_id"] == "SKU_1000") & (merged["competitor_name"] == "Zepto")].iloc[0]
    assert row_zepto["competitor_price"] == 14.50
    
    row_blinkit_updated = merged[(merged["product_id"] == "SKU_1000") & (merged["competitor_name"] == "Blinkit")].iloc[0]
    assert row_blinkit_updated["competitor_price"] == 13.90
    assert row_blinkit_updated["promotion_active"] == False

