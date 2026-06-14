import os
import json
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import backend.config as cfg
from backend.layer1.engine2.model_store import save_model, load_model, save_metadata, load_metadata
from backend.layer1.engine2.preprocessing import SafeLabelEncoder
from backend.layer1.engine2.engine2 import run_pipeline
from backend.data_ingestion.validators import (
    validate_sales_data,
    validate_inventory_data,
    validate_market_data,
    validate_supplier_data
)
from backend.data_ingestion.sales_ingestion import append_sales_data
from backend.data_ingestion.inventory_ingestion import append_inventory_data
from backend.data_ingestion.market_ingestion import append_market_data
from backend.data_ingestion.supplier_ingestion import append_supplier_data
from backend.retraining.retrain_engine2 import check_and_trigger_retraining
from backend.monitoring.forecast_monitor import calculate_forecast_accuracy

# -------------------------------------------------------------
# 1. Model Store Tests
# -------------------------------------------------------------

def test_model_store_saving_and_loading(tmp_path):
    model_file = tmp_path / "test_model.pkl"
    metadata_file = tmp_path / "test_metadata.json"
    
    # Create simple dummy model and encoders
    dummy_model = "mock_xgboost_model"
    dummy_features = ["price", "log_price", "lag_sales"]
    
    encoder = SafeLabelEncoder()
    encoder.fit(pd.Series(["Beverages", "Snacks"]))
    dummy_encoders = {"category_encoded": encoder}
    
    # Save
    save_model(dummy_model, dummy_features, dummy_encoders, str(model_file))
    assert model_file.exists()
    
    # Load and verify
    loaded_model, loaded_features, loaded_encoders = load_model(str(model_file))
    assert loaded_model == dummy_model
    assert loaded_features == dummy_features
    assert "category_encoded" in loaded_encoders
    assert loaded_encoders["category_encoded"].transform("Beverages") == 0
    assert loaded_encoders["category_encoded"].transform("Snacks") == 1
    
    # Test Metadata
    dummy_metadata = {
        "model_version": "1.0",
        "trained_at": "2026-06-13 12:00:00",
        "training_rows": 100,
        "train_r2": 0.85
    }
    save_metadata(dummy_metadata, str(metadata_file))
    assert metadata_file.exists()
    
    loaded_metadata = load_metadata(str(metadata_file))
    assert loaded_metadata == dummy_metadata


# -------------------------------------------------------------
# 2. Data Validation Tests
# -------------------------------------------------------------

def test_validate_sales_data():
    # Valid sales data
    valid_sales = pd.DataFrame({
        "date": ["2026-06-01", "2026-06-02"],
        "product_id": ["SKU_1000", "SKU_1000"],
        "selling_price": [10.5, 11.2],
        "units_sold": [5, 10]
    })
    # Should not raise any error
    validate_sales_data(valid_sales)

    # Missing column
    invalid_sales_missing = valid_sales.drop(columns=["date"])
    with pytest.raises(ValueError, match="Missing required column 'date'"):
        validate_sales_data(invalid_sales_missing)

    # Negative price
    invalid_sales_price = valid_sales.copy()
    invalid_sales_price["selling_price"] = [-5.0, 11.2]
    with pytest.raises(ValueError, match="Price/selling_price must be > 0"):
        validate_sales_data(invalid_sales_price)

    # Negative units sold
    invalid_sales_units = valid_sales.copy()
    invalid_sales_units["units_sold"] = [5, -3]
    with pytest.raises(ValueError, match="Negative units_sold"):
        validate_sales_data(invalid_sales_units)

    # Duplicate rows
    invalid_sales_dup = pd.concat([valid_sales, valid_sales.iloc[[0]]])
    with pytest.raises(ValueError, match="Duplicate rows detected"):
        validate_sales_data(invalid_sales_dup)


def test_validate_inventory_data():
    # Valid inventory data
    valid_inv = pd.DataFrame({
        "product_id": ["SKU_1000", "SKU_1001"],
        "retailer_company": ["Blinkit", "DMart"],
        "store_location": ["Mumbai", "Bengaluru"],
        "stock": [100, 200],
        "reserved_stock": [5, 10]
    })
    validate_inventory_data(valid_inv)

    # Negative stock
    invalid_inv_stock = valid_inv.copy()
    invalid_inv_stock["stock"] = [-10, 200]
    with pytest.raises(ValueError, match="Negative stock"):
        validate_inventory_data(invalid_inv_stock)

    # Negative reserved stock
    invalid_inv_res = valid_inv.copy()
    invalid_inv_res["reserved_stock"] = [5, -1]
    with pytest.raises(ValueError, match="Negative reserved_stock"):
        validate_inventory_data(invalid_inv_res)

    # Duplicate rows
    invalid_inv_dup = pd.concat([valid_inv, valid_inv.iloc[[0]]])
    with pytest.raises(ValueError, match="Duplicate rows detected"):
        validate_inventory_data(invalid_inv_dup)


def test_validate_market_data():
    valid_market = pd.DataFrame({
        "product_id": ["SKU_1000", "SKU_1001"],
        "competitor_price": [12.0, 15.5]
    })
    validate_market_data(valid_market)

    # Missing product_id
    invalid_market = valid_market.drop(columns=["product_id"])
    with pytest.raises(ValueError, match="Missing required column 'product_id'"):
        validate_market_data(invalid_market)

    # Negative competitor price
    invalid_market_price = valid_market.copy()
    invalid_market_price["competitor_price"] = [12.0, -1.0]
    with pytest.raises(ValueError, match="Price/selling_price must be > 0"):
        validate_market_data(invalid_market_price)


def test_validate_supplier_data():
    valid_supplier = pd.DataFrame({
        "product_id": ["SKU_1000", "SKU_1001"],
        "supplier_id": ["SUP_A", "SUP_B"],
        "lead_time": [5, 10],
        "reliability": [0.95, 0.80]
    })
    validate_supplier_data(valid_supplier)

    # Reliability out of bounds
    invalid_supplier = valid_supplier.copy()
    invalid_supplier["reliability"] = [1.2, 0.8]
    with pytest.raises(ValueError, match="Reliability must be between 0 and 1"):
        validate_supplier_data(invalid_supplier)

    # Negative lead time
    invalid_supplier_lead = valid_supplier.copy()
    invalid_supplier_lead["lead_time"] = [-2, 10]
    with pytest.raises(ValueError, match="Negative lead_time"):
        validate_supplier_data(invalid_supplier_lead)


# -------------------------------------------------------------
# 3. Data Ingestion Appending Tests
# -------------------------------------------------------------

def test_data_ingestion_appending_logic(tmp_path, monkeypatch):
    sales_file = tmp_path / "sales.csv"
    inv_file = tmp_path / "inventory.csv"
    market_file = tmp_path / "competitors.csv"
    supplier_file = tmp_path / "procurement.csv"

    # Patch config paths
    monkeypatch.setattr(cfg, "CUSTOMER_SALES_PATH", str(sales_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_PATH", str(inv_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_CURRENT_PATH", str(inv_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_HISTORY_PATH", str(tmp_path / "inventory_history.csv"))
    monkeypatch.setattr(cfg, "CUSTOMER_COMPETITOR_PATH", str(market_file))
    monkeypatch.setattr(cfg, "CUSTOMER_PROCUREMENT_PATH", str(supplier_file))

    # Pre-create empty inventory files to bypass auto-migration during test
    pd.DataFrame(columns=["product_id", "current_stock", "reserved_stock", "warehouse"]).to_csv(inv_file, index=False)
    pd.DataFrame(columns=["snapshot_timestamp", "product_id", "current_stock", "reserved_stock", "warehouse"]).to_csv(tmp_path / "inventory_history.csv", index=False)

    # Test Sales Ingestion
    df_sales_1 = pd.DataFrame({
        "date": ["2026-06-01"],
        "product_id": ["SKU_1000"],
        "selling_price": [10.0],
        "units_sold": [5]
    })
    rows_added = append_sales_data(df_sales_1)
    assert rows_added == 1
    assert sales_file.exists()

    # Append duplicate (should drop duplicates, rows_added = 0)
    rows_added_dup = append_sales_data(df_sales_1)
    assert rows_added_dup == 0

    # Append new row
    df_sales_2 = pd.DataFrame({
        "date": ["2026-06-02"],
        "product_id": ["SKU_1000"],
        "selling_price": [10.5],
        "units_sold": [6]
    })
    rows_added_new = append_sales_data(df_sales_2)
    assert rows_added_new == 1
    
    saved_sales = pd.read_csv(sales_file)
    assert len(saved_sales) == 2

    # Test Inventory Ingestion
    df_inv = pd.DataFrame({
        "product_id": ["SKU_1000"],
        "retailer_company": ["Blinkit"],
        "store_location": ["Mumbai"],
        "stock": [50],
        "reserved_stock": [2]
    })
    assert append_inventory_data(df_inv) == 1
    assert append_inventory_data(df_inv) == 0  # Duplicate

    # Test Market Ingestion
    df_market = pd.DataFrame({
        "product_id": ["SKU_1000"],
        "competitor_price": [9.9]
    })
    assert append_market_data(df_market) == 1
    assert append_market_data(df_market) == 0  # Duplicate

    # Test Supplier Ingestion
    df_supplier = pd.DataFrame({
        "product_id": ["SKU_1000"],
        "supplier_id": ["SUP_1"],
        "lead_time": [4],
        "reliability": [0.9]
    })
    assert append_supplier_data(df_supplier) == 1
    assert append_supplier_data(df_supplier) == 0  # Duplicate


# -------------------------------------------------------------
# 4. Retraining Criteria Tests
# -------------------------------------------------------------

def test_automatic_retraining_criteria(tmp_path, monkeypatch):
    sales_file = tmp_path / "sales.csv"
    metadata_file = tmp_path / "engine2_metadata.json"

    monkeypatch.setattr(cfg, "CUSTOMER_SALES_PATH", str(sales_file))
    # Patch metadata paths in retraining script
    monkeypatch.setattr("backend.retraining.retrain_engine2.METADATA_PATH", str(metadata_file))

    # Helper to mock run_pipeline inside retrain_engine2
    retrained_called = False
    def mock_run_pipeline(force_retrain=False):
        nonlocal retrained_called
        retrained_called = True

    monkeypatch.setattr("backend.retraining.retrain_engine2.run_pipeline", mock_run_pipeline)

    # 1. No sales file -> should return False and skip
    assert check_and_trigger_retraining() is False
    assert not retrained_called

    # Create synthetic sales file with 10 rows
    pd.DataFrame({"date": ["2026-06-01"] * 10, "product_id": ["SKU_1000"] * 10}).to_csv(sales_file, index=False)

    # 2. No metadata file -> should trigger training immediately (returns True)
    retrained_called = False
    assert check_and_trigger_retraining() is True
    assert retrained_called

    # Create metadata: trained recently, 10 training_rows
    metadata = {
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "training_rows": 10
    }
    with open(metadata_file, "w") as f:
        json.dump(metadata, f)

    # 3. Metada exists, recent training, rows unchanged -> should NOT trigger (returns False)
    retrained_called = False
    assert check_and_trigger_retraining() is False
    assert not retrained_called

    # 4. Condition A: Trained >= 7 days ago -> should trigger (returns True)
    old_time = (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")
    metadata["trained_at"] = old_time
    with open(metadata_file, "w") as f:
        json.dump(metadata, f)

    retrained_called = False
    assert check_and_trigger_retraining() is True
    assert retrained_called

    # Reset metadata back to recent
    metadata["trained_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(metadata_file, "w") as f:
        json.dump(metadata, f)

    # 5. Condition B: 500+ new rows since last training -> should trigger (returns True)
    # Total current rows in sales file: 520 (which is 10 + 510 new rows)
    pd.DataFrame({"date": ["2026-06-01"] * 520, "product_id": ["SKU_1000"] * 520}).to_csv(sales_file, index=False)
    
    retrained_called = False
    assert check_and_trigger_retraining() is True
    assert retrained_called


# -------------------------------------------------------------
# 5. Orchestrator and Caching Execution Test
# -------------------------------------------------------------

def test_run_pipeline_caching_and_execution(tmp_path, monkeypatch):
    sales_file = tmp_path / "sales.csv"
    products_file = tmp_path / "products.csv"
    inv_file = tmp_path / "inventory.csv"
    model_file = tmp_path / "engine2_model.pkl"
    metadata_file = tmp_path / "engine2_metadata.json"

    # Patch config variables and orchestrator paths
    monkeypatch.setattr(cfg, "CUSTOMER_SALES_PATH", str(sales_file))
    monkeypatch.setattr(cfg, "CUSTOMER_PRODUCTS_PATH", str(products_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_PATH", str(inv_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_CURRENT_PATH", str(inv_file))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_HISTORY_PATH", str(tmp_path / "inventory_history.csv"))
    
    monkeypatch.setattr("backend.layer1.engine2.engine2.MODEL_PATH", str(model_file))
    monkeypatch.setattr("backend.layer1.engine2.engine2.METADATA_PATH", str(metadata_file))

    # Pre-create history inventory file to bypass auto-migration during test
    pd.DataFrame(columns=["snapshot_timestamp", "product_id", "current_stock", "reserved_stock", "warehouse"]).to_csv(tmp_path / "inventory_history.csv", index=False)

    # Construct robust synthetic dataset
    # We generate 110 unique dates to test the pipeline in "normal" mode and avoid validation/test split index issues.
    dates = [ (datetime(2026, 1, 1) + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(120) ]
    
    # 110 rows for SKU_1000 (enough for "normal" mode > 100)
    sales_data = []
    for d in dates[:110]:
        sales_data.append({
            "date": d,
            "product_id": "SKU_1000",
            "selling_price": float(round(10.0 + np.sin(len(sales_data)/10.0), 2)),
            "units_sold": int(5 + np.cos(len(sales_data)/10.0) * 2)
        })
    # Add a few rows for SKU_1001 (triggers cold start <= 30 records)
    for d in dates[:10]:
        sales_data.append({
            "date": d,
            "product_id": "SKU_1001",
            "selling_price": 25.0,
            "units_sold": 2
        })

    df_sales = pd.DataFrame(sales_data)
    df_sales.to_csv(sales_file, index=False)

    df_products = pd.DataFrame([
        {
            "product_id": "SKU_1000",
            "name": "Product 1000",
            "category": "Beverages",
            "subcategory": "Soft Drinks",
            "brand": "BrandX",
            "pack_size_ml": 500.0,
            "base_market_price": 10.0
        },
        {
            "product_id": "SKU_1001",
            "name": "Product 1001",
            "category": "Beverages",
            "subcategory": "Soft Drinks",
            "brand": "BrandX",
            "pack_size_ml": 300.0,
            "base_market_price": 25.0
        }
    ])
    df_products.to_csv(products_file, index=False)

    df_inv = pd.DataFrame([
        {
            "product_id": "SKU_1000",
            "retailer_company": "Reliance Retail",
            "store_location": "Mumbai",
            "stock": 100,
            "reserved_stock": 5
        },
        {
            "product_id": "SKU_1001",
            "retailer_company": "Reliance Retail",
            "store_location": "Mumbai",
            "stock": 50,
            "reserved_stock": 2
        }
    ])
    df_inv.to_csv(inv_file, index=False)

    # Clean up any prediction history file from previous tests if it exists locally
    history_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "history", "prediction_history.csv")
    if os.path.exists(history_file):
        try:
            os.remove(history_file)
        except Exception:
            pass

    # First run: model file does not exist, should train and save model + metadata
    res_1 = run_pipeline(
        sales_csv_path=str(sales_file),
        target_product_id="SKU_1000",
        products_csv_path=str(products_file),
        inventory_csv_path=str(inv_file),
        retailer_company="Reliance Retail",
        store_location="Mumbai",
        force_retrain=False
    )
    assert model_file.exists()
    assert metadata_file.exists()
    assert res_1["prediction_source"] == "historical_sales"
    assert res_1["optimal_price"] > 0
    assert res_1["expected_demand"] > 0

    # Modify metadata file to verify that the second run loads it instead of retraining
    with open(metadata_file, "r") as f:
        meta_data = json.load(f)
    meta_data["train_r2"] = 0.9999  # Unique signature
    with open(metadata_file, "w") as f:
        json.dump(meta_data, f)

    # Second run: force_retrain=False, model files exist. Should reload.
    res_2 = run_pipeline(
        sales_csv_path=str(sales_file),
        target_product_id="SKU_1000",
        products_csv_path=str(products_file),
        inventory_csv_path=str(inv_file),
        retailer_company="Reliance Retail",
        store_location="Mumbai",
        force_retrain=False
    )
    # The signature in metadata is preserved (demonstrates caching was used)
    loaded_meta = load_metadata(str(metadata_file))
    assert loaded_meta["train_r2"] == 0.9999

    # Third run: cold start product (SKU_1001, count=10 <= 30)
    res_cold = run_pipeline(
        sales_csv_path=str(sales_file),
        target_product_id="SKU_1001",
        products_csv_path=str(products_file),
        inventory_csv_path=str(inv_file),
        retailer_company="Reliance Retail",
        store_location="Mumbai",
        force_retrain=False
    )
    assert res_cold["prediction_source"] == "similar_products"
    assert len(res_cold["similar_products_used"]) > 0

    # Fourth run: force_retrain=True. Should retrain and overwrite signature
    res_3 = run_pipeline(
        sales_csv_path=str(sales_file),
        target_product_id="SKU_1000",
        products_csv_path=str(products_file),
        inventory_csv_path=str(inv_file),
        retailer_company="Reliance Retail",
        store_location="Mumbai",
        force_retrain=True
    )
    loaded_meta_retrained = load_metadata(str(metadata_file))
    assert loaded_meta_retrained["train_r2"] != 0.9999  # Signature reset!


# -------------------------------------------------------------
# 6. Monitoring / Accuracy Metrics Tests
# -------------------------------------------------------------

def test_forecast_accuracy_monitoring(tmp_path, monkeypatch):
    sales_file = tmp_path / "sales.csv"
    history_file = tmp_path / "prediction_history.csv"

    monkeypatch.setattr(cfg, "CUSTOMER_SALES_PATH", str(sales_file))
    
    # Mock history file path inside forecast_monitor by monkeypatching history_file path
    # But wait, forecast_monitor computes history_file like:
    # history_dir = os.path.join(cfg.PROJECT_ROOT, "backend", "history")
    # Let's inspect forecast_monitor to mock history_file path:
    # We can patch 'os.path.exists' to return True for history_file when queried, and pd.read_csv to return custom DataFrames.
    # Alternatively, we can let forecast_monitor load them from the mock files directly.
    # Let's override pd.read_csv inside forecast_monitor or check how it loads:
    # history_dir = os.path.join(cfg.PROJECT_ROOT, "backend", "history")
    # history_file = os.path.join(history_dir, "prediction_history.csv")
    
    # Let's monkeypatch 'pandas.read_csv' to return custom DataFrames when matching the paths.
    orig_read_csv = pd.read_csv
    
    mock_history_df = pd.DataFrame([
        {
            "timestamp": "2026-06-01 12:00:00",
            "sku": "SKU_1000",
            "recommended_price": 10.0,
            "expected_demand": 5.0,
            "elasticity": -1.2,
            "prediction_source": "historical_sales"
        },
        {
            "timestamp": "2026-06-02 12:00:00",
            "sku": "SKU_1000",
            "recommended_price": 10.5,
            "expected_demand": 6.0,
            "elasticity": -1.2,
            "prediction_source": "historical_sales"
        }
    ])
    
    mock_sales_df = pd.DataFrame([
        {
            "date": "2026-06-01",
            "product_id": "SKU_1000",
            "selling_price": 10.0,
            "units_sold": 4  # expected 5 (error = 1)
        },
        {
            "date": "2026-06-02",
            "product_id": "SKU_1000",
            "selling_price": 10.5,
            "units_sold": 8  # expected 6 (error = -2)
        }
    ])

    def mock_read_csv(path, *args, **kwargs):
        path_str = str(path)
        if "prediction_history.csv" in path_str:
            return mock_history_df
        elif "sales.csv" in path_str:
            return mock_sales_df
        return orig_read_csv(path, *args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", mock_read_csv)
    monkeypatch.setattr(os.path, "exists", lambda path: True)  # Make it think both files exist

    # Run calculate_forecast_accuracy
    report = calculate_forecast_accuracy(sales_csv_path=str(sales_file))
    
    assert report is not None
    assert report["matches_count"] == 2
    # Errors: |5 - 4| = 1; |6 - 8| = 2. MAE = (1 + 2)/2 = 1.5
    assert report["MAE"] == 1.5
    # RMSE = sqrt((1^2 + (-2)^2)/2) = sqrt((1 + 4)/2) = sqrt(2.5) ≈ 1.5811
    assert pytest.approx(report["RMSE"], 0.01) == 1.5811
    # MAPE = ( |5-4|/4 + |6-8|/8 ) / 2 * 100 = (0.25 + 0.25) / 2 * 100 = 25.0
    assert report["MAPE"] == 25.0
