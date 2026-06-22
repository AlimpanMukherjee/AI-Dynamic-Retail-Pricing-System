import os
import shutil
import pandas as pd
import backend.config as cfg
from backend.onboarding.validators import validate_products, validate_procurement, validate_inventory
from backend.inventory.inventory_ingestion import update_current_inventory, append_inventory_history
from datetime import datetime

def onboard_single_product(
    product_data: dict,
    procurement_data: dict,
    inventory_data: dict
) -> dict:
    """
    Onboards a single product by:
    1. Initializing target files from DEV templates if they do not exist.
    2. Validating product metadata, procurement costs, and inventory values.
    3. Appending the data to products, procurement, and inventory datasets.
    """
    # Define paths
    products_path = cfg.CUSTOMER_PRODUCTS_PATH
    procurement_path = cfg.CUSTOMER_PROCUREMENT_PATH
    
    # Initialize directories
    os.makedirs(os.path.dirname(products_path), exist_ok=True)
    os.makedirs(os.path.dirname(procurement_path), exist_ok=True)

    # Copy template if file does not exist
    if not os.path.exists(products_path) and os.path.exists(cfg.DEV_PRODUCTS_PATH):
        shutil.copyfile(cfg.DEV_PRODUCTS_PATH, products_path)
    if not os.path.exists(procurement_path) and os.path.exists(cfg.DEV_PROCUREMENT_PATH):
        shutil.copyfile(cfg.DEV_PROCUREMENT_PATH, procurement_path)

    # Read current data to check for duplicate product ID
    sku = str(product_data.get("product_id", "")).strip()
    if not sku:
        raise ValueError("Product ID cannot be empty.")

    if os.path.exists(products_path):
        df_existing_prod = pd.read_csv(products_path)
        if sku in df_existing_prod["product_id"].astype(str).str.strip().values:
            raise ValueError(f"Product ID '{sku}' already exists in the Product Master Catalog.")

    # Create single-row dataframes for validation
    df_prod = pd.DataFrame([product_data])
    df_proc = pd.DataFrame([procurement_data])
    df_inv = pd.DataFrame([inventory_data])

    # Run onboarding validators
    validate_products(df_prod)
    validate_procurement(df_proc)
    validate_inventory(df_inv)

    # Save Product data
    if os.path.exists(products_path):
        df_existing_prod = pd.read_csv(products_path)
        df_new_prod = pd.concat([df_existing_prod, df_prod], ignore_index=True)
    else:
        df_new_prod = df_prod
    df_new_prod.to_csv(products_path, index=False)

    # Save Procurement data
    if os.path.exists(procurement_path):
        df_existing_proc = pd.read_csv(procurement_path)
        df_new_proc = pd.concat([df_existing_proc, df_proc], ignore_index=True)
    else:
        df_new_proc = df_proc
    df_new_proc.to_csv(procurement_path, index=False)

    # Save Inventory data using internal UPSERT & history logging
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_current_inventory(df_inv, timestamp_str, mode="overwrite")
    append_inventory_history(df_inv, timestamp_str)

    return {
        "status": "success",
        "product_id": sku,
        "product_name": product_data.get("product_name")
    }
