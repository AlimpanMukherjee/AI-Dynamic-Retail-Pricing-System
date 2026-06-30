import pandas as pd
import numpy as np
import os

# Target margins based on product category
CATEGORY_MARGINS = {
    "staples": 0.05,
    "packaged foods": 0.10,
    "dairy": 0.12,
    "beverages": 0.10,
    "snacks": 0.15,
    "personal care": 0.20
}
DEFAULT_MARGIN = 0.10

# -----------------------------
# STEP 1: LOAD DATA & JOIN
# -----------------------------
def load_and_join_data(products_path, procurement_path):
    """
    Loads normalized datasets and performs a relational join on product_id.
    """
    if not os.path.exists(products_path):
        raise FileNotFoundError(f"Products file not found at: {products_path}")
    if not os.path.exists(procurement_path):
        raise FileNotFoundError(f"Procurement file not found at: {procurement_path}")

    df_products = pd.read_csv(products_path)
    df_procurement = pd.read_csv(procurement_path)

    # Perform relational join
    df_joined = pd.merge(df_procurement, df_products, on="product_id", how="left", suffixes=("", "_master"))
    return df_joined


# -----------------------------
# STEP 2: PROCUREMENT COMPUTATION
# -----------------------------
def compute_procurement_metrics(df_product_suppliers, target_supplier_id=None, currency_fluctuation_factor=1.0):
    """
    Computes procurement metrics for a product.
    
    If multiple suppliers exist:
      - Uses target_supplier_id if specified.
      - Otherwise, selects the primary supplier (highest reliability).
      - Computes cost volatility across all available suppliers.
    """
    if df_product_suppliers.empty:
        raise ValueError("Supplier procurement data is empty for the target product.")

    # 1. Compute Cost Volatility across all suppliers
    # Coeff of Variation = standard deviation / mean
    supplier_prices = df_product_suppliers["supplier_price"].values
    if len(supplier_prices) > 1:
        price_std = np.std(supplier_prices)
        price_mean = np.mean(supplier_prices)
        cost_volatility = price_std / (price_mean + 1e-5)
    else:
        cost_volatility = 0.0

    # 2. Select specific supplier or primary supplier
    if target_supplier_id:
        supplier_row = df_product_suppliers[df_product_suppliers["supplier_id"] == target_supplier_id]
        if supplier_row.empty:
            print(f"Warning: Supplier {target_supplier_id} not found. Defaulting to primary supplier.")
            supplier_row = df_product_suppliers.sort_values(by="supplier_reliability", ascending=False).iloc[0]
        else:
            supplier_row = supplier_row.iloc[0]
    else:
        # Sort by reliability descending and pick the top one as primary supplier
        supplier_row = df_product_suppliers.sort_values(by="supplier_reliability", ascending=False).iloc[0]

    # Mapped inputs
    supplier_price = float(supplier_row.get("supplier_price", 0))
    freight_cost = float(supplier_row.get("freight_cost", 0))
    warehouse_cost = float(supplier_row.get("warehouse_cost", 0))
    gst_tax = float(supplier_row.get("gst_tax", 0))
    reliability = float(supplier_row.get("supplier_reliability", 1.0))
    lead_time_days = float(supplier_row.get("lead_time_days", 5.0))
    category = str(supplier_row.get("category", "")).lower()

    # 3. True Landed Cost (incorporating currency fluctuations)
    adjusted_supplier_price = supplier_price * currency_fluctuation_factor
    true_landed_cost = adjusted_supplier_price + freight_cost + warehouse_cost + gst_tax

    # 4. Supply Risk (0.0 to 1.0)
    # Higher risk if reliability is low, and if lead times are long (normalized to 15 days scale)
    reliability_risk = 1.0 - reliability
    lead_time_risk = np.clip(lead_time_days / 15.0, 0.0, 1.0)
    supply_risk = (0.7 * reliability_risk) + (0.3 * lead_time_risk)
    supply_risk = np.clip(supply_risk, 0.0, 1.0)

    # 5. Category-Specific Margin
    minimum_margin_pct = CATEGORY_MARGINS.get(category, DEFAULT_MARGIN)

    # 6. Risk Buffer
    # Buffer up to 10% of landed cost based on supply risk, and 5% based on cost volatility
    risk_buffer = true_landed_cost * ((supply_risk * 0.10) + (cost_volatility * 0.05))

    # 7. Minimum Safe Price
    # minimum_safe_price = landed_cost + risk_buffer + minimum_margin
    minimum_margin = true_landed_cost * minimum_margin_pct
    minimum_safe_price = true_landed_cost + risk_buffer + minimum_margin

    return {
        "supplier_id": supplier_row.get("supplier_id"),
        "supplier_reliability": round(reliability, 3),
        "lead_time_days": int(lead_time_days),
        "category": category,
        "minimum_margin_pct": round(minimum_margin_pct, 3),
        "true_landed_cost": float(round(true_landed_cost, 2)),
        "cost_volatility": float(round(cost_volatility, 3)),
        "supply_risk": float(round(supply_risk, 3)),
        "risk_buffer": float(round(risk_buffer, 2)),
        "minimum_safe_price": float(round(minimum_safe_price, 2))
    }


# -----------------------------
# STEP 3: MAIN PIPELINE
# -----------------------------
def run_pipeline(products_csv_path, procurement_csv_path, target_product_id="SKU_1000", target_supplier_id=None, currency_fluctuation_factor=1.0):
    # Perform relational join dynamically
    df_joined = load_and_join_data(products_csv_path, procurement_csv_path)

    # Filter for the target product
    df_product_suppliers = df_joined[df_joined["product_id"] == target_product_id]
    if df_product_suppliers.empty:
        raise ValueError(f"Product ID {target_product_id} not found in joined dataset.")

    # Compute metrics
    metrics = compute_procurement_metrics(df_product_suppliers, target_supplier_id, currency_fluctuation_factor)

    print(f"\n===== PROCUREMENT & SUPPLY FOR {target_product_id} =====")
    print("Product Name:          ", df_product_suppliers.iloc[0]["product_name"])
    print("Category:              ", metrics["category"].upper())
    print("Selected Supplier:     ", metrics["supplier_id"])
    print("Supplier Reliability:  ", f"{round(metrics['supplier_reliability'] * 100, 1)}%")
    print("Lead Time (days):      ", metrics["lead_time_days"])
    print("---------------------------------------------")
    print("True Landed Cost ($):  ", metrics["true_landed_cost"])
    print("Cost Volatility (0-1): ", metrics["cost_volatility"])
    print("Supply Risk (0-1):     ", metrics["supply_risk"])
    print("Risk Buffer ($):       ", metrics["risk_buffer"])
    print("Target Margin (%):     ", f"{round(metrics['minimum_margin_pct'] * 100, 1)}%")
    print("---------------------------------------------")
    print("Minimum Safe Price ($):", metrics["minimum_safe_price"])

    return {
        "product_id": target_product_id,
        "supplier_id": metrics["supplier_id"],
        "true_landed_cost": metrics["true_landed_cost"],
        "cost_volatility": metrics["cost_volatility"],
        "supply_risk": metrics["supply_risk"],
        "minimum_safe_price": metrics["minimum_safe_price"]
    }


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    from backend.config import CUSTOMER_PRODUCTS_PATH, CUSTOMER_PROCUREMENT_PATH
    # Assumes run from workspace root
    result = run_pipeline(
        products_csv_path=CUSTOMER_PRODUCTS_PATH,
        procurement_csv_path=CUSTOMER_PROCUREMENT_PATH,
        target_product_id="SKU_1000",
        currency_fluctuation_factor=1.0
    )
    print("\nPipeline execution result:")
    print(result)

