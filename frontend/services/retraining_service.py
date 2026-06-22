import os
import pandas as pd
import streamlit as st
import backend.config as cfg
from backend.retraining.retrain_model import (
    train_new_model,
    activate_model,
    _initialize_registry
)

@st.cache_data
def load_model_registry() -> pd.DataFrame:
    """
    Loads model version entries from model_registry.csv.
    """
    _initialize_registry()
    path = cfg.CUSTOMER_MODEL_REGISTRY_PATH
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def get_active_model_details() -> dict:
    """
    Resolves metrics and properties for the currently active ML model.
    """
    df = load_model_registry()
    if df.empty:
        return {}
    active_rows = df[df["active"] == True]
    if active_rows.empty:
        # Check first version as fallback
        return df.iloc[0].to_dict() if len(df) > 0 else {}
    return active_rows.iloc[0].to_dict()


def execute_model_retraining(force_override_gate: bool = False) -> dict:
    """
    Executes model retraining, executes chronological evaluation splits,
    and runs the safety R2 validation threshold checks.
    """
    # 1. Get current active model info before training
    active_info = get_active_model_details()
    old_val_r2 = float(active_info.get("val_r2", -999.0)) if active_info else -999.0

    # 2. Run training in backend
    res = train_new_model()
    if isinstance(res, dict) and res.get("status") == "limited_data":
        return res
        
    version, eval_stats, training_rows = res
    new_val_r2 = float(eval_stats["validation_r2"])

    # 3. Validation Safety Gate Check
    gate_passed = (new_val_r2 > old_val_r2) or force_override_gate or (old_val_r2 == -999.0)

    # Clear cache since registry has a new version
    st.cache_data.clear()

    if gate_passed:
        # Activate model version operationally
        activate_model(version)
        st.cache_data.clear()
        return {
            "status": "activated",
            "version": version,
            "new_val_r2": new_val_r2,
            "old_val_r2": old_val_r2 if old_val_r2 != -999.0 else "N/A",
            "training_rows": training_rows,
            "train_r2": eval_stats["train_r2"],
            "test_r2": eval_stats["test_r2"]
        }
    else:
        # Inactive model version is created but old remains operational
        return {
            "status": "gate_failed",
            "version": version,
            "new_val_r2": new_val_r2,
            "old_val_r2": old_val_r2,
            "training_rows": training_rows,
            "train_r2": eval_stats["train_r2"],
            "test_r2": eval_stats["test_r2"]
        }
