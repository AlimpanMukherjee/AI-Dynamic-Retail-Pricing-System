import os
import pytest
import pandas as pd
import backend.config as cfg
from backend.inventory.inventory_repository import (
    load_current_inventory,
    get_product_inventory,
    get_current_inventory_path
)
from backend.data_ingestion.sales_ingestion import append_sales_data
from backend.pipeline.pricing_pipeline import run_coordinated_pricing
from frontend.services.inventory_service import get_inventory_summary

def test_sales_upload_inventory_sync(tmp_path, monkeypatch):
    # Setup isolated temporary paths directly on cfg to avoid cache conflicts with other tests
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_CURRENT_PATH", str(tmp_path / "inventory_current.csv"))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_PATH", str(tmp_path / "inventory_current.csv"))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_HISTORY_PATH", str(tmp_path / "inventory_history.csv"))
    monkeypatch.setattr(cfg, "CUSTOMER_SALES_PATH", str(tmp_path / "sales.csv"))
    monkeypatch.setattr(cfg, "CUSTOMER_PRODUCTS_PATH", str(tmp_path / "products.csv"))
    monkeypatch.setattr(cfg, "CUSTOMER_PROCUREMENT_PATH", str(tmp_path / "procurement.csv"))
    monkeypatch.setattr(cfg, "CUSTOMER_COMPETITOR_PATH", str(tmp_path / "competitors.csv"))
    monkeypatch.setattr(cfg, "CUSTOMER_ALERTS_PATH", str(tmp_path / "alerts.csv"))
    monkeypatch.setattr(cfg, "DEV_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(cfg, "_get_customer_data_dir", lambda: str(tmp_path))
    
    print("\n[DEBUG] cfg.DEV_DATA_DIR is:", cfg.DEV_DATA_DIR)
    print("[DEBUG] CUSTOMER_INVENTORY_CURRENT_PATH is:", cfg.CUSTOMER_INVENTORY_CURRENT_PATH)
    print("[DEBUG] get_current_inventory_path() is:", get_current_inventory_path())

    products_file = tmp_path / "products.csv"
    inventory_file = tmp_path / "inventory_current.csv"
    history_file = tmp_path / "inventory_history.csv"
    sales_file = tmp_path / "sales.csv"
    procurement_file = tmp_path / "procurement.csv"
    competitors_file = tmp_path / "competitors.csv"
    alerts_file = tmp_path / "alerts.csv"

    # Initialize dataframes
    df_products = pd.DataFrame([{
        "product_id": "SKU_1000",
        "product_name": "Test Product",
        "category": "PACKAGED FOODS",
        "brand": "Test Brand",
        "base_market_price": 10.0,
        "supplier_price": 6.0,
        "freight_cost": 1.0,
        "warehouse_cost": 0.5,
        "gst_tax": 0.5
    }])
    df_products.to_csv(products_file, index=False)

    df_inventory = pd.DataFrame([{
        "product_id": "SKU_1000",
        "product_name": "Test Product",
        "category": "PACKAGED FOODS",
        "brand": "Test Brand",
        "current_stock": 2000,
        "reserved_stock": 0,
        "reorder_point": 500,
        "safety_stock": 200,
        "sales_velocity_per_day": 30.0,  # Ensure days_of_supply <= 5.0 when stock is 100
        "sales_velocity": 30.0,
        "lead_time_days": 5,
        "lead_time": 5,
        "stock_age_days": 10,
        "warehouse_location": "Bengaluru",
        "warehouse": "Bengaluru",
        "retailer_company": "Reliance Retail",
        "store_location": "Bengaluru",
        "last_updated": "2026-06-21 12:00:00"
    }])
    df_inventory.to_csv(inventory_file, index=False)
    
    # History file must exist for ingestion
    pd.DataFrame(columns=["snapshot_timestamp", "product_id", "current_stock", "reserved_stock", "warehouse"]).to_csv(history_file, index=False)

    df_sales = pd.DataFrame(columns=["date", "product_id", "selling_price", "units_sold"])
    df_sales.to_csv(sales_file, index=False)

    df_procurement = pd.DataFrame([{
        "product_id": "SKU_1000",
        "supplier_id": "SUP_001",
        "supplier_price": 6.0,
        "freight_cost": 1.0,
        "warehouse_cost": 0.5,
        "gst_tax": 0.5,
        "supplier_reliability": 0.95
    }])
    df_procurement.to_csv(procurement_file, index=False)

    df_competitors = pd.DataFrame([{
        "date": "2026-06-21",
        "product_id": "SKU_1000",
        "product_name": "Test Product",
        "competitor_price": 9.5,
        "competitor_name": "Comp1",
        "market_region": "Bengaluru",
        "promotion_active": False,
        "rating": 4.5
    }])
    df_competitors.to_csv(competitors_file, index=False)

    # Patch Engine 2 run_pipeline to return standard mock values instantly (bypassing slow training)
    monkeypatch.setattr(
        "backend.layer1.engine2.run_pipeline",
        lambda *args, **kwargs: {
            "optimal_price": 11.0,
            "expected_demand": 50.0,
            "elasticity": -1.5,
            "prediction_source": "historical_sales",
            "similar_products_used": []
        }
    )

    # Scenario: Upload Sales -> 1900 sold
    df_upload = pd.DataFrame([{
        "date": "2026-06-21",
        "product_id": "SKU_1000",
        "selling_price": 10.0,
        "units_sold": 1900
    }])

    # 1. Action: Upload sales
    rows_added = append_sales_data(df_upload)
    assert rows_added == 1

    # 2. Verify inventory_current.csv = 100 stock remaining
    df_curr_inv = load_current_inventory()
    sku_row = df_curr_inv[df_curr_inv["product_id"] == "SKU_1000"].iloc[0]
    assert sku_row["current_stock"] == 100
    assert sku_row["sales_velocity_per_day"] == 1900.0
 
    # 3. Action: Run Pricing Pipeline
    result = run_coordinated_pricing(
        product_id="SKU_1000",
        retailer_company="Reliance Retail",
        store_location="Bengaluru"
    )
 
    # 4. Verify Engine 3 Stock = 100
    e3_state = result["pricing_state"]["E3"]
    assert e3_state["net_stock"] == 100
    # Expected days_of_supply = 100 / 1900 = 0.0526... rounded to 1 decimal place is 0.1
    assert abs(e3_state["days_of_supply"] - 0.1) < 0.01

    # 5. Verify Dashboard stock = 100
    dashboard_summary = get_inventory_summary()
    assert dashboard_summary["total_stock"] == 100

    # 6. Verify Product Search stock = 100
    product_search_inv = get_product_inventory("SKU_1000")
    assert product_search_inv["current_stock"] == 100

    # 7. Verify Alert Engine generated a LOW_STOCK alert
    assert os.path.exists(alerts_file)
    df_alerts = pd.read_csv(alerts_file)
    low_stock_alerts = df_alerts[df_alerts["alert_type"] == "LOW_STOCK"]
    assert len(low_stock_alerts) == 1
    assert low_stock_alerts.iloc[0]["status"] == "OPEN"
    assert low_stock_alerts.iloc[0]["product_id"] == "SKU_1000"
