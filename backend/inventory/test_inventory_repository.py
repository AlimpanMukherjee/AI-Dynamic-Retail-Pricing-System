import os
import pytest
import pandas as pd
import backend.config as cfg
from backend.inventory.inventory_repository import (
    load_current_inventory,
    save_current_inventory,
    get_product_inventory,
    update_product_inventory,
    get_current_inventory_path,
    initialize_inventory_datasets
)
from backend.inventory.inventory_ingestion import process_inventory_upload

def test_repository_basic_operations(tmp_path, monkeypatch):
    current_file = tmp_path / "inventory_current.csv"
    history_file = tmp_path / "inventory_history.csv"
    
    monkeypatch.setattr(cfg, "_get_customer_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(cfg, "DEV_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_CURRENT_PATH", str(current_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_HISTORY_PATH", str(history_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_PATH", str(current_file))

    # Path helper test
    assert get_current_inventory_path() == str(current_file)

    # Empty loading
    df = load_current_inventory()
    assert df.empty

    # Save and load
    df_save = pd.DataFrame([{"product_id": "SKU_99", "current_stock": 500}])
    save_current_inventory(df_save)
    df_load = load_current_inventory()
    assert len(df_load) == 1
    assert df_load.iloc[0]["product_id"] == "SKU_99"

    # Get product inventory helper
    data = get_product_inventory("SKU_99")
    assert data["product_id"] == "SKU_99"
    assert data["current_stock"] == 500

    # Get non-existent
    assert get_product_inventory("SKU_NONE") == {}

    # Update product inventory
    success = update_product_inventory("SKU_99", 750)
    assert success
    assert get_product_inventory("SKU_99")["current_stock"] == 750

    # Update non-existent
    assert not update_product_inventory("SKU_NONE", 100)

def test_ingestion_modes(tmp_path, monkeypatch):
    current_file = tmp_path / "inventory_current.csv"
    history_file = tmp_path / "inventory_history.csv"
    backup_dir = tmp_path / "uploads"
    
    monkeypatch.setattr(cfg, "_get_customer_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(cfg, "DEV_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_CURRENT_PATH", str(current_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_HISTORY_PATH", str(history_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_PATH", str(current_file))
    monkeypatch.setattr(cfg, "BACKUP_INVENTORY_DIR", str(backup_dir))

    pd.DataFrame(columns=["snapshot_timestamp", "product_id", "current_stock", "reserved_stock", "warehouse"]).to_csv(history_file, index=False)

    df_init = pd.DataFrame([{"product_id": "SKU_100", "current_stock": 200}])

    # Mode A: initialize (should succeed first time)
    process_inventory_upload(df_init, mode="initialize")
    assert load_current_inventory().iloc[0]["current_stock"] == 200

    # Mode A: initialize second time should raise error
    with pytest.raises(ValueError, match="Operational inventory has already been initialized"):
        process_inventory_upload(df_init, mode="initialize")

    # Mode B: restock (should add stock: 200 + 150 = 350)
    df_restock = pd.DataFrame([{"product_id": "SKU_100", "current_stock": 150}])
    process_inventory_upload(df_restock, mode="restock")
    assert load_current_inventory().iloc[0]["current_stock"] == 350

    # Mode C: overwrite (should overwrite stock directly to 100)
    df_overwrite = pd.DataFrame([{"product_id": "SKU_100", "current_stock": 100}])
    process_inventory_upload(df_overwrite, mode="overwrite")
    assert load_current_inventory().iloc[0]["current_stock"] == 100
