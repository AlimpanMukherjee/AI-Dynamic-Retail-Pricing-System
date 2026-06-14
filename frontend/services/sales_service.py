import os
import pandas as pd
import streamlit as st
import backend.config as cfg
from backend.data_ingestion.validators import validate_sales_data

def validate_sales_file(df: pd.DataFrame):
    """
    Validates sales dataframe columns and boundaries using the backend validator rules.
    """
    # Support 'price' columns compatibility rename for onboarding
    if "price" in df.columns and "selling_price" not in df.columns:
        df["selling_price"] = df["price"]
        
    validate_sales_data(df)


def append_sales_upload(file_source) -> dict:
    """
    Reads, validates, and appends daily sales uploads (CSV or Excel) to sales_history.csv.
    Prevents duplicate entries by dropping exact matches.
    """
    try:
        # Resolve source type
        if isinstance(file_source, pd.DataFrame):
            df = file_source.copy()
        elif hasattr(file_source, 'read'):
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
        raise ValueError(f"Failed to read file source: {str(e)}")

    # Run validation
    validate_sales_file(df)

    sales_path = cfg.CUSTOMER_SALES_PATH

    # Append and drop duplicates
    if os.path.exists(sales_path):
        df_existing = pd.read_csv(sales_path)
        df_combined = pd.concat([df_existing, df], ignore_index=True)
        df_combined = df_combined.drop_duplicates().reset_index(drop=True)
        rows_added = len(df_combined) - len(df_existing)
    else:
        df_combined = df.copy()
        rows_added = len(df)

    os.makedirs(os.path.dirname(sales_path), exist_ok=True)
    df_combined.to_csv(sales_path, index=False)

    # Convert date representations to strings
    dates = pd.to_datetime(df["date"])
    start_date = dates.min().strftime("%Y-%m-%d")
    end_date = dates.max().strftime("%Y-%m-%d")

    # Clear cached reads since the data has changed
    st.cache_data.clear()

    return {
        "rows_processed": len(df),
        "rows_inserted": rows_added,
        "products_affected": df["product_id"].nunique(),
        "start_date": start_date,
        "end_date": end_date
    }


def get_sales_summary() -> dict:
    """
    Returns high-level statistics of the sales_history.csv dataset.
    Uses st.cache_data for speed.
    """
    sales_path = cfg.CUSTOMER_SALES_PATH
    if not os.path.exists(sales_path):
        return {
            "total_records": 0,
            "total_revenue": 0.0,
            "latest_sale_date": "N/A",
            "first_sale_date": "N/A"
        }

    df = pd.read_csv(sales_path)
    if df.empty:
        return {
            "total_records": 0,
            "total_revenue": 0.0,
            "latest_sale_date": "N/A",
            "first_sale_date": "N/A"
        }

    # Support 'price' columns compatibility rename
    price_col = "selling_price" if "selling_price" in df.columns else "price"
    revenue = float((df[price_col] * df["units_sold"]).sum())
    
    dates = pd.to_datetime(df["date"])
    
    return {
        "total_records": len(df),
        "total_revenue": revenue,
        "latest_sale_date": dates.max().strftime("%Y-%m-%d"),
        "first_sale_date": dates.min().strftime("%Y-%m-%d")
    }
