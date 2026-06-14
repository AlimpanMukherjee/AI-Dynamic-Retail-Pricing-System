import os
import shutil
import logging
import pandas as pd
from datetime import datetime
from typing import Union
from io import StringIO, BytesIO

import backend.config as cfg

logger = logging.getLogger("pricing_system.inventory.inventory_ingestion")

def initialize_inventory_datasets():
    """
    Checks if current and history inventory CSV files exist.
    If they do not exist, and legacy inventory.csv exists, automatically migrates them.
    """
    current_path = cfg.CUSTOMER_INVENTORY_CURRENT_PATH
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


def validate_inventory_file(file_source) -> pd.DataFrame:
    """
    Reads the upload source and verifies schema and content boundaries.
    Mandatory columns: product_id, current_stock.
    Rejects the upload if duplicate SKU records exist within the file itself.
    """
    try:
        if isinstance(file_source, pd.DataFrame):
            df = file_source.copy()
        elif hasattr(file_source, 'read'):
            # File-like object (StringIO, BytesIO, UploadedFile)
            df = pd.read_csv(file_source)
        else:
            df = pd.read_csv(str(file_source))
    except Exception as e:
        logger.error(f"Failed to parse CSV upload: {str(e)}")
        raise ValueError(f"Failed to read CSV source: {str(e)}")

    # Support compatibility rename: if 'stock' is present but 'current_stock' is not
    if "stock" in df.columns and "current_stock" not in df.columns:
        df["current_stock"] = df["stock"]

    # Verify mandatory columns
    for col in ["product_id", "current_stock"]:
        if col not in df.columns:
            raise ValueError(f"Validation Error: Missing required column '{col}' in inventory dataset")

    # Clean and validate product_id
    if df["product_id"].isnull().any():
        raise ValueError("Validation Error: product_id cannot be empty")
    df["product_id"] = df["product_id"].astype(str).str.strip()
    if (df["product_id"] == "").any() or (df["product_id"] == "nan").any():
        raise ValueError("Validation Error: product_id cannot be empty")

    # Validate duplicate products inside the uploaded file itself
    if df["product_id"].duplicated().any():
        dup_sku = df[df["product_id"].duplicated()]["product_id"].iloc[0]
        raise ValueError(f"Validation Error: Duplicate SKU records detected within the upload file for SKU: {dup_sku}")

    # Validate current_stock >= 0
    try:
        df["current_stock"] = pd.to_numeric(df["current_stock"])
    except Exception:
        raise ValueError("Validation Error: Column 'current_stock' must be numeric in inventory dataset")
    if (df["current_stock"] < 0).any():
        bad_sku = df[df["current_stock"] < 0]["product_id"].iloc[0]
        raise ValueError(f"Validation Error: Negative current_stock detected for SKU: {bad_sku}")

    # Validate reserved_stock >= 0 if present
    if "reserved_stock" in df.columns:
        try:
            df["reserved_stock"] = pd.to_numeric(df["reserved_stock"])
        except Exception:
            raise ValueError("Validation Error: Column 'reserved_stock' must be numeric in inventory dataset")
        if (df["reserved_stock"] < 0).any():
            bad_sku = df[df["reserved_stock"] < 0]["product_id"].iloc[0]
            raise ValueError(f"Validation Error: Negative reserved_stock detected for SKU: {bad_sku}")

    return df


def append_inventory_history(df: pd.DataFrame, timestamp_str: str):
    """
    Appends validated inventory records to inventory_history.csv.
    Inserts snapshot_timestamp column and preserves all columns from the upload,
    aligning schemas by appending new columns and mapping values to matching headers.
    """
    history_path = cfg.CUSTOMER_INVENTORY_HISTORY_PATH
    
    # Initialize datasets if legacy file needs migration first
    initialize_inventory_datasets()

    df_hist = df.copy()
    df_hist["snapshot_timestamp"] = timestamp_str

    if os.path.exists(history_path):
        df_existing = pd.read_csv(history_path)
        # Ensure any new columns present in the upload are added to the existing structure
        for col in df_hist.columns:
            if col not in df_existing.columns:
                df_existing[col] = None
        df_combined = pd.concat([df_existing, df_hist], ignore_index=True, sort=False)
    else:
        df_combined = df_hist

    # Place snapshot_timestamp first
    cols = ["snapshot_timestamp"] + [c for c in df_combined.columns if c != "snapshot_timestamp"]
    df_combined = df_combined[cols]

    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    df_combined.to_csv(history_path, index=False)
    logger.info(f"Appended {len(df_hist)} records to history path: {history_path}")


def update_current_inventory(df: pd.DataFrame, timestamp_str: str) -> tuple:
    """
    Performs UPSERT logic into inventory_current.csv.
    Explicit Overwrite Rule:
      - Columns present in upload overwrite old values.
      - Columns absent in upload are preserved for existing SKUs.
    Sets 'last_updated' to the upload timestamp.
    Returns: (inserted_count, updated_count)
    """
    current_path = cfg.CUSTOMER_INVENTORY_CURRENT_PATH
    
    # Initialize datasets if legacy file needs migration first
    initialize_inventory_datasets()

    if os.path.exists(current_path):
        df_curr = pd.read_csv(current_path)
        df_curr["product_id"] = df_curr["product_id"].astype(str).str.strip()
    else:
        df_curr = pd.DataFrame(columns=["product_id"])

    # Extract target upload columns to update (excluding product_id)
    upload_cols = [col for col in df.columns if col != "product_id"]

    # Align schemas by adding missing upload columns to df_curr if absent
    for col in upload_cols:
        if col not in df_curr.columns:
            df_curr[col] = None
    if "last_updated" not in df_curr.columns:
        df_curr["last_updated"] = None

    # Perform UPSERT via dictionary indexing to make logic clear and fast
    curr_dict = df_curr.set_index("product_id").to_dict(orient="index")
    
    inserted_count = 0
    updated_count = 0

    for _, row in df.iterrows():
        sku = row["product_id"]
        row_data = row.to_dict()
        
        if sku in curr_dict:
            # Overwrite only the upload-provided columns, preserve other columns
            for col in upload_cols:
                curr_dict[sku][col] = row_data[col]
            curr_dict[sku]["last_updated"] = timestamp_str
            updated_count += 1
        else:
            # Insert new SKU record
            new_record = {col: None for col in df_curr.columns if col != "product_id"}
            for col in upload_cols:
                new_record[col] = row_data[col]
            new_record["last_updated"] = timestamp_str
            curr_dict[sku] = new_record
            inserted_count += 1

    # Re-assemble DataFrame
    rows = []
    for sku, info in curr_dict.items():
        row_entry = {"product_id": sku}
        row_entry.update(info)
        rows.append(row_entry)

    df_result = pd.DataFrame(rows)
    
    os.makedirs(os.path.dirname(current_path), exist_ok=True)
    df_result.to_csv(current_path, index=False)
    logger.info(f"UPSERT complete for current inventory. Inserted: {inserted_count}, Updated: {updated_count}")
    
    return inserted_count, updated_count


def save_raw_backup(file_source, timestamp_str: str) -> str:
    """
    Saves the original uploaded file copy to backend/uploads/inventory/YYYY_MM_DD_HHMMSS.csv.
    """
    backup_dir = cfg.BACKUP_INVENTORY_DIR
    os.makedirs(backup_dir, exist_ok=True)

    # Format timestamp for file naming: "2026-06-14 16:52:14" -> "2026_06_14_165214"
    clean_ts = timestamp_str.replace("-", "_").replace(":", "").replace(" ", "_")
    backup_file = os.path.join(backup_dir, f"{clean_ts}.csv")

    if isinstance(file_source, pd.DataFrame):
        file_source.to_csv(backup_file, index=False)
    elif hasattr(file_source, 'read'):
        # Reset stream if possible
        if hasattr(file_source, 'seek'):
            try:
                file_source.seek(0)
            except Exception:
                pass
        
        content = file_source.read()
        mode = "wb" if isinstance(content, bytes) else "w"
        encoding = None if isinstance(content, bytes) else "utf-8"
        with open(backup_file, mode, encoding=encoding) as f:
            f.write(content)

        # Reset stream for subsequent pandas parsing
        if hasattr(file_source, 'seek'):
            try:
                file_source.seek(0)
            except Exception:
                pass
    else:
        # File path
        shutil.copyfile(str(file_source), backup_file)

    logger.info(f"Saved raw upload backup file to: {backup_file}")
    return backup_file


def process_inventory_upload(file_source) -> dict:
    """
    Orchestrates the inventory ingestion workflow:
      1. Generates snapshot timestamp.
      2. Saves original backup to recovery folder.
      3. Validates file schema, bounds, and internal SKU uniqueness.
      4. Appends snapshot records to the append-only inventory history.
      5. UPSERTs updates into the current operational state.
    """
    # Trigger legacy migration first if needed
    initialize_inventory_datasets()

    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Backup raw source
    save_raw_backup(file_source, timestamp_str)

    # 2. Validate
    df_validated = validate_inventory_file(file_source)

    # 3. Append to History
    append_inventory_history(df_validated, timestamp_str)

    # 4. UPSERT into Current state
    inserted, updated = update_current_inventory(df_validated, timestamp_str)

    return {
        "rows_processed": len(df_validated),
        "rows_inserted": inserted,
        "rows_updated": updated,
        "history_rows_added": len(df_validated)
    }
