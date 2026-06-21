import os
import pandas as pd
import streamlit as st
import backend.config as cfg
from backend.inventory.inventory_ingestion import process_inventory_upload as backend_process_upload

def process_inventory_upload(file_source, mode: str = "overwrite") -> dict:
    """
    Validates, backups, and processes inventory upload. 
    Clears cache data upon completion to refresh dashboard metrics.
    """
    res = backend_process_upload(file_source, mode=mode)
    st.cache_data.clear()
    return res


def get_inventory_summary() -> dict:
    """
    Calculates stock health breakdowns, product lists, and aggregate metrics.
    Uses st.cache_data to speed up UI loading.
    """
    from backend.inventory.inventory_repository import load_current_inventory
    df = load_current_inventory()
    if df.empty:
        return {
            "total_products": 0,
            "total_stock": 0,
            "low_stock_count": 0,
            "critical_stock_count": 0,
            "health_counts": {"Healthy": 0, "Watchlist": 0, "Critical": 0},
            "latest_update": "N/A",
            "products_list": pd.DataFrame()
        }
    # Clean product IDs
    df["product_id"] = df["product_id"].astype(str).str.strip()

    # Calculate net stock and define status thresholds
    df["current_stock"] = pd.to_numeric(df["current_stock"], errors='coerce').fillna(0)
    df["reserved_stock"] = pd.to_numeric(df["reserved_stock"], errors='coerce').fillna(0)
    df["net_stock"] = (df["current_stock"] - df["reserved_stock"]).clip(lower=0)
    
    # Resolve reorder and safety thresholds
    df["reorder_point"] = pd.to_numeric(df.get("reorder_point"), errors='coerce').fillna(1.0)
    df["safety_stock"] = pd.to_numeric(df.get("safety_stock"), errors='coerce').fillna(df["reorder_point"] * 0.4)
    
    # Define stock status
    def determine_status(row):
        ns = row["net_stock"]
        rp = row["reorder_point"]
        ss = row["safety_stock"]
        if ns <= ss:
            return "Critical"
        elif ns <= rp:
            return "Watchlist"
        else:
            return "Healthy"

    df["stock_status"] = df.apply(determine_status, axis=1)

    # Merge base price from products database
    products_path = getattr(cfg, "CUSTOMER_PRODUCTS_PATH", None)
    if products_path and os.path.exists(products_path):
        try:
            df_prod = pd.read_csv(products_path)
            df_prod["product_id"] = df_prod["product_id"].astype(str).str.strip()
            df_prod = df_prod[["product_id", "base_market_price"]].drop_duplicates(subset=["product_id"])
            if "base_market_price" in df.columns:
                df = df.drop(columns=["base_market_price"])
            df = pd.merge(df, df_prod, on="product_id", how="left")
        except Exception as e:
            print(f"Error merging base_market_price in get_inventory_summary: {e}")

    # Merge procurement cost details (picking the primary supplier with highest reliability)
    procurement_path = getattr(cfg, "CUSTOMER_PROCUREMENT_PATH", None)
    if procurement_path and os.path.exists(procurement_path):
        try:
            df_proc = pd.read_csv(procurement_path)
            df_proc["product_id"] = df_proc["product_id"].astype(str).str.strip()
            df_proc = df_proc.sort_values(by="supplier_reliability", ascending=False)
            df_proc_unique = df_proc.drop_duplicates(subset=["product_id"])
            
            cost_cols = ["product_id", "supplier_price", "freight_cost", "warehouse_cost", "gst_tax"]
            existing_cost_cols = [c for c in cost_cols if c in df_proc_unique.columns]
            df_proc_costs = df_proc_unique[existing_cost_cols].copy()
            
            required_landed_cols = ["supplier_price", "freight_cost", "warehouse_cost", "gst_tax"]
            if all(c in df_proc_costs.columns for c in required_landed_cols):
                df_proc_costs["true_landed_cost"] = (
                    df_proc_costs["supplier_price"] +
                    df_proc_costs["freight_cost"] +
                    df_proc_costs["warehouse_cost"] +
                    df_proc_costs["gst_tax"]
                )
            
            to_drop = [c for c in df_proc_costs.columns if c != "product_id" and c in df.columns]
            if to_drop:
                df = df.drop(columns=to_drop)
            df = pd.merge(df, df_proc_costs, on="product_id", how="left")
        except Exception as e:
            print(f"Error merging procurement costs in get_inventory_summary: {e}")

    # Read latest upload time
    latest_update = "N/A"
    if "last_updated" in df.columns:
        dates = pd.to_datetime(df["last_updated"], errors='coerce').dropna()
        if not dates.empty:
            latest_update = dates.max().strftime("%Y-%m-%d %H:%M:%S")

    # Group counts
    status_counts = df["stock_status"].value_counts().to_dict()
    health_counts = {
        "Healthy": status_counts.get("Healthy", 0),
        "Watchlist": status_counts.get("Watchlist", 0),
        "Critical": status_counts.get("Critical", 0)
    }

    return {
        "total_products": len(df["product_id"].unique()),
        "total_stock": int(df["current_stock"].sum()),
        "low_stock_count": health_counts["Watchlist"],
        "critical_stock_count": health_counts["Critical"],
        "health_counts": health_counts,
        "latest_update": latest_update,
        "products_list": df
    }


def get_product_inventory(product_id: str) -> dict:
    """
    Looks up stock details for a single target product.
    """
    summary = get_inventory_summary()
    df = summary["products_list"]
    if df.empty:
        return {}

    p_id = str(product_id).strip()
    match = df[df["product_id"] == p_id]
    if match.empty:
        return {}

    row = match.iloc[0].to_dict()
    
    # Calculate Days of Supply for preview
    sales_vel = float(row.get("sales_velocity_per_day", row.get("sales_velocity", 0.0)))
    net_st = float(row.get("net_stock", 0.0))
    days_of_supply = net_st / (sales_vel + 1e-5)

    return {
        "product_id": row["product_id"],
        "product_name": row.get("product_name", "N/A"),
        "category": row.get("category", "N/A"),
        "brand": row.get("brand", "N/A"),
        "current_stock": int(row["current_stock"]),
        "reserved_stock": int(row["reserved_stock"]),
        "net_stock": int(row["net_stock"]),
        "stock_status": row["stock_status"],
        "warehouse": row.get("warehouse", row.get("warehouse_location", "N/A")),
        "days_of_supply": round(days_of_supply, 1)
    }
