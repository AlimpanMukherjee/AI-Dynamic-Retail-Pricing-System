import pandas as pd
import numpy as np
from typing import List

class ValidationError(ValueError):
    """Exception raised for errors in onboarding data validation."""
    pass

def validate_products(df: pd.DataFrame) -> None:
    """
    Validates products dataframe structure and content.
    
    Required columns:
      - product_id
      - product_name
      - category
      - subcategory
      
    Checks:
      - Missing required columns
      - Null values in required columns
      - Duplicate product IDs
    """
    required_cols = ["product_id", "product_name", "category", "subcategory"]
    
    # Check for missing columns
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValidationError(f"Missing required columns in products data: {missing_cols}")
        
    # Check for null values in required columns
    for col in required_cols:
        if df[col].isnull().any():
            null_rows = df[df[col].isnull()].index.tolist()
            raise ValidationError(f"Null values detected in products column '{col}' at row index: {null_rows}")
            
    # Check for duplicate product IDs
    if df["product_id"].duplicated().any():
        duplicated_ids = df[df["product_id"].duplicated()]["product_id"].unique().tolist()
        raise ValidationError(f"Duplicate product IDs detected: {duplicated_ids}")


def validate_inventory(df: pd.DataFrame) -> None:
    """
    Validates inventory dataframe structure and content.
    
    Required columns:
      - product_id
      - current_stock
      
    Checks:
      - Missing required columns
      - Null or empty values in product_id
      - Null or invalid values in current_stock
      - Negative stock values
    """
    required_cols = ["product_id", "current_stock"]
    
    # Check for missing columns
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValidationError(f"Missing required columns in inventory data: {missing_cols}")
        
    # Check for missing/null product_id
    if df["product_id"].isnull().any():
        null_rows = df[df["product_id"].isnull()].index.tolist()
        raise ValidationError(f"Null product_id detected in inventory data at row index: {null_rows}")
        
    # Check for null values in current_stock
    if df["current_stock"].isnull().any():
        null_rows = df[df["current_stock"].isnull()].index.tolist()
        raise ValidationError(f"Null current_stock detected in inventory data at row index: {null_rows}")
        
    # Check for negative stock values
    try:
        stocks = pd.to_numeric(df["current_stock"])
    except (ValueError, TypeError) as e:
        raise ValidationError(f"Invalid non-numeric values in current_stock: {str(e)}")
        
    if (stocks < 0).any():
        negative_rows = df[stocks < 0].index.tolist()
        raise ValidationError(f"Negative stock values detected in inventory data at row index: {negative_rows}")


def validate_procurement(df: pd.DataFrame) -> None:
    """
    Validates procurement dataframe structure and content.
    
    Required columns:
      - product_id
      - supplier_id
      
    Checks:
      - Missing required columns
      - Null values in product_id or supplier_id
      - Invalid/negative values in cost columns (supplier_price, freight_cost, warehouse_cost, gst_tax)
    """
    required_cols = ["product_id", "supplier_id"]
    
    # Check for missing columns
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValidationError(f"Missing required columns in procurement data: {missing_cols}")
        
    # Check for null values in required columns
    for col in required_cols:
        if df[col].isnull().any():
            null_rows = df[df[col].isnull()].index.tolist()
            raise ValidationError(f"Null values detected in procurement column '{col}' at row index: {null_rows}")
            
    # Check invalid costs if they are present in the upload
    cost_cols = ["supplier_price", "freight_cost", "warehouse_cost", "gst_tax"]
    for col in cost_cols:
        if col in df.columns:
            non_null_vals = df[col].dropna()
            try:
                numeric_vals = pd.to_numeric(non_null_vals)
            except (ValueError, TypeError) as e:
                raise ValidationError(f"Invalid non-numeric values in procurement column '{col}': {str(e)}")
                
            if (numeric_vals < 0).any():
                negative_rows = df[df[col] < 0].index.tolist()
                raise ValidationError(f"Negative cost values detected in procurement column '{col}' at row index: {negative_rows}")


def validate_sales(df: pd.DataFrame) -> None:
    """
    Validates sales dataframe structure and content.
    
    Required columns:
      - product_id
      - units_sold
      
    Checks:
      - Missing required columns
      - Null or empty product_id
      - Null or invalid units_sold
      - Negative sales (units_sold < 0)
    """
    required_cols = ["product_id", "units_sold"]
    
    # Check for missing columns
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValidationError(f"Missing required columns in sales data: {missing_cols}")
        
    # Check for missing product_id
    if df["product_id"].isnull().any():
        null_rows = df[df["product_id"].isnull()].index.tolist()
        raise ValidationError(f"Null product_id detected in sales data at row index: {null_rows}")
        
    # Check for null units_sold
    if df["units_sold"].isnull().any():
        null_rows = df[df["units_sold"].isnull()].index.tolist()
        raise ValidationError(f"Null units_sold detected in sales data at row index: {null_rows}")
        
    # Check for negative sales
    try:
        sales = pd.to_numeric(df["units_sold"])
    except (ValueError, TypeError) as e:
        raise ValidationError(f"Invalid non-numeric values in units_sold: {str(e)}")
        
    if (sales < 0).any():
        negative_rows = df[sales < 0].index.tolist()
        raise ValidationError(f"Negative sales values detected in sales data at row index: {negative_rows}")


def validate_competitors(df: pd.DataFrame) -> None:
    """
    Validates competitor intelligence dataframe structure and content.
    
    Required columns:
      - product_id
      - competitor_price
      
    Checks:
      - Missing required columns
      - Null values in required columns
      - Negative competitor prices
    """
    required_cols = ["product_id", "competitor_price"]
    
    # Check for missing columns
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValidationError(f"Missing required columns in competitor data: {missing_cols}")
        
    # Check for null values in required columns
    for col in required_cols:
        if df[col].isnull().any():
            null_rows = df[df[col].isnull()].index.tolist()
            raise ValidationError(f"Null values detected in competitor column '{col}' at row index: {null_rows}")
            
    # Check for negative competitor prices
    try:
        prices = pd.to_numeric(df["competitor_price"])
    except (ValueError, TypeError) as e:
        raise ValidationError(f"Invalid non-numeric values in competitor_price: {str(e)}")
        
    if (prices < 0).any():
        negative_rows = df[prices < 0].index.tolist()
        raise ValidationError(f"Negative prices detected in competitor column 'competitor_price' at row index: {negative_rows}")
