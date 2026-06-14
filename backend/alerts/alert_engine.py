import os
import pandas as pd
from datetime import datetime
import streamlit as st
import backend.config as cfg

from backend.alerts.alert_rules import (
    check_low_stock,
    check_stockout_risk,
    check_supply_risk,
    check_price_change
)

COLUMNS = ["timestamp", "alert_type", "severity", "product_id", "message", "status"]

def _initialize_alerts_csv():
    """
    Initializes alerts.csv if it does not exist.
    """
    path = cfg.CUSTOMER_ALERTS_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        pd.DataFrame(columns=COLUMNS).to_csv(path, index=False)


def generate_alerts(product_id: str, pricing_result: dict):
    """
    Runs alert rule checks on the pricing results and appends triggers to alerts.csv.
    Prevents duplicate active alerts for the same SKU & alert type.
    """
    _initialize_alerts_csv()
    path = cfg.CUSTOMER_ALERTS_PATH

    # Extract metrics
    pricing_state = pricing_result.get("pricing_state", {})
    e1 = pricing_state.get("E1", {})
    e3 = pricing_state.get("E3", {})
    e4 = pricing_state.get("E4", {})

    days_of_supply = e3.get("days_of_supply", 999.0)
    stockout_risk = e3.get("stockout_risk", 0.0)
    supply_risk = e1.get("supply_risk", 0.0)
    final_price = pricing_result.get("final_price", 0.0)

    # Get retailer and location for localized comparison
    retailer = e3.get("retailer_company") or e4.get("retailer_company") or "N/A"
    location = e3.get("store_location") or e4.get("market_region") or "N/A"

    # Find previous recommendation to check price deviations
    previous_price = 0.0
    try:
        from frontend.services.pricing_history_service import get_latest_pricing
        prev = get_latest_pricing(product_id, retailer, location)
        if prev:
            previous_price = float(prev.get("final_price", 0.0))
    except Exception:
        pass

    # Read existing alerts to check duplicates
    try:
        df_existing = pd.read_csv(path)
    except Exception:
        df_existing = pd.DataFrame(columns=COLUMNS)

    new_alerts = []

    def add_alert(alert_type, severity, message):
        # Duplicate check: Is there already an OPEN alert of this type for this SKU?
        is_dup = False
        if not df_existing.empty:
            mask = (
                (df_existing["product_id"].astype(str).str.strip() == str(product_id).strip()) &
                (df_existing["alert_type"] == alert_type) &
                (df_existing["status"] == "OPEN")
            )
            if mask.any():
                is_dup = True

        if not is_dup:
            new_alerts.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "alert_type": alert_type,
                "severity": severity,
                "product_id": str(product_id).strip(),
                "message": message,
                "status": "OPEN"
            })

    # Rule 1: Low Stock Alert
    if check_low_stock(days_of_supply):
        add_alert(
            "LOW_STOCK",
            "HIGH",
            f"Low stock warning: only {days_of_supply:.1f} days of supply remaining."
        )

    # Rule 2: Stockout Alert
    if check_stockout_risk(stockout_risk):
        add_alert(
            "STOCKOUT_RISK",
            "HIGH",
            f"High stockout risk detected: {stockout_risk:.2%}"
        )

    # Rule 3: Procurement Alert
    if check_supply_risk(supply_risk):
        add_alert(
            "SUPPLY_RISK",
            "HIGH",
            f"High supply procurement risk detected: {supply_risk:.2%}"
        )

    # Rule 4: Price Change Alert
    if previous_price > 0.0 and check_price_change(final_price, previous_price):
        dev = (final_price - previous_price) / previous_price
        add_alert(
            "PRICE_CHANGE",
            "WARNING",
            f"Significant price change: from ₹{previous_price:.2f} to ₹{final_price:.2f} ({dev:+.1%})."
        )

    if new_alerts:
        df_new = pd.DataFrame(new_alerts)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.to_csv(path, index=False)
        try:
            st.cache_data.clear()
        except Exception:
            pass


def resolve_alert(product_id: str, alert_type: str) -> bool:
    """
    Sets the status of open alerts of alert_type for product_id to RESOLVED.
    """
    _initialize_alerts_csv()
    path = cfg.CUSTOMER_ALERTS_PATH
    try:
        df = pd.read_csv(path)
        if df.empty:
            return False

        mask = (
            (df["product_id"].astype(str).str.strip() == str(product_id).strip()) &
            (df["alert_type"].astype(str).str.strip() == str(alert_type).strip()) &
            (df["status"] == "OPEN")
        )
        if not mask.any():
            return False

        df.loc[mask, "status"] = "RESOLVED"
        df.to_csv(path, index=False)
        try:
            st.cache_data.clear()
        except Exception:
            pass
        return True
    except Exception:
        return False
