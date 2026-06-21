import os
import shutil
import logging
import pandas as pd
from datetime import datetime
import backend.config as cfg

logger = logging.getLogger("pricing_system.inventory.inventory_repository")

def get_current_inventory_path() -> str:
    """
    Returns the configured path to the current inventory CSV file.
    """
    return cfg.CUSTOMER_INVENTORY_CURRENT_PATH

def initialize_inventory_datasets():
    """
    Checks if current and history inventory CSV files exist.
    If they do not exist, and legacy inventory.csv exists, automatically migrates them.
    """
    current_path = get_current_inventory_path()
    history_path = cfg.CUSTOMER_INVENTORY_HISTORY_PATH
    
    # Check if the files already exist
    if os.path.exists(current_path) and os.path.exists(history_path):
        return
        
    data_dir = os.path.dirname(current_path)
    old_inventory_path = os.path.join(data_dir, "inventory.csv")
    
    # Fallback to dev dataset if not found in customer data directory
    if not os.path.exists(old_inventory_path):
        old_inventory_path = os.path.join(cfg.DEV_DATA_DIR, "inventory.csv")
        
    if not os.path.exists(old_inventory_path):
        logger.info("Legacy inventory.csv not found. Skipping auto-migration.")
        return
        
    logger.info(f"Legacy inventory.csv found at {old_inventory_path}. Migrating datasets...")
    try:
        df_old = pd.read_csv(old_inventory_path)
        if df_old.empty:
            return
            
        migration_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Initialize current inventory state (one row per SKU, keeping the last record)
        if not os.path.exists(current_path):
            df_current = df_old.drop_duplicates(subset=["product_id"], keep="last").copy()
            df_current["last_updated"] = migration_time
            if "warehouse_location" in df_current.columns and "warehouse" not in df_current.columns:
                df_current["warehouse"] = df_current["warehouse_location"]
                
            os.makedirs(os.path.dirname(current_path), exist_ok=True)
            df_current.to_csv(current_path, index=False)
            logger.info(f"Successfully migrated current state to {current_path}")
            
        # 2. Initialize history inventory state (all records, snapshot_timestamp column)
        if not os.path.exists(history_path):
            df_history = df_old.copy()
            df_history["snapshot_timestamp"] = migration_time
            if "warehouse_location" in df_history.columns and "warehouse" not in df_history.columns:
                df_history["warehouse"] = df_history["warehouse_location"]
                
            cols = ["snapshot_timestamp"] + [c for c in df_history.columns if c != "snapshot_timestamp"]
            df_history = df_history[cols]
            
            os.makedirs(os.path.dirname(history_path), exist_ok=True)
            df_history.to_csv(history_path, index=False)
            logger.info(f"Successfully migrated history state to {history_path}")
            
    except Exception as e:
        logger.error(f"Error during legacy inventory migration: {str(e)}")

def load_current_inventory() -> pd.DataFrame:
    """
    Loads and returns the current operational inventory DataFrame.
    Automatically initializes datasets if necessary.
    """
    initialize_inventory_datasets()
    current_path = get_current_inventory_path()
    if not os.path.exists(current_path):
        return pd.DataFrame(columns=["product_id", "current_stock"])
    try:
        df = pd.read_csv(current_path)
        if not df.empty:
            df["product_id"] = df["product_id"].astype(str).str.strip()
        return df
    except Exception as e:
        logger.error(f"Failed to load current inventory from {current_path}: {e}")
        return pd.DataFrame(columns=["product_id", "current_stock"])

def save_current_inventory(df: pd.DataFrame) -> None:
    """
    Saves the provided DataFrame as the current operational inventory.
    """
    current_path = get_current_inventory_path()
    try:
        os.makedirs(os.path.dirname(current_path), exist_ok=True)
        df.to_csv(current_path, index=False)
        logger.info(f"Successfully saved current inventory to {current_path}")
    except Exception as e:
        logger.error(f"Failed to save current inventory to {current_path}: {e}")
        raise

def get_product_inventory(product_id: str) -> dict:
    """
    Retrieves inventory attributes for a single product_id as a dictionary.
    """
    df = load_current_inventory()
    if df.empty:
        return {}
    
    p_id = str(product_id).strip()
    match = df[df["product_id"] == p_id]
    if match.empty:
        return {}
        
    row = match.iloc[0].to_dict()
    # Normalize numeric values
    current_stock = pd.to_numeric(row.get("current_stock"), errors='coerce')
    current_stock = int(current_stock) if not pd.isna(current_stock) else 0
    
    reserved_stock = pd.to_numeric(row.get("reserved_stock"), errors='coerce')
    reserved_stock = int(reserved_stock) if not pd.isna(reserved_stock) else 0
    
    net_stock = max(0, current_stock - reserved_stock)
    
    # Check reorder and safety thresholds
    rp = pd.to_numeric(row.get("reorder_point"), errors='coerce')
    rp = rp if not pd.isna(rp) else 1.0
    ss = pd.to_numeric(row.get("safety_stock"), errors='coerce')
    ss = ss if not pd.isna(ss) else rp * 0.4
    
    if net_stock <= ss:
        stock_status = "Critical"
    elif net_stock <= rp:
        stock_status = "Watchlist"
    else:
        stock_status = "Healthy"
        
    return {
        "product_id": row["product_id"],
        "product_name": row.get("product_name", "N/A"),
        "category": row.get("category", "N/A"),
        "brand": row.get("brand", "N/A"),
        "current_stock": current_stock,
        "reserved_stock": reserved_stock,
        "net_stock": net_stock,
        "stock_status": stock_status,
        "warehouse": row.get("warehouse", row.get("warehouse_location", "N/A")),
        "last_updated": row.get("last_updated", "N/A")
    }

def update_product_inventory(product_id: str, stock: int) -> bool:
    """
    Updates the current_stock for a single product_id. Returns True if updated, False otherwise.
    """
    df = load_current_inventory()
    if df.empty:
        return False
        
    p_id = str(product_id).strip()
    mask = df["product_id"] == p_id
    if not mask.any():
        return False
        
    df.loc[mask, "current_stock"] = stock
    df.loc[mask, "last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_current_inventory(df)
    return True

def get_inventory_snapshot() -> pd.DataFrame:
    """
    Returns a copy of the current operational inventory DataFrame.
    """
    return load_current_inventory().copy()
