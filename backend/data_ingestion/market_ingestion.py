import os
import pandas as pd
import backend.config as cfg
from backend.data_ingestion.validators import validate_market_data

def append_market_data(new_market_df: pd.DataFrame):
    """
    Validates and appends new market competitor records to the competitors.csv master dataset.
    Prevents duplicate appends by dropping exact matches.
    """
    validate_market_data(new_market_df)
    
    competitors_path = cfg.CUSTOMER_COMPETITOR_PATH
    
    if os.path.exists(competitors_path):
        df_existing = pd.read_csv(competitors_path)
        df_combined = pd.concat([df_existing, new_market_df], ignore_index=True)
        df_combined = df_combined.drop_duplicates().reset_index(drop=True)
        rows_added = len(df_combined) - len(df_existing)
    else:
        df_combined = new_market_df.copy()
        rows_added = len(df_combined)
        
    os.makedirs(os.path.dirname(competitors_path), exist_ok=True)
    df_combined.to_csv(competitors_path, index=False)
    return rows_added
