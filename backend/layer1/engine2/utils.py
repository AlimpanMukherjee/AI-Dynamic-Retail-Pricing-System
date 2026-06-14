import os
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger("pricing_system.layer1.engine2.utils")

def store_prediction_history(sku, recommended_price, expected_demand, elasticity, prediction_source):
    """
    Stores prediction metadata in backend/history/prediction_history.csv
    """
    history_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 
        "history"
    )
    os.makedirs(history_dir, exist_ok=True)
    history_file = os.path.join(history_dir, "prediction_history.csv")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_record = pd.DataFrame([{
        "timestamp": timestamp,
        "sku": sku,
        "recommended_price": recommended_price,
        "expected_demand": expected_demand,
        "elasticity": elasticity,
        "prediction_source": prediction_source
    }])
    
    if not os.path.exists(history_file):
        new_record.to_csv(history_file, index=False)
    else:
        new_record.to_csv(history_file, mode='a', header=False, index=False)
        
    logger.info(f"Recorded prediction history for {sku} under {history_file}")
