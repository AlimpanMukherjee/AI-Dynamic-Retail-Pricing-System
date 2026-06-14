import pandas as pd
import numpy as np

def _check_missing_fields(df, fields, dataset_name):
    for field in fields:
        if field not in df.columns:
            raise ValueError(f"Validation Error: Missing required column '{field}' in {dataset_name} dataset")
        if df[field].isnull().any() or (df[field] == "").any():
            # Find which SKU has the missing field for better readability
            sku_info = ""
            if "product_id" in df.columns:
                bad_rows = df[df[field].isnull() | (df[field] == "")]
                if not bad_rows.empty:
                    sku_info = f" (detected for SKU: {bad_rows['product_id'].iloc[0]})"
            raise ValueError(f"Validation Error: Missing values in column '{field}' in {dataset_name} dataset{sku_info}")

def _check_duplicates(df, dataset_name):
    if df.duplicated().any():
        raise ValueError(f"Validation Error: Duplicate rows detected in {dataset_name} dataset")

def _check_numeric_positive(df, column, dataset_name, strictly_positive=False):
    if column not in df.columns:
        return
    try:
        series = pd.to_numeric(df[column])
    except Exception:
        raise ValueError(f"Validation Error: Column '{column}' must be numeric in {dataset_name} dataset")
    
    if strictly_positive:
        if (series <= 0).any():
            sku_info = ""
            if "product_id" in df.columns:
                bad_rows = df[df[column] <= 0]
                sku_info = f" for SKU: {bad_rows['product_id'].iloc[0]}"
            raise ValueError(f"Validation Error: Price/selling_price must be > 0{sku_info}")
    else:
        if (series < 0).any():
            sku_info = ""
            if "product_id" in df.columns:
                bad_rows = df[df[column] < 0]
                sku_info = f" detected for {bad_rows['product_id'].iloc[0]}"
            raise ValueError(f"Validation Error: Negative {column}{sku_info}")

def validate_sales_data(df: pd.DataFrame):
    """
    Validates sales data uploads
    """
    _check_missing_fields(df, ["date", "product_id"], "sales")
    _check_duplicates(df, "sales")
    
    price_col = "selling_price" if "selling_price" in df.columns else "price"
    _check_numeric_positive(df, price_col, "sales", strictly_positive=True)
    _check_numeric_positive(df, "units_sold", "sales", strictly_positive=False)

def validate_inventory_data(df: pd.DataFrame):
    """
    Validates inventory data uploads
    """
    _check_missing_fields(df, ["product_id"], "inventory")
    _check_duplicates(df, "inventory")
    
    stock_col = "current_stock" if "current_stock" in df.columns else "stock"
    _check_numeric_positive(df, stock_col, "inventory", strictly_positive=False)
    _check_numeric_positive(df, "reserved_stock", "inventory", strictly_positive=False)

def validate_market_data(df: pd.DataFrame):
    """
    Validates market competitor data uploads
    """
    _check_missing_fields(df, ["product_id"], "market competitor")
    _check_duplicates(df, "market competitor")
    
    comp_price_col = "competitor_price" if "competitor_price" in df.columns else None
    if comp_price_col:
        _check_numeric_positive(df, comp_price_col, "market competitor", strictly_positive=True)

def validate_supplier_data(df: pd.DataFrame):
    """
    Validates supplier procurement data uploads
    """
    _check_missing_fields(df, ["product_id", "supplier_id"], "supplier procurement")
    _check_duplicates(df, "supplier procurement")
    
    lead_time_col = "lead_time_days" if "lead_time_days" in df.columns else "lead_time"
    _check_numeric_positive(df, lead_time_col, "supplier procurement", strictly_positive=False)
    
    rel_col = "supplier_reliability" if "supplier_reliability" in df.columns else "reliability"
    if rel_col in df.columns:
        try:
            series = pd.to_numeric(df[rel_col])
        except Exception:
            raise ValueError(f"Validation Error: Column '{rel_col}' must be numeric in supplier procurement dataset")
        if (series < 0).any() or (series > 1).any():
            sku_info = ""
            bad_rows = df[(df[rel_col] < 0) | (df[rel_col] > 1)]
            if not bad_rows.empty:
                sku_info = f" for SKU: {bad_rows['product_id'].iloc[0]}"
            raise ValueError(f"Validation Error: Reliability must be between 0 and 1{sku_info}")
