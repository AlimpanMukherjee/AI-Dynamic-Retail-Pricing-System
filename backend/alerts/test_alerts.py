import os
import pytest
import pandas as pd
import backend.config as cfg
from backend.alerts.alert_rules import (
    check_low_stock,
    check_stockout_risk,
    check_supply_risk,
    check_price_change
)
from backend.alerts.alert_engine import generate_alerts, resolve_alert

@pytest.fixture
def temp_alerts_paths(tmp_path, monkeypatch):
    """
    Isolates alerts.csv and pricing_history.csv inside a temporary directory.
    """
    alerts_file = tmp_path / "alerts.csv"
    history_file = tmp_path / "pricing_history.csv"

    monkeypatch.setattr(cfg, "CUSTOMER_ALERTS_PATH", str(alerts_file))
    monkeypatch.setattr(cfg, "CUSTOMER_PRICING_HISTORY_PATH", str(history_file))

    return {
        "alerts": alerts_file,
        "history": history_file
    }


def test_alert_rules():
    # Test low stock rules
    assert check_low_stock(5.0) == True
    assert check_low_stock(7.0) == False
    assert check_low_stock(10.0) == False

    # Test stockout risk rules
    assert check_stockout_risk(0.85) == True
    assert check_stockout_risk(0.80) == False
    assert check_stockout_risk(0.50) == False

    # Test supply risk rules
    assert check_supply_risk(0.95) == True
    assert check_supply_risk(0.90) == False
    assert check_supply_risk(0.30) == False

    # Test price change rules
    assert check_price_change(110.0, 100.0) == False  # Exactly 10%
    assert check_price_change(111.0, 100.0) == True   # 11% (exceeds 10%)
    assert check_price_change(89.0, 100.0) == True    # -11% (exceeds 10%)
    assert check_price_change(95.0, 100.0) == False   # -5%


def test_alert_generation_and_duplication(temp_alerts_paths):
    # Mock pricing pipeline result that triggers all alerts
    mock_pricing_result = {
        "final_price": 120.0,
        "confidence": 0.95,
        "pricing_state": {
            "E1": {
                "supply_risk": 0.95,  # triggers SUPPLY_RISK
                "minimum_safe_price": 90.0
            },
            "E3": {
                "days_of_supply": 4.5,     # triggers LOW_STOCK
                "stockout_risk": 0.88,    # triggers STOCKOUT_RISK
                "recommended_multiplier": 1.0,
                "retailer_company": "Reliance Retail",
                "store_location": "Mumbai"
            },
            "E4": {
                "market_region": "Mumbai",
                "recommended_multiplier": 1.0
            }
        }
    }

    # Generate first time
    generate_alerts("SKU_9999", mock_pricing_result)
    
    assert os.path.exists(temp_alerts_paths["alerts"])
    df = pd.read_csv(temp_alerts_paths["alerts"])
    
    # LOW_STOCK, STOCKOUT_RISK, SUPPLY_RISK should be triggered
    # (PRICE_CHANGE is not triggered since there is no previous history yet)
    assert len(df) == 3
    assert all(df["status"] == "OPEN")
    assert all(df["product_id"] == "SKU_9999")
    assert set(df["alert_type"].values) == {"LOW_STOCK", "STOCKOUT_RISK", "SUPPLY_RISK"}

    # Generate a second time with identical data - should NOT create duplicate alerts
    generate_alerts("SKU_9999", mock_pricing_result)
    df_dup = pd.read_csv(temp_alerts_paths["alerts"])
    assert len(df_dup) == 3  # Still only 3 open alerts!


def test_alert_resolution_workflow(temp_alerts_paths):
    mock_pricing_result = {
        "final_price": 100.0,
        "pricing_state": {
            "E1": {"supply_risk": 0.95},
            "E3": {
                "days_of_supply": 4.0,
                "stockout_risk": 0.90,
                "retailer_company": "Reliance Retail",
                "store_location": "Mumbai"
            }
        }
    }

    # Generate alerts
    generate_alerts("SKU_1056", mock_pricing_result)
    
    df = pd.read_csv(temp_alerts_paths["alerts"])
    assert len(df) == 3
    assert len(df[df["status"] == "OPEN"]) == 3

    # Resolve LOW_STOCK alert
    success = resolve_alert("SKU_1056", "LOW_STOCK")
    assert success == True

    df_res = pd.read_csv(temp_alerts_paths["alerts"])
    assert df_res[df_res["alert_type"] == "LOW_STOCK"]["status"].iloc[0] == "RESOLVED"
    assert df_res[df_res["alert_type"] == "STOCKOUT_RISK"]["status"].iloc[0] == "OPEN"

    # Try resolving again - should return False since it's already resolved
    success_retry = resolve_alert("SKU_1056", "LOW_STOCK")
    assert success_retry == False

    # Generate alerts again - should re-trigger LOW_STOCK because it was resolved
    generate_alerts("SKU_1056", mock_pricing_result)
    df_retriggered = pd.read_csv(temp_alerts_paths["alerts"])
    
    # We should have the old resolved alert, the re-triggered open alert,
    # and the other 2 alerts which remained open (and thus were not duplicated)
    assert len(df_retriggered) == 4
    assert len(df_retriggered[df_retriggered["status"] == "OPEN"]) == 3
    assert len(df_retriggered[df_retriggered["status"] == "RESOLVED"]) == 1
