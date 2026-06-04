import pandas as pd
import numpy as np
import os

# Lead time mapping based on warehouse location (fallback in case lead_time_days is missing)
LOCATION_LEAD_TIME = {
    "Mumbai": 5,
    "Delhi": 6,
    "Kolkata": 7,
    "Bengaluru": 8
}
DEFAULT_LEAD_TIME = 7

# -----------------------------
# STEP 1: LOAD DATA
# -----------------------------
def load_data(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Data file not found at: {path}")
    df = pd.read_csv(path)
    return df


# -----------------------------
# STEP 2: INVENTORY COMPUTATION
# -----------------------------
def compute_inventory_metrics(row):
    """
    Computes inventory metrics for a single product row.
    
    Inputs (mapped from new/old schemas):
      - current_stock: total inventory on hand
      - reserved_stock: stock committed to orders, unavailable for new sales (default: 0)
      - reorder_point: safety threshold for reordering
      - safety_stock: minimum buffer stock (default: reorder_point * 0.4)
      - sales_velocity_per_day / sales_velocity: average units sold per day
      - lead_time_days / lead_time: supplier fulfillment lead time in days
      - stock_age_days: age of stock in warehouse
      - warehouse_location: location of stock
    """
    # 1. Parse fields with backward compatibility
    current_stock = float(row.get("current_stock", 0))
    reserved_stock = float(row.get("reserved_stock", 0))
    reorder_point = float(row.get("reorder_point", 1))
    
    # Calculate net available stock
    net_stock = max(0.0, current_stock - reserved_stock)

    # Get sales velocity
    sales_velocity = float(row.get("sales_velocity_per_day", row.get("sales_velocity", 0)))
    
    # Get stock age
    stock_age = float(row.get("stock_age_days", 0))
    
    # Get safety stock
    safety_stock = float(row.get("safety_stock", reorder_point * 0.4))

    # 2. Get Lead Time
    if "lead_time_days" in row:
        lead_time = float(row["lead_time_days"])
    elif "lead_time" in row:
        lead_time = float(row["lead_time"])
    else:
        location = row.get("warehouse_location", "")
        lead_time = float(LOCATION_LEAD_TIME.get(location, DEFAULT_LEAD_TIME))

    # 3. Days of Supply (using net available stock, avoid divide-by-zero)
    days_of_supply = net_stock / (sales_velocity + 1e-5)

    # 4. Stockout Risk (0.0 to 1.0)
    # Risk increases if days of supply is less than lead time + safety days
    safety_days = safety_stock / (sales_velocity + 1e-5)
    
    if days_of_supply <= lead_time:
        stockout_risk = 1.0
    else:
        # Scale risk between lead_time and lead_time + safety_days
        divisor = safety_days if safety_days > 0 else 3.0
        stockout_risk = np.clip(1.0 - (days_of_supply - lead_time) / divisor, 0.0, 1.0)

    # Fallback to dataset-provided risk if present and we want comparison
    dataset_risk_score = row.get("stockout_risk_score", None)

    # 5. Inventory Pressure (-1.0 to 1.0)
    # -1.0 means critical understock (net stock < reorder point)
    #  1.0 means critical overstock (net stock > 3x reorder point)
    #  0.0 means perfect balance (net stock around reorder point)
    if net_stock == reorder_point:
        inventory_pressure = 0.0
    elif net_stock > reorder_point:
        # Overstock pressure: ratio of net stock to reorder point
        ratio = net_stock / (reorder_point + 1e-5)
        # Reaches 1.0 pressure at 3x reorder point
        inventory_pressure = np.clip((ratio - 1.0) / 2.0, 0.0, 1.0)
    else:
        # Understock pressure: ratio of net stock to reorder point
        ratio = net_stock / (reorder_point + 1e-5)
        # Reaches -1.0 pressure at 0 stock
        inventory_pressure = np.clip(ratio - 1.0, -1.0, 0.0)

    # 6. Urgency Score (0.0 to 1.0)
    # High urgency occurs if we are running out of stock (understock)
    # OR if we have massive overstock of old/aging inventory (perishable pressure)
    understock_urgency = stockout_risk
    overstock_urgency = np.clip(inventory_pressure * (stock_age / 90.0), 0.0, 1.0)
    urgency_score = float(max(understock_urgency, overstock_urgency))

    # 7. Recommended Price Adjustment Multiplier
    # - Low stock (negative pressure) -> Raise price (up to +10%)
    # - High stock (positive pressure) -> Lower price (down to -15%)
    max_discount = 0.15
    max_premium = 0.10
    
    if inventory_pressure >= 0:
        recommended_multiplier = 1.0 - (inventory_pressure * max_discount)
    else:
        recommended_multiplier = 1.0 - (inventory_pressure * max_premium)

    return {
        "net_stock": float(net_stock),
        "days_of_supply": float(round(days_of_supply, 1)),
        "lead_time_days": int(lead_time),
        "stockout_risk": float(round(stockout_risk, 3)),
        "dataset_risk_score": float(dataset_risk_score) if dataset_risk_score is not None else None,
        "inventory_pressure": float(round(inventory_pressure, 3)),
        "urgency_score": float(round(urgency_score, 3)),
        "recommended_multiplier": float(round(recommended_multiplier, 3))
    }


# -----------------------------
# STEP 3: MAIN PIPELINE
# -----------------------------
def run_pipeline(csv_path, target_product_id="SKU_1000", retailer_company=None, store_location=None):
    df = load_data(csv_path)

    # Filter for the target product
    df_product = df[df["product_id"] == target_product_id]
    if df_product.empty:
        raise ValueError(f"Product ID {target_product_id} not found in the dataset.")
        
    # Optional filtering by retailer and store location (since dataset has multiple stores per product)
    if retailer_company:
        df_filtered = df_product[df_product["retailer_company"].str.lower() == retailer_company.lower()]
        if not df_filtered.empty:
            df_product = df_filtered
            
    if store_location:
        df_filtered = df_product[df_product["store_location"].str.lower() == store_location.lower()]
        if not df_filtered.empty:
            df_product = df_filtered

    # Select the first matching row from the filtered set
    product_row = df_product.iloc[0].to_dict()
    metrics = compute_inventory_metrics(product_row)

    print(f"\n===== INVENTORY DYNAMICS FOR {target_product_id} =====")
    print("Product Name:          ", product_row.get("product_name"))
    print("Retailer:              ", product_row.get("retailer_company", "N/A"))
    print("Store Location:        ", product_row.get("store_location", "N/A"))
    print("Warehouse Location:    ", product_row.get("warehouse_location", "N/A"))
    print("---------------------------------------------")
    print("Current Stock:         ", product_row.get("current_stock"))
    print("Reserved Stock:        ", product_row.get("reserved_stock", 0))
    print("Net Available Stock:   ", metrics["net_stock"])
    print("Reorder Point:         ", product_row.get("reorder_point"))
    print("Safety Stock:          ", product_row.get("safety_stock", "N/A"))
    print("Sales Velocity (daily):", product_row.get("sales_velocity_per_day", product_row.get("sales_velocity", 0)))
    print("Stock Age (days):      ", product_row.get("stock_age_days"))
    print("---------------------------------------------")
    print("Days of Supply:        ", metrics["days_of_supply"])
    print("Lead Time (days):      ", metrics["lead_time_days"])
    print("Stockout Risk (Calc):  ", metrics["stockout_risk"])
    if metrics["dataset_risk_score"] is not None:
        print("Stockout Risk (Data):  ", metrics["dataset_risk_score"])
    print("Inventory Pressure:    ", metrics["inventory_pressure"])
    print("Urgency Score (0-1):   ", metrics["urgency_score"])
    print("Recommended Multiplier:", metrics["recommended_multiplier"])

    return {
        "product_id": target_product_id,
        "retailer_company": product_row.get("retailer_company"),
        "store_location": product_row.get("store_location"),
        "stockout_risk": metrics["stockout_risk"],
        "inventory_pressure": metrics["inventory_pressure"],
        "urgency_score": metrics["urgency_score"],
        "recommended_multiplier": metrics["recommended_multiplier"]
    }


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    # Run for SKU_1000 at Reliance Retail in Bengaluru (first row of dataset)
    result = run_pipeline("datasets/inventory.csv", "SKU_1000", "Reliance Retail", "Bengaluru")
    print("\nPipeline execution result:")
    print(result)
