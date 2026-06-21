import os
import shutil
import logging
import pandas as pd
from datetime import datetime
from typing import Union
from io import StringIO, BytesIO

import backend.config as cfg
from backend.inventory.inventory_repository import (
    initialize_inventory_datasets,
    load_current_inventory,
    save_current_inventory
)

logger = logging.getLogger("pricing_system.inventory.inventory_ingestion")


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
            name = getattr(file_source, 'name', '').lower()
            if name.endswith('.xlsx') or name.endswith('.xls'):
                df = pd.read_excel(file_source, engine='openpyxl')
            else:
                df = pd.read_csv(file_source)
        else:
            path = str(file_source)
            if path.endswith('.xlsx') or path.endswith('.xls'):
                df = pd.read_excel(path, engine='openpyxl')
            else:
                df = pd.read_csv(path)
    except Exception as e:
        logger.error(f"Failed to parse upload source: {str(e)}")
        raise ValueError(f"Failed to read upload source: {str(e)}")

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


def update_current_inventory(df: pd.DataFrame, timestamp_str: str, mode: str = "overwrite") -> tuple:
    """
    Performs UPSERT, Restock, or Initialize logic into inventory_current.csv.
    Explicit Overwrite Rule:
      - Columns present in upload overwrite old values (unless restock mode is selected).
      - Columns absent in upload are preserved for existing SKUs.
    Sets 'last_updated' to the upload timestamp.
    Returns: (inserted_count, updated_count)
    """
    # Initialize datasets if legacy file needs migration first
    initialize_inventory_datasets()

    if mode == "initialize":
        # Raise error if current operational stock exists
        df_existing = load_current_inventory()
        if not df_existing.empty:
            raise ValueError("Operational inventory has already been initialized. Use 'restock' or 'overwrite' mode.")

    df_curr = load_current_inventory()
    if df_curr.empty:
        df_curr = pd.DataFrame(columns=["product_id"])
    else:
        df_curr["product_id"] = df_curr["product_id"].astype(str).str.strip()

    # Extract target upload columns to update (excluding product_id)
    upload_cols = [col for col in df.columns if col != "product_id"]

    # Align schemas by adding missing upload columns to df_curr if absent
    for col in upload_cols:
        if col not in df_curr.columns:
            df_curr[col] = None
    if "last_updated" not in df_curr.columns:
        df_curr["last_updated"] = None

    # Perform UPSERT/Restock/Initialize via dictionary indexing
    curr_dict = df_curr.set_index("product_id").to_dict(orient="index")
    
    inserted_count = 0
    updated_count = 0

    for _, row in df.iterrows():
        sku = row["product_id"]
        row_data = row.to_dict()
        
        if sku in curr_dict:
            if mode == "restock":
                # Adds stock: new_stock = current_stock + incoming_stock
                current_qty = pd.to_numeric(curr_dict[sku].get("current_stock"), errors='coerce')
                current_qty = current_qty if not pd.isna(current_qty) else 0
                incoming_qty = pd.to_numeric(row_data.get("current_stock"), errors='coerce')
                incoming_qty = incoming_qty if not pd.isna(incoming_qty) else 0
                
                curr_dict[sku]["current_stock"] = current_qty + incoming_qty
                
                # For other upload-provided columns, overwrite
                for col in upload_cols:
                    if col != "current_stock":
                        curr_dict[sku][col] = row_data[col]
            else:
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
    save_current_inventory(df_result)
    logger.info(f"UPSERT/Restock complete for current inventory. Mode: {mode}, Inserted: {inserted_count}, Updated: {updated_count}")
    
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


def process_inventory_upload(file_source, mode: str = "overwrite") -> dict:
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
    inserted, updated = update_current_inventory(df_validated, timestamp_str, mode=mode)

    return {
        "rows_processed": len(df_validated),
        "rows_inserted": inserted,
        "rows_updated": updated,
        "history_rows_added": len(df_validated)
    }


def deduct_inventory_from_sales(sales_df: pd.DataFrame):
    """
    Deducts the units sold in sales_df from the current stock in inventory_current.csv.
    Clamps the remaining stock to 0.
    Updates last_updated timestamp for modified products.
    """
    try:
        # Load inventory via repository
        df_inv = load_current_inventory()
        if df_inv.empty:
            logger.warning("Inventory current file empty or not found. Skipping deduction.")
            return

        # Aggregate units sold per product in the sales dataframe
        sales_df = sales_df.copy()
        sales_df["product_id"] = sales_df["product_id"].astype(str).str.strip()
        sales_agg = sales_df.groupby("product_id")["units_sold"].sum().to_dict()

        # Deduct stock for matching products
        updated = False
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for prod_id, qty in sales_agg.items():
            prod_id_str = str(prod_id).strip()
            mask = df_inv["product_id"] == prod_id_str
            if mask.any():
                # Get current stock
                current_stock = pd.to_numeric(df_inv.loc[mask, "current_stock"], errors='coerce').fillna(0).values[0]
                new_stock = max(0.0, float(current_stock) - float(qty))
                # Preserve integer representation if originally float/int integer-valued
                if float(current_stock).is_integer():
                    new_stock = int(new_stock)
                df_inv.loc[mask, "current_stock"] = new_stock
                df_inv.loc[mask, "last_updated"] = timestamp_str
                updated = True

        if updated:
            save_current_inventory(df_inv)
            logger.info("Successfully updated current stock levels in inventory based on sales.")
    except Exception as e:
        logger.error(f"Error deducting inventory from sales: {str(e)}")

