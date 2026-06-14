import os
import logging
import pandas as pd
from datetime import datetime

import backend.config as cfg
from backend.layer1.engine2.model_store import load_metadata
from backend.layer1.engine2.engine2 import run_pipeline

logger = logging.getLogger("pricing_system.retraining.retrain_engine2")

MODEL_DIR = os.path.join(cfg.PROJECT_ROOT, "backend", "models")
METADATA_PATH = os.path.join(MODEL_DIR, "engine2_metadata.json")

def check_and_trigger_retraining(force=False):
    """
    Checks retraining conditions (Option A: Weekly, Option B: 500 new rows).
    If conditions met or force=True, retrains Engine 2 model.
    Returns:
        bool: True if model retrained, False otherwise.
    """
    sales_path = cfg.CUSTOMER_SALES_PATH
    if not os.path.exists(sales_path):
        logger.warning(f"Sales path {sales_path} does not exist. Cannot evaluate retraining.")
        return False
        
    df_sales = pd.read_csv(sales_path)
    current_rows = len(df_sales)
    
    metadata = load_metadata(METADATA_PATH)
    
    if metadata is None:
        logger.info("Metadata missing. Triggering training.")
        run_pipeline(force_retrain=True)
        return True
        
    # Condition A: Weekly retraining (>= 7 days elapsed)
    trained_at_str = metadata.get("trained_at")
    weekly_trigger = False
    if trained_at_str:
        try:
            trained_at_dt = datetime.strptime(trained_at_str, "%Y-%m-%d %H:%M:%S")
            elapsed_days = (datetime.now() - trained_at_dt).days
            if elapsed_days >= 7:
                weekly_trigger = True
                logger.info(f"Weekly retraining condition met: {elapsed_days} days elapsed since last training.")
        except Exception as e:
            logger.warning(f"Failed to parse trained_at timestamp: {trained_at_str}. Error: {str(e)}")
            
    # Condition B: Threshold retraining (>= 500 new rows since last training)
    last_training_rows = metadata.get("training_rows", 0)
    new_rows = current_rows - last_training_rows
    threshold_trigger = new_rows >= 500
    
    if threshold_trigger:
        logger.info(f"Threshold retraining condition met: {new_rows} new sales rows detected (threshold: 500).")
        
    if force or weekly_trigger or threshold_trigger:
        logger.info("Triggering retraining pipeline...")
        run_pipeline(force_retrain=True)
        return True
        
    logger.info("Retraining conditions not met. Skipping retraining.")
    return False
