import os
import logging
import pandas as pd
import numpy as np
import backend.config as cfg

logger = logging.getLogger("pricing_system.monitoring.forecast_monitor")

def calculate_forecast_accuracy(sales_csv_path=None):
    """
    Compares Engine 2 expected_demand predictions with actual units_sold from sales records.
    Calculates MAE, RMSE, and MAPE metrics.
    """
    if sales_csv_path is None:
        sales_csv_path = cfg.CUSTOMER_SALES_PATH
        
    history_dir = os.path.join(cfg.PROJECT_ROOT, "backend", "history")
    history_file = os.path.join(history_dir, "prediction_history.csv")
    
    if not os.path.exists(history_file):
        logger.warning("No prediction history found. Cannot calculate accuracy metrics.")
        return None
        
    if not os.path.exists(sales_csv_path):
        logger.warning(f"Sales dataset {sales_csv_path} not found.")
        return None
        
    df_pred = pd.read_csv(history_file)
    df_sales = pd.read_csv(sales_csv_path)
    
    # Extract YYYY-MM-DD from prediction timestamp
    df_pred["date"] = pd.to_datetime(df_pred["timestamp"], format='mixed').dt.strftime("%Y-%m-%d")
    df_sales["date"] = pd.to_datetime(df_sales["date"], format='mixed').dt.strftime("%Y-%m-%d")
    
    # Align column names for merging
    df_pred_sub = df_pred[["date", "sku", "expected_demand"]].rename(columns={"sku": "product_id"})
    
    # Merge on date and product_id
    df_merged = pd.merge(df_sales, df_pred_sub, on=["date", "product_id"], how="inner")
    
    if df_merged.empty:
        logger.info("No prediction-to-actual matching dates found in current dataset.")
        return {
            "MAE": None,
            "RMSE": None,
            "MAPE": None,
            "matches_count": 0
        }
        
    predicted = df_merged["expected_demand"]
    actual = df_merged["units_sold"]
    
    # MAE
    mae = float(np.mean(np.abs(predicted - actual)))
    
    # RMSE
    rmse = float(np.sqrt(np.mean((predicted - actual) ** 2)))
    
    # MAPE
    non_zero_actuals = actual != 0
    if non_zero_actuals.any():
        mape = float(np.mean(np.abs(predicted[non_zero_actuals] - actual[non_zero_actuals]) / actual[non_zero_actuals]) * 100)
    else:
        mape = None
        
    report = {
        "MAE": mae,
        "RMSE": rmse,
        "MAPE": mape,
        "matches_count": len(df_merged)
    }
    
    logger.info(f"Forecast Accuracy Report: {report}")
    return report
