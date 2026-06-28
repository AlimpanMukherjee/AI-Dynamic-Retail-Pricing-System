import os
import pandas as pd
import streamlit as st
import backend.config as cfg
from backend.data_ingestion.validators import validate_sales_data, normalize_date_column

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
        df_existing = normalize_date_column(df_existing, "date")
        
        # Find which rows in df are actually new based on the primary key (date, product_id)
        df_existing_keys = df_existing[['date', 'product_id']]
        df_new = df.merge(df_existing_keys, on=['date', 'product_id'], how='left', indicator=True)
        df_new = df_new[df_new['_merge'] == 'left_only'].drop(columns=['_merge'])

        # Append only new rows
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        rows_added = len(df_combined) - len(df_existing)
    else:
        df_combined = df.copy()
        df_new = df.copy()
        rows_added = len(df)

    os.makedirs(os.path.dirname(sales_path), exist_ok=True)
    df_combined.to_csv(sales_path, index=False)

    # Deduct stock for new sales records
    if rows_added > 0 and not df_new.empty:
        from backend.inventory.inventory_ingestion import deduct_inventory_from_sales
        deduct_inventory_from_sales(df_new)

    # Convert date representations to strings safely
    dates = pd.to_datetime(df["date"], format='mixed')
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


@st.cache_data
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
    
    dates = pd.to_datetime(df["date"], format='mixed')
    
    latest_ts = dates.max()
    has_time = (dates.dt.time != pd.Timestamp("2000-01-01 00:00:00").time()).any()
    if has_time:
        latest_str = latest_ts.strftime("%Y-%m-%d %H:%M:%S")
    else:
        latest_str = latest_ts.strftime("%Y-%m-%d")
        
    return {
        "total_records": len(df),
        "total_revenue": revenue,
        "latest_sale_date": latest_str,
        "first_sale_date": dates.min().strftime("%Y-%m-%d")
    }

@st.cache_data
def get_sales_history_df() -> pd.DataFrame:
    """
    Returns the raw sales history DataFrame (cached).
    """
    sales_path = cfg.CUSTOMER_SALES_PATH
    if not os.path.exists(sales_path):
        return pd.DataFrame()
    return pd.read_csv(sales_path)
