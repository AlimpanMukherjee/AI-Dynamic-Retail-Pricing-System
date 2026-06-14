import os
import pandas as pd
import streamlit as st
import backend.config as cfg
from backend.alerts.alert_engine import resolve_alert as backend_resolve_alert

COLUMNS = ["timestamp", "alert_type", "severity", "product_id", "message", "status"]

@st.cache_data
def load_alerts() -> pd.DataFrame:
    """
    Loads all generated alerts from alerts.csv.
    """
    path = cfg.CUSTOMER_ALERTS_PATH
    if not os.path.exists(path):
        return pd.DataFrame(columns=COLUMNS)
    try:
        df = pd.read_csv(path)
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = None
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df[COLUMNS]
    except Exception:
        return pd.DataFrame(columns=COLUMNS)


def resolve_alert(product_id: str, alert_type: str) -> bool:
    """
    Resolves an alert by calling the backend resolve utility.
    """
    return backend_resolve_alert(product_id, alert_type)


def get_alerts_summary() -> dict:
    """
    Computes summary counters of open and high severity alerts for the Dashboard.
    """
    df = load_alerts()
    if df.empty:
        return {
            "open_count": 0,
            "high_severity_count": 0,
            "resolved_count": 0,
            "open_list": pd.DataFrame()
        }

    df_open = df[df["status"] == "OPEN"]
    df_high = df_open[df_open["severity"] == "HIGH"]
    df_res = df[df["status"] == "RESOLVED"]

    return {
        "open_count": len(df_open),
        "high_severity_count": len(df_high),
        "resolved_count": len(df_res),
        "open_list": df_open
    }
