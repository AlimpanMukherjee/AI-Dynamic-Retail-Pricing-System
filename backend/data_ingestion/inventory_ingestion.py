import os
import pandas as pd
import backend.config as cfg
from backend.data_ingestion.validators import validate_inventory_data

def append_inventory_data(new_inventory_df: pd.DataFrame):
    """
    Validates and appends new inventory records to the inventory.csv master dataset.
    Prevents duplicate appends by dropping exact matches.
    """
    validate_inventory_data(new_inventory_df)
    
    inventory_path = cfg.CUSTOMER_INVENTORY_PATH
    
    if os.path.exists(inventory_path):
        df_existing = pd.read_csv(inventory_path)
        df_combined = pd.concat([df_existing, new_inventory_df], ignore_index=True)
        df_combined = df_combined.drop_duplicates().reset_index(drop=True)
        rows_added = len(df_combined) - len(df_existing)
    else:
        df_combined = new_inventory_df.copy()
        rows_added = len(df_combined)
        
    os.makedirs(os.path.dirname(inventory_path), exist_ok=True)
    df_combined.to_csv(inventory_path, index=False)
    return rows_added
