import pandas as pd
import numpy as np
import os


# -----------------------------
# STEP 1: LOAD DATA
# -----------------------------
def load_data(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Data file not found at: {path}")
    df = pd.read_csv(path)
    return df


# -----------------------------
# STEP 2: RETRIEVE OUR PRICE
# -----------------------------
def get_our_price(sales_csv_path, target_product_id):
    """
    Retrieves our latest selling price for the product from sales.csv.
    """
    try:
        df_sales = pd.read_csv(sales_csv_path)
        df_product_sales = df_sales[df_sales["product_id"] == target_product_id]
        if not df_product_sales.empty:
            # Sort by date and take the last row
            df_product_sales = df_product_sales.sort_values(by="date")
            latest_row = df_product_sales.iloc[-1]
            price = latest_row.get("selling_price", latest_row.get("price", None))
            return float(price) if price is not None else None
    except Exception as e:
        print(f"Warning: Could not retrieve our price from sales.csv ({e}). Using competitor baseline.")
    return None


# -----------------------------
# STEP 3: COMPUTE MARKET METRICS
# -----------------------------
def compute_market_metrics(df_product, our_price=None, market_trend_score=0.5):
    """
    Computes competitor band, market pressure, and competitive gap.
    """
    if df_product.empty:
        raise ValueError("Competitor data is empty for the target product.")

    # 1. Competitor Band [min, max]
    min_comp = float(df_product["competitor_price"].min())
    max_comp = float(df_product["competitor_price"].max())
    competitor_band = [round(min_comp, 2), round(max_comp, 2)]

    # Baselines
    median_comp = float(df_product["competitor_price"].median())
    mean_comp = float(df_product["competitor_price"].mean())

    # 2. Competitive Gap
    # If our price is not provided, default to the median competitor price (gap = 0.0)
    if our_price is None:
        our_price = median_comp

    competitive_gap = our_price - median_comp
    competitive_gap_pct = competitive_gap / (median_comp + 1e-5)

    # 3. Market Pressure (0.0 to 1.0)
    # Blend competitor promotion rate, competitor ratings, and market trend
    # High promotions -> High pressure
    # High competitor ratings -> High pressure (stronger competitor quality threat)
    promotion_rate = float(df_product["promotion_active"].astype(bool).mean())
    
    # Normalize rating from 0.0 to 1.0 (assuming max rating of 5.0)
    avg_rating = float(df_product["rating"].mean())
    rating_score = np.clip(avg_rating / 5.0, 0.0, 1.0)

    # Blended score: 40% promo activity, 40% rating threat, 20% market trend
    market_pressure = (0.4 * promotion_rate) + (0.4 * rating_score) + (0.2 * market_trend_score)
    market_pressure = np.clip(market_pressure, 0.0, 1.0)

    # 4. Recommended Multiplier
    # If we are overpriced (gap > 0), lower our price (multiplier < 1.0)
    # If we are underpriced (gap < 0), we have room to raise price (multiplier > 1.0)
    # Limit changes to +/- 15%
    recommended_multiplier = 1.0 - np.clip(competitive_gap_pct, -0.15, 0.15)

    return {
        "our_price": float(round(our_price, 2)),
        "competitor_band": competitor_band,
        "median_competitor_price": float(round(median_comp, 2)),
        "mean_competitor_price": float(round(mean_comp, 2)),
        "competitive_gap": float(round(competitive_gap, 2)),
        "competitive_gap_pct": float(round(competitive_gap_pct, 4)),
        "competitor_promotion_rate": float(round(promotion_rate, 3)),
        "average_competitor_rating": float(round(avg_rating, 2)),
        "market_pressure": float(round(market_pressure, 3)),
        "recommended_multiplier": float(round(recommended_multiplier, 3))
    }


# -----------------------------
# STEP 4: MAIN PIPELINE
# -----------------------------
def run_pipeline(competitors_csv=None, sales_csv=None, target_product_id="SKU_1000", market_region=None, market_trend_score=0.5):
    # Dynamically resolve path defaults at call time to support routing configuration
    import backend.config as cfg
    if competitors_csv is None:
        competitors_csv = cfg.CUSTOMER_COMPETITOR_PATH
    if sales_csv is None:
        sales_csv = cfg.CUSTOMER_SALES_PATH

    df_comp = load_data(competitors_csv)

    # Filter for the target product
    df_product = df_comp[df_comp["product_id"] == target_product_id]
    if df_product.empty:
        raise ValueError(f"Product ID {target_product_id} not found in competitor dataset.")

    # Filter by region if specified
    if market_region:
        df_region = df_product[df_product["market_region"].str.lower() == market_region.lower()]
        if not df_region.empty:
            df_product = df_region

    # Retrieve our latest price
    our_price = get_our_price(sales_csv, target_product_id)

    # Compute metrics
    metrics = compute_market_metrics(df_product, our_price, market_trend_score)

    print(f"\n===== MARKET INTELLIGENCE FOR {target_product_id} =====")
    print("Product Name:             ", df_product.iloc[0]["product_name"])
    print("Market Region:            ", market_region if market_region else "All Regions")
    print("Number of Competitors:    ", len(df_product))
    print("---------------------------------------------")
    print("Our Current Price:        ", metrics["our_price"])
    print("Competitor Price Band:    ", metrics["competitor_band"])
    print("Median Competitor Price:  ", metrics["median_competitor_price"])
    print("Mean Competitor Price:    ", metrics["mean_competitor_price"])
    print("Competitive Gap ($ / unit):", metrics["competitive_gap"])
    print("Competitive Gap (%):      ", f"{round(metrics['competitive_gap_pct'] * 100, 2)}%")
    print("---------------------------------------------")
    print("Competitor Promo Rate:    ", f"{round(metrics['competitor_promotion_rate'] * 100, 1)}%")
    print("Avg Competitor Rating:    ", metrics["average_competitor_rating"])
    print("Market Pressure (0-1):    ", metrics["market_pressure"])
    print("Recommended Multiplier:   ", metrics["recommended_multiplier"])

    return {
        "product_id": target_product_id,
        "market_region": market_region,
        "competitor_band": metrics["competitor_band"],
        "market_pressure": metrics["market_pressure"],
        "competitive_gap": metrics["competitive_gap"],
        "recommended_multiplier": metrics["recommended_multiplier"]
    }


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    # Assumes run from workspace root
    result = run_pipeline(
        competitors_csv=CUSTOMER_COMPETITOR_PATH,
        sales_csv=CUSTOMER_SALES_PATH,
        target_product_id="SKU_1000",
        market_region="Delhi",
        market_trend_score=0.5
    )
    print("\nPipeline execution result:")
    print(result)
