import pandas as pd
from backend.inventory.inventory_ingestion import process_inventory_upload

def append_inventory_data(new_inventory_df: pd.DataFrame) -> int:
    """
    Validates and UPSERTs new inventory records to inventory_current.csv 
    and appends history snapshots to inventory_history.csv.
    
    Delegates to the new inventory ingestion pipeline and returns the count 
    of newly inserted SKUs to maintain backward compatibility with tests.
    """
    result = process_inventory_upload(new_inventory_df)
    return result["rows_inserted"]
