import os
import shutil
import pandas as pd
from datetime import datetime
import json
import joblib

import backend.config as cfg
from backend.layer1.engine2.data_loader import load_and_join_data
from backend.layer1.engine2.preprocessing import preprocess
from backend.layer1.engine2.trainer import train_model
from backend.layer1.engine2.model_store import (
    save_model as store_save_model,
    load_model as store_load_model
)

# Operational Paths
OPERATIONAL_MODEL_DIR = os.path.join(cfg.PROJECT_ROOT, "backend", "models")
OPERATIONAL_MODEL_PATH = os.path.join(OPERATIONAL_MODEL_DIR, "engine2_model.pkl")
OPERATIONAL_METADATA_PATH = os.path.join(OPERATIONAL_MODEL_DIR, "engine2_metadata.json")

def _initialize_registry():
    """
    Initializes the model registry CSV if it does not exist.
    """
    registry_path = cfg.CUSTOMER_MODEL_REGISTRY_PATH
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    os.makedirs(cfg.MODELS_DIR, exist_ok=True)

    if not os.path.exists(registry_path):
        df_registry = pd.DataFrame(columns=[
            "model_version",
            "training_date",
            "training_rows",
            "train_r2",
            "val_r2",
            "test_r2",
            "active"
        ])
        df_registry.to_csv(registry_path, index=False)


def train_new_model() -> tuple:
    """
    Trains a new XGBoost forecasting model using the latest sales history.
    Saves the trained model and returns (version, eval_stats, training_rows) or status dict.
    """
    _initialize_registry()

    sales_path = cfg.CUSTOMER_SALES_PATH
    if not os.path.exists(sales_path):
        # Fallback to dev dataset under tests or if missing
        sales_path = cfg.DEV_SALES_PATH

    # Count rows in resolved sales_path
    sales_count = 0
    if os.path.exists(sales_path):
        try:
            sales_count = len(pd.read_csv(sales_path))
        except Exception:
            pass

    if sales_count < 500:
        return {
            "status": "limited_data",
            "message": "Insufficient data for reliable training. Pricing system remains operational with reduced Engine 2 influence."
        }

    products_path = cfg.CUSTOMER_PRODUCTS_PATH
    if not os.path.exists(products_path):
        products_path = cfg.DEV_PRODUCTS_PATH

    inventory_path = cfg.CUSTOMER_INVENTORY_PATH
    if not os.path.exists(inventory_path):
        inventory_path = cfg.DEV_INVENTORY_PATH

    # Load and preprocess
    df = load_and_join_data(sales_path, products_path, inventory_path)
    df_preprocessed, encoders = preprocess(df)

    # Train
    model, features, eval_stats = train_model(df_preprocessed)

    # Determine version string
    registry_path = cfg.CUSTOMER_MODEL_REGISTRY_PATH
    df_reg = pd.read_csv(registry_path)
    new_version_num = len(df_reg) + 1
    version = f"v{new_version_num}"

    # Save to root models dir
    save_model(model, features, encoders, version)

    # Log to registry as INACTIVE initially
    new_record = {
        "model_version": version,
        "training_date": datetime.now().strftime("%Y-%m-%d"),
        "training_rows": int(len(df)),
        "train_r2": float(eval_stats["train_r2"]),
        "val_r2": float(eval_stats["validation_r2"]),
        "test_r2": float(eval_stats["test_r2"]),
        "active": False
    }
    
    df_reg = pd.concat([df_reg, pd.DataFrame([new_record])], ignore_index=True)
    df_reg.to_csv(registry_path, index=False)

    return version, eval_stats, len(df)


def save_model(model, features, encoders, version: str):
    """
    Saves model components into models/model_v{version}.pkl.
    """
    os.makedirs(cfg.MODELS_DIR, exist_ok=True)
    filepath = os.path.join(cfg.MODELS_DIR, f"model_{version}.pkl")
    store_save_model(model, features, encoders, filepath)


def activate_model(version: str) -> bool:
    """
    Activates the selected model version in the registry.
    Copies it to the operational directory so the pricing pipeline consumes it.
    """
    _initialize_registry()
    registry_path = cfg.CUSTOMER_MODEL_REGISTRY_PATH
    if not os.path.exists(registry_path):
        return False

    df_reg = pd.read_csv(registry_path)
    if version not in df_reg["model_version"].values:
        return False

    # Mark active
    df_reg["active"] = (df_reg["model_version"] == version)
    df_reg.to_csv(registry_path, index=False)

    # Copy to operational path
    src_pkl = os.path.join(cfg.MODELS_DIR, f"model_{version}.pkl")
    if not os.path.exists(src_pkl):
        return False

    os.makedirs(OPERATIONAL_MODEL_DIR, exist_ok=True)
    shutil.copyfile(src_pkl, OPERATIONAL_MODEL_PATH)

    # Write operational metadata json
    row = df_reg[df_reg["model_version"] == version].iloc[0]
    meta = {
        "model_version": str(row["model_version"]),
        "trained_at": f"{row['training_date']} 00:00:00",
        "training_rows": int(row["training_rows"]),
        "train_r2": float(row["train_r2"]),
        "validation_r2": float(row["val_r2"]),
        "test_r2": float(row["test_r2"])
    }
    
    with open(OPERATIONAL_METADATA_PATH, 'w') as f:
        json.dump(meta, f, indent=4)

    return True


def load_active_model() -> tuple:
    """
    Loads model components of the currently active model from the registry.
    """
    _initialize_registry()
    registry_path = cfg.CUSTOMER_MODEL_REGISTRY_PATH
    if os.path.exists(registry_path):
        try:
            df_reg = pd.read_csv(registry_path)
            active_rows = df_reg[df_reg["active"] == True]
            if not active_rows.empty:
                version = active_rows.iloc[0]["model_version"]
                pkl_path = os.path.join(cfg.MODELS_DIR, f"model_{version}.pkl")
                if os.path.exists(pkl_path):
                    return store_load_model(pkl_path)
        except Exception:
            pass

    # Fallback to standard model path
    return store_load_model(OPERATIONAL_MODEL_PATH)
