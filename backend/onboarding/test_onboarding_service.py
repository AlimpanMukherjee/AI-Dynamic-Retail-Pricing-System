import os
import pytest
import pandas as pd
import backend.config as cfg
from frontend.services.product_onboarding_service import onboard_single_product
from backend.onboarding.validators import ValidationError
from backend.inventory.inventory_repository import load_current_inventory

def test_onboard_single_product_success(tmp_path, monkeypatch):
    # Setup temp paths in config
    products_file = tmp_path / "products.csv"
    procurement_file = tmp_path / "procurement.csv"
    inventory_file = tmp_path / "inventory_current.csv"
    history_file = tmp_path / "inventory_history.csv"

    # Create dummy initial files
    df_empty_products = pd.DataFrame(columns=["product_id", "product_name", "category", "subcategory", "base_market_price"])
    df_empty_procurement = pd.DataFrame(columns=["product_id", "supplier_id", "supplier_price", "freight_cost", "warehouse_cost", "gst_tax", "supplier_reliability", "lead_time_days"])
    df_empty_inventory = pd.DataFrame(columns=["product_id", "current_stock", "reserved_stock", "safety_stock", "store_location"])

    df_empty_products.to_csv(products_file, index=False)
    df_empty_procurement.to_csv(procurement_file, index=False)
    df_empty_inventory.to_csv(inventory_file, index=False)

    monkeypatch.setattr(cfg, "_get_customer_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(cfg, "DEV_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(cfg, "CUSTOMER_PRODUCTS_PATH", str(products_file))
    monkeypatch.setattr(cfg, "CUSTOMER_PROCUREMENT_PATH", str(procurement_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_CURRENT_PATH", str(inventory_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_PATH", str(inventory_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_HISTORY_PATH", str(history_file))

    prod_data = {
        "product_id": "SKU_NEW_99",
        "product_name": "Premium Tea Brand",
        "category": "Beverages",
        "subcategory": "Tea",
        "base_market_price": 50.0
    }

    proc_data = {
        "product_id": "SKU_NEW_99",
        "supplier_id": "SUP_MOCK_1",
        "supplier_price": 30.0,
        "freight_cost": 2.5,
        "warehouse_cost": 1.0,
        "gst_tax": 3.0,
        "supplier_reliability": 0.95,
        "lead_time_days": 4
    }

    inv_data = {
        "product_id": "SKU_NEW_99",
        "current_stock": 200,
        "reserved_stock": 10,
        "safety_stock": 20,
        "store_location": "Mumbai"
    }

    result = onboard_single_product(prod_data, proc_data, inv_data)

    assert result["status"] == "success"
    assert result["product_id"] == "SKU_NEW_99"

    # Verify products csv contains the new product
    df_p = pd.read_csv(products_file)
    assert "SKU_NEW_99" in df_p["product_id"].values
    assert df_p.loc[df_p["product_id"] == "SKU_NEW_99", "product_name"].values[0] == "Premium Tea Brand"

    # Verify procurement contains it
    df_pr = pd.read_csv(procurement_file)
    assert "SKU_NEW_99" in df_pr["product_id"].values
    assert df_pr.loc[df_pr["product_id"] == "SKU_NEW_99", "supplier_price"].values[0] == 30.0

    # Verify inventory contains it
    df_i = load_current_inventory()
    assert "SKU_NEW_99" in df_i["product_id"].values
    assert int(df_i.loc[df_i["product_id"] == "SKU_NEW_99", "current_stock"].values[0]) == 200


def test_onboard_single_product_duplicate_error(tmp_path, monkeypatch):
    # Setup temp paths in config
    products_file = tmp_path / "products.csv"
    procurement_file = tmp_path / "procurement.csv"
    inventory_file = tmp_path / "inventory_current.csv"

    # Save existing product
    df_existing_products = pd.DataFrame({
        "product_id": ["SKU_DUPE"],
        "product_name": ["Old Product"],
        "category": ["Beverages"],
        "subcategory": ["Soda"],
        "base_market_price": [15.0]
    })
    df_existing_products.to_csv(products_file, index=False)

    df_empty_procurement = pd.DataFrame(columns=["product_id", "supplier_id", "supplier_price", "freight_cost", "warehouse_cost", "gst_tax"])
    df_empty_procurement.to_csv(procurement_file, index=False)

    monkeypatch.setattr(cfg, "_get_customer_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(cfg, "DEV_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(cfg, "CUSTOMER_PRODUCTS_PATH", str(products_file))
    monkeypatch.setattr(cfg, "CUSTOMER_PROCUREMENT_PATH", str(procurement_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_CURRENT_PATH", str(inventory_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_PATH", str(inventory_file))

    prod_data = {
        "product_id": "SKU_DUPE",
        "product_name": "New Product Duplicate",
        "category": "Beverages",
        "subcategory": "Tea",
        "base_market_price": 50.0
    }

    # Should raise ValueError due to duplicate ID
    with pytest.raises(ValueError, match="already exists"):
        onboard_single_product(prod_data, {}, {})


def test_onboard_single_product_validation_error(tmp_path, monkeypatch):
    # Setup temp paths in config
    products_file = tmp_path / "products.csv"
    procurement_file = tmp_path / "procurement.csv"
    inventory_file = tmp_path / "inventory_current.csv"

    # Create dummy empty files
    pd.DataFrame(columns=["product_id", "product_name", "category", "subcategory"]).to_csv(products_file, index=False)
    pd.DataFrame(columns=["product_id", "supplier_id"]).to_csv(procurement_file, index=False)

    monkeypatch.setattr(cfg, "_get_customer_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(cfg, "DEV_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(cfg, "CUSTOMER_PRODUCTS_PATH", str(products_file))
    monkeypatch.setattr(cfg, "CUSTOMER_PROCUREMENT_PATH", str(procurement_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_CURRENT_PATH", str(inventory_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_PATH", str(inventory_file))

    # Missing product_name, category, subcategory
    prod_data = {
        "product_id": "SKU_BAD_1"
    }

    with pytest.raises(ValidationError, match="Missing required columns"):
        onboard_single_product(prod_data, {}, {})
