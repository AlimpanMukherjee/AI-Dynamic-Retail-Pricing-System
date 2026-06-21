import os
import pandas as pd
from backend.onboarding.validators import validate_inventory
from backend.config import CUSTOMER_INVENTORY_PATH

def upload_inventory(file_source, target_path=CUSTOMER_INVENTORY_PATH) -> str:
    """
    Reads, validates, and saves customer inventory CSV data.
    
    Parameters:
        file_source (str or file-like): Path to a CSV file or file-like object.
        target_path (str): File path where the validated CSV will be written.
        
    Returns:
        str: Success message indicating file path where data was written.
    """
    try:
        df = pd.read_csv(file_source)
    except Exception as e:
        raise ValueError(f"Failed to read CSV source: {str(e)}")
        
    # Run validators
    validate_inventory(df)
    
    # Save to target path
    import backend.config as cfg
    from backend.inventory.inventory_repository import save_current_inventory
    
    is_operational = False
    if target_path:
        norm_targ = os.path.abspath(target_path)
        norm_curr = os.path.abspath(cfg.CUSTOMER_INVENTORY_CURRENT_PATH)
        norm_inv_legacy = os.path.abspath(cfg.CUSTOMER_INVENTORY_PATH)
        if norm_targ in [norm_curr, norm_inv_legacy]:
            is_operational = True
            
    if is_operational:
        save_current_inventory(df)
    else:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        df.to_csv(target_path, index=False)
    
    return f"Inventory dataset successfully validated and saved to {target_path}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m backend.onboarding.upload_inventory <csv_path>")
        sys.exit(1)
        
    try:
        msg = upload_inventory(sys.argv[1])
        print(msg)
    except Exception as e:
        print(f"Validation/Upload Error: {str(e)}")
        sys.exit(1)
