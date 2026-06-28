import pandas as pd
from backend.onboarding.validators import (
    validate_sales,
    validate_inventory,
    validate_procurement,
    validate_competitors,
    normalize_date_column as onboard_normalize_date,
    ValidationError
)

def validate_sales_data(df: pd.DataFrame) -> None:
    """
    Validates sales data uploads (compatibility shim).
    """
    for field in ["product_id", "date"]:
        if field not in df.columns:
            raise ValueError(f"Missing required column '{field}'")
    if df.duplicated().any():
        raise ValueError("Duplicate rows detected in sales data")
    
    price_col = "selling_price" if "selling_price" in df.columns else ("price" if "price" in df.columns else None)
    if price_col is not None:
        try:
            prices = pd.to_numeric(df[price_col])
            if (prices <= 0).any():
                raise ValueError("Price/selling_price must be > 0")
        except (ValueError, TypeError):
            raise ValueError("Price/selling_price must be > 0")
            
    if "units_sold" in df.columns:
        try:
            units = pd.to_numeric(df["units_sold"])
            if (units < 0).any():
                raise ValueError("Negative units_sold detected")
        except (ValueError, TypeError):
            raise ValueError("Negative units_sold detected")

    try:
        validate_sales(df, require_date=True)
    except ValidationError as e:
        raise ValueError(str(e))

def validate_inventory_data(df: pd.DataFrame) -> None:
    """
    Validates inventory data uploads (compatibility shim).
    """
    if "stock" in df.columns and "current_stock" not in df.columns:
        df = df.copy()
        df["current_stock"] = df["stock"]
    for field in ["product_id"]:
        if field not in df.columns:
            raise ValueError(f"Missing required column '{field}'")
    if df.duplicated().any():
        raise ValueError("Duplicate rows detected in inventory data")
    
    if "current_stock" in df.columns:
        try:
            stocks = pd.to_numeric(df["current_stock"])
            if (stocks < 0).any():
                raise ValueError("Negative stock values detected")
        except (ValueError, TypeError):
            raise ValueError("Negative stock values detected")
            
    if "reserved_stock" in df.columns:
        try:
            reserved = pd.to_numeric(df["reserved_stock"].dropna())
            if (reserved < 0).any():
                raise ValueError("Negative reserved_stock values detected")
        except (ValueError, TypeError):
            raise ValueError("Negative reserved_stock values detected")

    try:
        validate_inventory(df)
    except ValidationError as e:
        raise ValueError(str(e))

def validate_market_data(df: pd.DataFrame) -> None:
    """
    Validates market competitor data uploads (compatibility shim).
    """
    for field in ["product_id"]:
        if field not in df.columns:
            raise ValueError(f"Missing required column '{field}'")
    if df.duplicated().any():
        raise ValueError("Duplicate rows detected in competitor data")
        
    if "competitor_price" in df.columns:
        try:
            prices = pd.to_numeric(df["competitor_price"])
            if (prices <= 0).any():
                raise ValueError("Price/selling_price must be > 0")
        except (ValueError, TypeError):
            raise ValueError("Price/selling_price must be > 0")

    try:
        validate_competitors(df)
    except ValidationError as e:
        raise ValueError(str(e))

def validate_supplier_data(df: pd.DataFrame) -> None:
    """
    Validates supplier procurement data uploads (compatibility shim).
    """
    for field in ["product_id", "supplier_id"]:
        if field not in df.columns:
            raise ValueError(f"Missing required column '{field}'")
    if df.duplicated().any():
        raise ValueError("Duplicate rows detected in procurement data")
        
    try:
        validate_procurement(df)
    except ValidationError as e:
        msg = str(e)
        if "lead time" in msg:
            raise ValueError("Negative lead_time values detected")
        raise ValueError(msg)

def normalize_date_column(df: pd.DataFrame, column: str = "date") -> pd.DataFrame:
    """
    Safely converts a date column to YYYY-MM-DD string format (compatibility shim).
    """
    return onboard_normalize_date(df, column)
