import os
import pandas as pd
from datetime import datetime
import streamlit as st
import backend.config as cfg

COLUMNS = [
    "run_timestamp",
    "product_id",
    "retailer",
    "location",
    "engine1_price",
    "engine2_price",
    "engine3_multiplier",
    "engine4_multiplier",
    "final_price",
    "confidence",
    "supply_risk",
    "inventory_pressure",
    "market_pressure",
    "event_active",
    "event_type",
    "attendance",
    "event_score",
    "event_influence",
    "distance_km",
    "duration_hours",
    "impact_level",
    "base_price",
    "e2_contribution_raw",
    "e2_contribution",
    "e3_contribution_raw",
    "e3_contribution",
    "e4_contribution_raw",
    "e4_contribution",
    "e5_contribution_raw",
    "e5_contribution",
    "total_uplift",
    "confidence_score",
    "confidence_level",
    "sales_history_count",
    "engine2_confidence",
    "price_before_event",
    "event_opportunity_score",
    "event_uplift_pct",
    "event_uplift_amount",
    "expected_event_demand",
    "available_inventory",
    "inventory_shortage",
    "inventory_coverage",
    "elasticity",
    "recommended_price_increase_pct",
    "mrp",
    "price_before_mrp",
    "mrp_limit_applied"
]

def save_pricing_decision(
    product_id: str,
    retailer: str,
    location: str,
    engine1_price: float,
    engine2_price: float,
    engine3_multiplier: float,
    engine4_multiplier: float,
    final_price: float,
    confidence: float,
    supply_risk: float,
    inventory_pressure: float,
    market_pressure: float,
    event_active: bool = False,
    event_type: str = "Other",
    attendance: int = 0,
    event_score: float = 0.0,
    event_influence: float = 0.0,
    distance_km: float = 2.0,
    duration_hours: float = 4.0,
    impact_level: str = "LOW",
    base_price: float = None,
    e2_contribution_raw: float = None,
    e2_contribution: float = None,
    e3_contribution_raw: float = None,
    e3_contribution: float = None,
    e4_contribution_raw: float = None,
    e4_contribution: float = None,
    e5_contribution_raw: float = None,
    e5_contribution: float = None,
    total_uplift: float = None,
    confidence_score: float = None,
    confidence_level: str = None,
    sales_history_count: int = None,
    engine2_confidence: float = None,
    price_before_event: float = None,
    event_opportunity_score: float = None,
    event_uplift_pct: float = None,
    event_uplift_amount: float = None,
    expected_event_demand: float = None,
    available_inventory: float = None,
    inventory_shortage: float = None,
    inventory_coverage: float = None,
    elasticity: float = None,
    recommended_price_increase_pct: float = None,
    mrp: float = None,
    price_before_mrp: float = None,
    mrp_limit_applied: bool = False
):
    """
    Saves a pricing decision to customer_data/pricing_history.csv.
    """
    history_path = cfg.CUSTOMER_PRICING_HISTORY_PATH
    os.makedirs(os.path.dirname(history_path), exist_ok=True)

    record = {
        "run_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "product_id": str(product_id).strip(),
        "retailer": str(retailer).strip(),
        "location": str(location).strip(),
        "engine1_price": round(float(engine1_price), 4),
        "engine2_price": round(float(engine2_price), 4),
        "engine3_multiplier": round(float(engine3_multiplier), 4),
        "engine4_multiplier": round(float(engine4_multiplier), 4),
        "final_price": round(float(final_price), 4),
        "confidence": round(float(confidence), 4),
        "supply_risk": round(float(supply_risk), 4),
        "inventory_pressure": round(float(inventory_pressure), 4),
        "market_pressure": round(float(market_pressure), 4),
        "event_active": bool(event_active),
        "event_type": str(event_type),
        "attendance": int(attendance),
        "event_score": round(float(event_score), 4),
        "event_influence": round(float(event_influence), 4),
        "distance_km": round(float(distance_km), 2),
        "duration_hours": round(float(duration_hours), 2),
        "impact_level": str(impact_level),
        "base_price": round(float(base_price), 4) if base_price is not None else None,
        "e2_contribution_raw": round(float(e2_contribution_raw), 4) if e2_contribution_raw is not None else None,
        "e2_contribution": round(float(e2_contribution), 4) if e2_contribution is not None else None,
        "e3_contribution_raw": round(float(e3_contribution_raw), 4) if e3_contribution_raw is not None else None,
        "e3_contribution": round(float(e3_contribution), 4) if e3_contribution is not None else None,
        "e4_contribution_raw": round(float(e4_contribution_raw), 4) if e4_contribution_raw is not None else None,
        "e4_contribution": round(float(e4_contribution), 4) if e4_contribution is not None else None,
        "e5_contribution_raw": round(float(e5_contribution_raw), 4) if e5_contribution_raw is not None else None,
        "e5_contribution": round(float(e5_contribution), 4) if e5_contribution is not None else None,
        "total_uplift": round(float(total_uplift), 4) if total_uplift is not None else None,
        "confidence_score": round(float(confidence_score), 2) if confidence_score is not None else None,
        "confidence_level": str(confidence_level) if confidence_level is not None else None,
        "sales_history_count": int(sales_history_count) if sales_history_count is not None else None,
        "engine2_confidence": round(float(engine2_confidence), 4) if engine2_confidence is not None else None,
        "price_before_event": round(float(price_before_event), 4) if price_before_event is not None else None,
        "event_opportunity_score": round(float(event_opportunity_score), 4) if event_opportunity_score is not None else None,
        "event_uplift_pct": round(float(event_uplift_pct), 4) if event_uplift_pct is not None else None,
        "event_uplift_amount": round(float(event_uplift_amount), 4) if event_uplift_amount is not None else None,
        "expected_event_demand": round(float(expected_event_demand), 4) if expected_event_demand is not None else None,
        "available_inventory": round(float(available_inventory), 4) if available_inventory is not None else None,
        "inventory_shortage": round(float(inventory_shortage), 4) if inventory_shortage is not None else None,
        "inventory_coverage": round(float(inventory_coverage), 4) if inventory_coverage is not None else None,
        "elasticity": round(float(elasticity), 4) if elasticity is not None else None,
        "recommended_price_increase_pct": round(float(recommended_price_increase_pct), 4) if recommended_price_increase_pct is not None else None,
        "mrp": round(float(mrp), 4) if mrp is not None else None,
        "price_before_mrp": round(float(price_before_mrp), 4) if price_before_mrp is not None else None,
        "mrp_limit_applied": bool(mrp_limit_applied)
    }

    df_new = pd.DataFrame([record])

    if os.path.exists(history_path):
        try:
            df_existing = pd.read_csv(history_path)
            # Ensure correct types and format compatibility
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        except Exception:
            df_combined = df_new
    else:
        df_combined = df_new

    df_combined.to_csv(history_path, index=False)

    # Invalidate cached reads in Streamlit
    try:
        st.cache_data.clear()
    except Exception:
        # Ignore if running outside streamlit session context
        pass


@st.cache_data
def load_pricing_history() -> pd.DataFrame:
    """
    Loads all saved pricing decisions from pricing_history.csv.
    """
    history_path = cfg.CUSTOMER_PRICING_HISTORY_PATH
    if not os.path.exists(history_path):
        return pd.DataFrame(columns=COLUMNS)
    try:
        df = pd.read_csv(history_path)
        # Check that columns match
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = None
        df["run_timestamp"] = pd.to_datetime(df["run_timestamp"])
        return df[COLUMNS]
    except Exception:
        return pd.DataFrame(columns=COLUMNS)


def get_product_pricing_history(product_id: str) -> pd.DataFrame:
    """
    Extracts pricing history records matching a specific SKU.
    """
    df = load_pricing_history()
    if df.empty:
        return df
    return df[df["product_id"] == str(product_id).strip()]


def get_latest_pricing(product_id: str, retailer: str, location: str) -> dict:
    """
    Queries pricing history to find the most recent matching pricing decision.
    """
    history_path = cfg.CUSTOMER_PRICING_HISTORY_PATH
    if not os.path.exists(history_path):
        return None
    try:
        df = pd.read_csv(history_path)
        if df.empty:
            return None
        # Filters
        mask = (
            (df["product_id"].astype(str).str.strip() == str(product_id).strip()) &
            (df["retailer"].astype(str).str.strip().str.lower() == str(retailer).strip().lower()) &
            (df["location"].astype(str).str.strip().str.lower() == str(location).strip().lower())
        )
        filtered = df[mask]
        if filtered.empty:
            return None
        # Sort by timestamp
        filtered = filtered.sort_values(by="run_timestamp", ascending=False)
        return filtered.iloc[0].to_dict()
    except Exception:
        return None
