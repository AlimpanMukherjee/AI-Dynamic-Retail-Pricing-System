import os
import pandas as pd
import backend.config as cfg
from backend.data_ingestion.validators import validate_sales_data, normalize_date_column

def append_sales_data(new_sales_df: pd.DataFrame):
    """
    Validates and appends new sales records to the sales.csv master dataset.
    Prevents duplicate appends by dropping exact matches.
    """
    validate_sales_data(new_sales_df)
    
    sales_path = cfg.CUSTOMER_SALES_PATH
    
    if os.path.exists(sales_path):
        df_existing = pd.read_csv(sales_path)
        df_existing = normalize_date_column(df_existing, "date")
        # Find which rows in new_sales_df are actually new
        common_cols = list(set(new_sales_df.columns).intersection(set(df_existing.columns)))
        if common_cols:
            df_new = new_sales_df.merge(df_existing[common_cols], on=common_cols, how='left', indicator=True)
            df_new = df_new[df_new['_merge'] == 'left_only'].drop(columns=['_merge'])
        else:
            df_new = new_sales_df.copy()

        df_combined = pd.concat([df_existing, new_sales_df], ignore_index=True)
        df_combined = df_combined.drop_duplicates().reset_index(drop=True)
        rows_added = len(df_combined) - len(df_existing)
    else:
        df_combined = new_sales_df.copy()
        df_new = new_sales_df.copy()
        rows_added = len(df_combined)

    os.makedirs(os.path.dirname(sales_path), exist_ok=True)
    df_combined.to_csv(sales_path, index=False)

    if rows_added > 0 and not df_new.empty:
        from backend.inventory.inventory_ingestion import deduct_inventory_from_sales
        deduct_inventory_from_sales(df_new)

    return rows_added
