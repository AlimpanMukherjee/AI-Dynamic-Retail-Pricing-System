import os
import pandas as pd
import backend.config as cfg
from backend.pipeline.pricing_pipeline import run_coordinated_pricing

def get_available_products() -> list:
    """
    Returns a sorted list of tuple dicts containing product_id and descriptive label names.
    """
    products_path = cfg.CUSTOMER_PRODUCTS_PATH
    if not os.path.exists(products_path):
        products_path = cfg.DEV_PRODUCTS_PATH
        
    if not os.path.exists(products_path):
        return []

    try:
        df = pd.read_csv(products_path)
        # Drop empty IDs
        df = df.dropna(subset=["product_id"])
        df["product_id"] = df["product_id"].astype(str).str.strip()
        
        # Resolve product name safely
        name_col = None
        if "product_name" in df.columns:
            name_col = "product_name"
        elif "name" in df.columns:
            name_col = "name"
            
        if name_col:
            df["name"] = df[name_col].astype(str).str.strip()
        else:
            df["name"] = "Product"
        
        # Build description list: "SKU_1056 - Maggi 70g Mini"
        products = []
        for _, row in df.iterrows():
            pid = row["product_id"]
            name = row["name"]
            products.append({
                "id": pid,
                "label": f"{pid} - {name}"
            })
        return sorted(products, key=lambda x: x["id"])
    except Exception as e:
        # Log exception to stdout to avoid swallowing it silently during troubleshooting
        print(f"Error in get_available_products: {str(e)}")
        return []


def get_available_retailers() -> list:
    """
    Returns the supported retailer company names in the dynamic pricing engines.
    """
    return ["Reliance Retail", "DMart", "Blinkit", "BigBasket"]


def get_resolved_retailer() -> str:
    """
    Dynamically loads the retailer company name from the current inventory dataset.
    Defaults to "Spencer's" if missing, empty, or unreadable.
    """
    inventory_path = cfg.CUSTOMER_INVENTORY_PATH
    if not os.path.exists(inventory_path):
        inventory_path = cfg.DEV_INVENTORY_PATH
        
    if not os.path.exists(inventory_path):
        return "Spencer's"
        
    try:
        df = pd.read_csv(inventory_path, nrows=5)
        if "retailer_company" in df.columns:
            retailers = df["retailer_company"].dropna().unique()
            if len(retailers) > 0:
                retailer = str(retailers[0]).strip()
                if retailer:
                    return retailer
        return "Spencer's"
    except Exception as e:
        print(f"Error reading retailer from inventory: {str(e)}")
        return "Spencer's"



def get_available_locations() -> list:
    """
    Returns the store locations supported by location-specific multipliers.
    """
    return ["Mumbai", "Delhi", "Bengaluru", "Kolkata"]


def run_pricing(
    product_id: str,
    retailer: str,
    location: str,
    event_active: bool = False,
    event_type: str = "Other",
    attendance: int = 0,
    distance_km: float = 2.0,
    duration_hours: float = 4.0
) -> dict:
    """
    Invokes the backend pricing coordination pipeline.
    Maps options to match engine lowercase configurations.
    
    Returns:
        dict: pricing results containing final_price, confidence, explanation,
              as well as price_journey and price_confidence explainability structures.
    """
    # Align BigBasket case with backend bigbasket check
    aligned_retailer = "Bigbasket" if retailer == "BigBasket" else retailer
    
    # Run coordinated pricing simulation
    result = run_coordinated_pricing(
        product_id=product_id,
        retailer_company=aligned_retailer,
        store_location=location,
        event_active=event_active,
        event_type=event_type,
        attendance=attendance,
        distance_km=distance_km,
        duration_hours=duration_hours
    )
    
    return result
