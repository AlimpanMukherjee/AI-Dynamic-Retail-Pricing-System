import os
import json
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from io import StringIO

import backend.config as cfg
from backend.inventory.inventory_ingestion import (
    validate_inventory_file,
    append_inventory_history,
    update_current_inventory,
    save_raw_backup,
    process_inventory_upload,
    initialize_inventory_datasets
)

@pytest.fixture
def temp_paths(tmp_path, monkeypatch):
    """
    Sets up temporary CSV paths in configuration and prepares raw legacy inventory file.
    """
    current_file = tmp_path / "inventory_current.csv"
    history_file = tmp_path / "inventory_history.csv"
    backup_dir = tmp_path / "uploads" / "inventory"
    
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_CURRENT_PATH", str(current_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_HISTORY_PATH", str(history_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_PATH", str(current_file))
    monkeypatch.setattr(cfg, "BACKUP_INVENTORY_DIR", str(backup_dir))

    # Pre-populate a fake old inventory.csv to simulate legacy data
    old_file = tmp_path / "inventory.csv"
    df_old = pd.DataFrame([
        {
            "product_id": "SKU_1056",
            "product_name": "Maggi 70g Mini",
            "brand": "Maggi",
            "category": "PACKAGED FOODS",
            "retailer_company": "Reliance Retail",
            "store_location": "Hyderabad",
            "warehouse_location": "Hyderabad DC",
            "current_stock": 5000,
            "reserved_stock": 100,
            "reorder_point": 200,
            "safety_stock": 80,
            "sales_velocity_per_day": 10.0,
            "lead_time_days": 5,
            "stock_age_days": 10
        },
        {
            "product_id": "SKU_1057",
            "product_name": "Lays Chips Classic",
            "brand": "Lays",
            "category": "PACKAGED FOODS",
            "retailer_company": "Reliance Retail",
            "store_location": "Hyderabad",
            "warehouse_location": "Hyderabad DC",
            "current_stock": 3000,
            "reserved_stock": 50,
            "reorder_point": 150,
            "safety_stock": 60,
            "sales_velocity_per_day": 8.0,
            "lead_time_days": 4,
            "stock_age_days": 8
        }
    ])
    df_old.to_csv(old_file, index=False)
    

    return {
        "current": current_file,
        "history": history_file,
        "backup": backup_dir,
        "old": old_file
    }


def test_legacy_migration(temp_paths):
    # Ensure current and history files do not exist initially
    assert not temp_paths["current"].exists()
    assert not temp_paths["history"].exists()
    
    # Trigger auto-migration
    initialize_inventory_datasets()
    
    assert temp_paths["current"].exists()
    assert temp_paths["history"].exists()
    
    df_curr = pd.read_csv(temp_paths["current"])
    assert len(df_curr) == 2
    assert "last_updated" in df_curr.columns
    assert df_curr[df_curr["product_id"] == "SKU_1056"]["current_stock"].iloc[0] == 5000
    
    df_hist = pd.read_csv(temp_paths["history"])
    assert len(df_hist) == 2
    assert "snapshot_timestamp" in df_hist.columns


def test_validate_inventory_file():
    # 1. Valid data
    valid_csv = "product_id,current_stock,reserved_stock,warehouse\nSKU_9999,100,5,DC1\n"
    df = validate_inventory_file(StringIO(valid_csv))
    assert len(df) == 1
    assert df["product_id"].iloc[0] == "SKU_9999"
    assert df["current_stock"].iloc[0] == 100

    # 2. Compatibility mapping (stock -> current_stock)
    compat_csv = "product_id,stock,reserved_stock\nSKU_9999,150,5\n"
    df_compat = validate_inventory_file(StringIO(compat_csv))
    assert "current_stock" in df_compat.columns
    assert df_compat["current_stock"].iloc[0] == 150

    # 3. Missing column
    invalid_cols = "product_id,reserved_stock\nSKU_9999,5\n"
    with pytest.raises(ValueError, match="Missing required column 'current_stock'"):
        validate_inventory_file(StringIO(invalid_cols))

    # 4. Empty product_id
    invalid_id = "product_id,current_stock\n,100\n"
    with pytest.raises(ValueError, match="product_id cannot be empty"):
        validate_inventory_file(StringIO(invalid_id))

    # 5. Duplicate product_id in file
    dup_csv = "product_id,current_stock\nSKU_9999,100\nSKU_9999,200\n"
    with pytest.raises(ValueError, match="Duplicate SKU records detected within the upload file"):
        validate_inventory_file(StringIO(dup_csv))

    # 6. Negative Stock
    neg_stock = "product_id,current_stock\nSKU_9999,-10\n"
    with pytest.raises(ValueError, match="Negative current_stock detected"):
        validate_inventory_file(StringIO(neg_stock))

    # 7. Negative Reserved Stock
    neg_reserved = "product_id,current_stock,reserved_stock\nSKU_9999,100,-5\n"
    with pytest.raises(ValueError, match="Negative reserved_stock detected"):
        validate_inventory_file(StringIO(neg_reserved))


def test_upsert_overwrite_rules(temp_paths):
    # Initialize files using migration
    initialize_inventory_datasets()
    
    # Upload data containing:
    # - SKU_1056: existing, updating stock, reserved, and warehouse.
    # - SKU_9999: new product, inserting.
    upload_df = pd.DataFrame([
        {
            "product_id": "SKU_1056",
            "current_stock": 4500,
            "reserved_stock": 90,
            "warehouse": "Hyderabad DC V2"
        },
        {
            "product_id": "SKU_9999",
            "current_stock": 1000,
            "reserved_stock": 10,
            "warehouse": "Mumbai DC"
        }
    ])
    
    timestamp = "2026-06-14 17:00:00"
    inserted, updated = update_current_inventory(upload_df, timestamp)
    
    assert inserted == 1
    assert updated == 1
    
    df_curr = pd.read_csv(temp_paths["current"])
    assert len(df_curr) == 3
    
    # Check updated product SKU_1056:
    row_1056 = df_curr[df_curr["product_id"] == "SKU_1056"].iloc[0].to_dict()
    assert row_1056["current_stock"] == 4500
    assert row_1056["reserved_stock"] == 90
    assert row_1056["warehouse"] == "Hyderabad DC V2"
    assert row_1056["last_updated"] == timestamp
    
    # Explicit Overwrite check: absent columns from upload (like reorder_point, stock_age_days) MUST be preserved!
    assert row_1056["reorder_point"] == 200
    assert row_1056["stock_age_days"] == 10
    
    # Check inserted SKU_9999:
    row_9999 = df_curr[df_curr["product_id"] == "SKU_9999"].iloc[0].to_dict()
    assert row_9999["current_stock"] == 1000
    assert row_9999["warehouse"] == "Mumbai DC"
    assert row_9999["last_updated"] == timestamp


def test_append_history(temp_paths):
    initialize_inventory_datasets()
    
    upload_df = pd.DataFrame([
        {
            "product_id": "SKU_1056",
            "current_stock": 4800,
            "reserved_stock": 90,
            "warehouse": "Hyderabad DC",
            "lead_time": 6,
            "supplier_id": "SUP_99"
        }
    ])
    
    timestamp = "2026-06-14 17:15:00"
    append_inventory_history(upload_df, timestamp)
    
    df_hist = pd.read_csv(temp_paths["history"])
    # Initial 2 rows from migration + 1 new row = 3 rows
    assert len(df_hist) == 3
    
    last_row = df_hist.iloc[-1].to_dict()
    assert last_row["snapshot_timestamp"] == timestamp
    assert last_row["product_id"] == "SKU_1056"
    assert last_row["current_stock"] == 4800
    assert last_row["reserved_stock"] == 90
    
    # Future compatibility column check
    assert last_row["lead_time"] == 6
    assert last_row["supplier_id"] == "SUP_99"


def test_save_raw_backup(temp_paths):
    csv_str = "product_id,current_stock\nSKU_1056,5000\n"
    timestamp = "2026-06-14 17:30:00"
    
    backup_file = save_raw_backup(StringIO(csv_str), timestamp)
    assert os.path.exists(backup_file)
    assert "2026_06_14_173000.csv" in backup_file
    
    with open(backup_file, "r") as f:
        content = f.read()
    assert content == csv_str


def test_process_inventory_upload(temp_paths):
    initialize_inventory_datasets()
    
    csv_str = "product_id,current_stock,reserved_stock,warehouse\nSKU_1056,4100,80,Hyderabad DC\nSKU_8888,2500,20,Delhi DC\n"
    result = process_inventory_upload(StringIO(csv_str))
    
    assert result["rows_processed"] == 2
    assert result["rows_inserted"] == 1  # SKU_8888
    assert result["rows_updated"] == 1   # SKU_1056
    assert result["history_rows_added"] == 2
    
    # Check that current stock is updated in target current csv
    df_curr = pd.read_csv(temp_paths["current"])
    assert df_curr[df_curr["product_id"] == "SKU_1056"]["current_stock"].iloc[0] == 4100
    assert df_curr[df_curr["product_id"] == "SKU_8888"]["current_stock"].iloc[0] == 2500


def test_deduct_inventory_from_sales(temp_paths):
    from backend.inventory.inventory_ingestion import deduct_inventory_from_sales
    initialize_inventory_datasets()
    
    # Verify initial stock
    df_curr = pd.read_csv(temp_paths["current"])
    assert df_curr[df_curr["product_id"] == "SKU_1056"]["current_stock"].iloc[0] == 5000
    assert df_curr[df_curr["product_id"] == "SKU_1057"]["current_stock"].iloc[0] == 3000

    # Create dummy sales dataframe
    sales_df = pd.DataFrame([
        {"product_id": "SKU_1056", "units_sold": 200},
        {"product_id": "SKU_1057", "units_sold": 3500},
        {"product_id": "SKU_9999", "units_sold": 10} # Non-existent SKU
    ])

    deduct_inventory_from_sales(sales_df)

    # Verify updated stock levels
    df_curr_new = pd.read_csv(temp_paths["current"])
    
    # 5000 - 200 = 4800
    assert df_curr_new[df_curr_new["product_id"] == "SKU_1056"]["current_stock"].iloc[0] == 4800
    # 3000 - 3500 = 0 (clamped)
    assert df_curr_new[df_curr_new["product_id"] == "SKU_1057"]["current_stock"].iloc[0] == 0
    # SKU_9999 not added to inventory
    assert "SKU_9999" not in df_curr_new["product_id"].values

