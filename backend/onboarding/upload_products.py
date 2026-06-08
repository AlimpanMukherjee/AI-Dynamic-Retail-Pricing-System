import os
import pandas as pd
from backend.onboarding.validators import validate_products
from backend.config import CUSTOMER_PRODUCTS_PATH

def upload_products(file_source, target_path=CUSTOMER_PRODUCTS_PATH) -> str:
    """
    Reads, validates, and saves customer products CSV data.
    
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
    validate_products(df)
    
    # Save to target path
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    df.to_csv(target_path, index=False)
    
    return f"Products dataset successfully validated and saved to {target_path}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m backend.onboarding.upload_products <csv_path>")
        sys.exit(1)
        
    try:
        msg = upload_products(sys.argv[1])
        print(msg)
    except Exception as e:
        print(f"Validation/Upload Error: {str(e)}")
        sys.exit(1)
