import pytest
import pandas as pd
import io
from backend.onboarding.validators import (
    ValidationError,
    validate_products,
    validate_inventory,
    validate_procurement,
    validate_sales,
    validate_competitors
)
from backend.onboarding.upload_products import upload_products
from backend.onboarding.upload_inventory import upload_inventory
from backend.onboarding.upload_procurement import upload_procurement
from backend.onboarding.upload_sales import upload_sales
from backend.onboarding.upload_competitors import upload_competitors

# -----------------------------
# 1. TEST PRODUCT VALIDATOR
# -----------------------------
def test_validate_products_success():
    df = pd.DataFrame({
        "product_id": ["SKU_1001", "SKU_1002"],
        "product_name": ["Product A", "Product B"],
        "category": ["Beverages", "Snacks"],
        "subcategory": ["Soda", "Chips"]
    })
    # Should not raise any exception
    validate_products(df)

def test_validate_products_missing_col():
    df = pd.DataFrame({
        "product_id": ["SKU_1001"],
        "product_name": ["Product A"],
        "category": ["Beverages"]
        # subcategory is missing
    })
    with pytest.raises(ValidationError, match="Missing required columns"):
        validate_products(df)

def test_validate_products_nulls():
    df = pd.DataFrame({
        "product_id": ["SKU_1001", None],
        "product_name": ["Product A", "Product B"],
        "category": ["Beverages", "Snacks"],
        "subcategory": ["Soda", "Chips"]
    })
    with pytest.raises(ValidationError, match="Null values detected"):
        validate_products(df)

def test_validate_products_duplicates():
    df = pd.DataFrame({
        "product_id": ["SKU_1001", "SKU_1001"],
        "product_name": ["Product A", "Product B"],
        "category": ["Beverages", "Snacks"],
        "subcategory": ["Soda", "Chips"]
    })
    with pytest.raises(ValidationError, match="Duplicate product IDs"):
        validate_products(df)


# -----------------------------
# 2. TEST INVENTORY VALIDATOR
# -----------------------------
def test_validate_inventory_success():
    df = pd.DataFrame({
        "product_id": ["SKU_1001"],
        "current_stock": [150]
    })
    validate_inventory(df)

def test_validate_inventory_negative():
    df = pd.DataFrame({
        "product_id": ["SKU_1001"],
        "current_stock": [-10]
    })
    with pytest.raises(ValidationError, match="Negative stock values"):
        validate_inventory(df)

def test_validate_inventory_nulls():
    df = pd.DataFrame({
        "product_id": [None],
        "current_stock": [10]
    })
    with pytest.raises(ValidationError, match="Null product_id"):
        validate_inventory(df)


# -----------------------------
# 3. TEST PROCUREMENT VALIDATOR
# -----------------------------
def test_validate_procurement_success():
    df = pd.DataFrame({
        "product_id": ["SKU_1001"],
        "supplier_id": ["SUP_123"],
        "supplier_price": [10.5],
        "freight_cost": [2.0]
    })
    validate_procurement(df)

def test_validate_procurement_negative_cost():
    df = pd.DataFrame({
        "product_id": ["SKU_1001"],
        "supplier_id": ["SUP_123"],
        "supplier_price": [-1.0]
    })
    with pytest.raises(ValidationError, match="Negative cost values"):
        validate_procurement(df)

def test_validate_procurement_non_numeric():
    df = pd.DataFrame({
        "product_id": ["SKU_1001"],
        "supplier_id": ["SUP_123"],
        "supplier_price": ["invalid_price"]
    })
    with pytest.raises(ValidationError, match="Invalid non-numeric values"):
        validate_procurement(df)


# -----------------------------
# 4. TEST SALES VALIDATOR
# -----------------------------
def test_validate_sales_success():
    df = pd.DataFrame({
        "product_id": ["SKU_1001"],
        "units_sold": [5]
    })
    validate_sales(df)

def test_validate_sales_negative():
    df = pd.DataFrame({
        "product_id": ["SKU_1001"],
        "units_sold": [-2]
    })
    with pytest.raises(ValidationError, match="Negative sales values"):
        validate_sales(df)


# -----------------------------
# 5. TEST COMPETITORS VALIDATOR
# -----------------------------
def test_validate_competitors_success():
    df = pd.DataFrame({
        "product_id": ["SKU_1001"],
        "competitor_price": [45.2]
    })
    validate_competitors(df)

def test_validate_competitors_negative():
    df = pd.DataFrame({
        "product_id": ["SKU_1001"],
        "competitor_price": [-5.0]
    })
    with pytest.raises(ValidationError, match="Negative prices detected"):
        validate_competitors(df)


# -----------------------------
# 6. TEST UPLOAD HANDLERS
# -----------------------------
def test_upload_products_handler(tmp_path):
    csv_data = (
        "product_id,product_name,category,subcategory\n"
        "SKU_MOCK_1,Cola Mock,Beverages,Carbonated\n"
    )
    buffer = io.StringIO(csv_data)
    temp_file = tmp_path / "products.csv"
    msg = upload_products(buffer, target_path=str(temp_file))
    assert "successfully validated and saved" in msg
    assert temp_file.exists()

def test_upload_inventory_handler(tmp_path):
    csv_data = (
        "product_id,current_stock\n"
        "SKU_MOCK_1,500\n"
    )
    buffer = io.StringIO(csv_data)
    temp_file = tmp_path / "inventory.csv"
    msg = upload_inventory(buffer, target_path=str(temp_file))
    assert "successfully validated and saved" in msg
    assert temp_file.exists()
