import os
import pandas as pd
import backend.config as cfg

def get_sales_record_count() -> int:
    """
    Returns the total number of sales records in the customer's sales history.
    """
    sales_path = cfg.CUSTOMER_SALES_PATH
    if not os.path.exists(sales_path):
        return 0
    try:
        df = pd.read_csv(sales_path)
        return len(df)
    except Exception:
        return 0

def calculate_engine2_confidence(sales_count: int) -> float:
    """
    Calculates the confidence score placed on Engine 2 predictions
    based on the available sales history count.
    """
    low = getattr(cfg, "LOW_DATA_THRESHOLD", 500)
    med = getattr(cfg, "MEDIUM_DATA_THRESHOLD", 1000)
    high = getattr(cfg, "HIGH_DATA_THRESHOLD", 5000)
    min_conf = getattr(cfg, "MIN_ENGINE2_CONFIDENCE", 0.10)

    if sales_count >= high:
        return 1.0
    elif sales_count >= 2500:
        return 0.8
    elif sales_count >= med:
        return 0.6
    elif sales_count >= low:
        return 0.4
    elif sales_count >= 100:
        return 0.2
    else:
        return min_conf

def get_customer_profile() -> dict:
    """
    Constructs the customer data availability profile.
    """
    sales_count = get_sales_record_count()
    confidence = calculate_engine2_confidence(sales_count)
    low_thresh = getattr(cfg, "LOW_DATA_THRESHOLD", 500)
    
    return {
        "sales_records": sales_count,
        "engine2_confidence": confidence,
        "training_eligible": bool(sales_count >= low_thresh)
    }
