import pandas as pd
import numpy as np
import os
from backend.layer1.shared_utils import load_csv
import backend.config as cfg
                                                                                        
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
    safety_stock = float(row.get("safety_stock", reorder_point * cfg.SAFETY_STOCK_FACTOR))

    # 2. Get Lead Time
    if "lead_time_days" in row:
        lead_time = float(row["lead_time_days"])
    elif "lead_time" in row:
        lead_time = float(row["lead_time"])
    else:
        location = row.get("warehouse_location", "")
        lead_time = float(cfg.LOCATION_LEAD_TIMES.get(location, cfg.DEFAULT_LEAD_TIME_DAYS))

    # 3. Days of Supply (using net available stock, avoid divide-by-zero)
    days_of_supply = net_stock / (sales_velocity + 1e-5)

    # 4. Stockout Risk (0.0 to 1.0)
    # Risk increases if days of supply is less than lead time + safety days
    safety_days = safety_stock / (sales_velocity + 1e-5)
    
    if days_of_supply <= lead_time:
        stockout_risk = 1.0
    else:
        # Scale risk between lead_time and lead_time + safety_days
        divisor = safety_days if safety_days > 0 else cfg.DEFAULT_SAFETY_DAYS
        stockout_risk = np.clip(1.0 - (days_of_supply - lead_time) / divisor, 0.0, 1.0)

    # Fallback to dataset-provided risk if present and we want comparison
    dataset_risk_score = row.get("stockout_risk_score", None)

    # -------------------------------------------------------------------------
    # 5. INVENTORY PRESSURE (-1.0 to 1.0)
    # -------------------------------------------------------------------------
    # Derive DOS_KEYPOINTS safely using explicit ordered key arrays to guarantee correctness
    keys = ["critical", "understock", "shortage", "healthy", "overstock", "heavy_overstock", "extreme_overstock", "max_saturation"]
    dos_points = [0.0] + [float(cfg.INVENTORY_THRESHOLDS[k]) for k in keys]

    # Target pressure values corresponding to each keypoint.
    # Map Days of Supply to pressure zones:
    #   - < 3 days: critical shortage, maps to -1.0
    #   - 3-7 days: understock, maps between -1.0 and -0.7
    #   - 7-15 days: moderate shortage, maps between -0.7 and -0.45
    #   - 15-30 days: approaching balance, maps between -0.45 and 0.0
    #   - 30-60 days: healthy to mild overstock, maps between 0.0 and 0.3
    #   - 60-120 days: overstock, maps between 0.3 and 0.6
    #   - 120-180 days: heavy overstock, maps between 0.6 and 0.8
    #   - 180+ days: approaches extreme saturation, mapping up to 1.0 (at 360 days)
    pressure_keypoints = cfg.INVENTORY_PRESSURE_KEYPOINTS

    # Perform continuous piecewise linear interpolation to determine inventory pressure
    inventory_pressure = float(np.interp(days_of_supply, dos_points, pressure_keypoints))

    # -------------------------------------------------------------------------
    # 6. URGENCY SCORE (0.0 to 1.0)
    # -------------------------------------------------------------------------
    # Urgency consists of two distinct components:
    # A. Stockout Urgency: Driven directly by stockout risk (the likelihood of running out of stock).
    stockout_urgency = stockout_risk

    # B. Liquidation Urgency: Driven by positive inventory pressure (overstock) and stock age.
    # We apply a slower aging factor to prevent stock
    # that is only moderately aged (e.g. 60-90 days) from escalating into critical emergency.
    liquidation_urgency = max(0.0, inventory_pressure) * (stock_age / cfg.LIQUIDATION_AGE_FACTOR)
    liquidation_urgency = float(np.clip(liquidation_urgency, 0.0, 1.0))

    # The final urgency score is the maximum of the two urgency signals.
    urgency_score = float(max(stockout_urgency, liquidation_urgency))

    # -------------------------------------------------------------------------
    # 7. RECOMMENDED PRICE ADJUSTMENT MULTIPLIER
    # -------------------------------------------------------------------------
    # - Negative pressure (understock) -> Raise price (premium up to +10%)
    # - Positive pressure (overstock) -> Lower price (discount down to -15%)
    
    if inventory_pressure >= 0:
        recommended_multiplier = 1.0 - (inventory_pressure * cfg.MAX_INVENTORY_DISCOUNT)
    else:
        recommended_multiplier = 1.0 - (inventory_pressure * cfg.MAX_INVENTORY_PREMIUM)

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
def run_pipeline(csv_path=None, target_product_id="SKU_1000", retailer_company=None, store_location=None):
    # Dynamically resolve path defaults at call time to support routing configuration
    import backend.config as cfg
    from backend.inventory.inventory_repository import load_current_inventory
    import logging

    if csv_path is None:
        csv_path = cfg.CUSTOMER_INVENTORY_PATH

    is_operational = False
    if csv_path:
        norm_inv = os.path.abspath(csv_path)
        norm_curr = os.path.abspath(cfg.CUSTOMER_INVENTORY_CURRENT_PATH)
        norm_inv_legacy = os.path.abspath(cfg.CUSTOMER_INVENTORY_PATH)
        if norm_inv in [norm_curr, norm_inv_legacy]:
            is_operational = True

    logger = logging.getLogger("pricing_system.layer1.engine3")
    logger.info(f"Engine 3 Inventory Source: {csv_path} (Operational: {is_operational})")

    if is_operational:
        df = load_current_inventory()
    else:
        df = load_csv(csv_path)

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
        "recommended_multiplier": metrics["recommended_multiplier"],
        "days_of_supply": metrics["days_of_supply"],
        "net_stock": metrics["net_stock"]
    }


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    import backend.config as cfg
    # Run for SKU_1000 at Reliance Retail in Bengaluru (first row of dataset)
    result = run_pipeline(cfg.CUSTOMER_INVENTORY_PATH, "SKU_1000", "Reliance Retail", "Bengaluru")
    print("\nPipeline execution result:")
    print(result)
