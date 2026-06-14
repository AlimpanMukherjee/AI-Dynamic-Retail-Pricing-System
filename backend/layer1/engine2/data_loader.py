import os
import pandas as pd
import numpy as np

def get_mode_or_first(series):
    if series.empty:
        return np.nan
    try:
        modes = series.mode()
        if not modes.empty:
            return modes.iloc[0]
    except Exception:
        pass
    if len(series) > 0:
        return series.iloc[0]
    return np.nan

def load_and_join_data(sales_path, products_path, inventory_path):
    """
    Loads sales, products, and inventory datasets, and left-joins them on product_id.
    Prevents row multiplication by aggregating inventory metadata at SKU level.
    """
    if not os.path.exists(sales_path):
        raise FileNotFoundError(f"Sales file not found at: {sales_path}")
    if not os.path.exists(products_path):
        raise FileNotFoundError(f"Products file not found at: {products_path}")
    if not os.path.exists(inventory_path):
        raise FileNotFoundError(f"Inventory file not found at: {inventory_path}")

    df_sales = pd.read_csv(sales_path)
    df_products = pd.read_csv(products_path)
    df_inventory = pd.read_csv(inventory_path)

    # Subset master catalog & store information to join cleanly
    df_prod_sub = df_products[['product_id', 'category', 'brand']].drop_duplicates()

    # Merge sales with products
    df_merged = pd.merge(df_sales, df_prod_sub, on="product_id", how="left", suffixes=("_sales", ""))
    
    # Redesign merge strategy to prevent row duplication
    # Aggregate inventory metadata using frequency-based mode (falling back to first)
    df_inv_agg = df_inventory.groupby("product_id").agg({
        "retailer_company": [
            ("retailer_count", "nunique"),
            ("retailer_company", lambda x: get_mode_or_first(x))
        ],
        "store_location": [
            ("location_count", "nunique"),
            ("store_location", lambda x: get_mode_or_first(x))
        ]
    })
    df_inv_agg.columns = [col[1] for col in df_inv_agg.columns]
    df_inv_agg = df_inv_agg.reset_index()

    # Merge sales with aggregated inventory metadata
    df_merged = pd.merge(df_merged, df_inv_agg, on="product_id", how="left")

    return df_merged
