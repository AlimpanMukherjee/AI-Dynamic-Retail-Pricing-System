import os
import pandas as pd
import backend.config as cfg
from backend.data_ingestion.validators import validate_supplier_data

def append_supplier_data(new_supplier_df: pd.DataFrame):
    """
    Validates and appends new supplier procurement records to the procurement.csv master dataset.
    Prevents duplicate appends by dropping exact matches.
    """
    validate_supplier_data(new_supplier_df)
    
    procurement_path = cfg.CUSTOMER_PROCUREMENT_PATH
    
    if os.path.exists(procurement_path):
        df_existing = pd.read_csv(procurement_path)
        df_combined = pd.concat([df_existing, new_supplier_df], ignore_index=True)
        df_combined = df_combined.drop_duplicates().reset_index(drop=True)
        rows_added = len(df_combined) - len(df_existing)
    else:
        df_combined = new_supplier_df.copy()
        rows_added = len(df_combined)
        
    os.makedirs(os.path.dirname(procurement_path), exist_ok=True)
    df_combined.to_csv(procurement_path, index=False)
    return rows_added
