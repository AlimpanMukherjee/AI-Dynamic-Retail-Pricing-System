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
    "market_pressure"
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
    market_pressure: float
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
        "market_pressure": round(float(market_pressure), 4)
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
