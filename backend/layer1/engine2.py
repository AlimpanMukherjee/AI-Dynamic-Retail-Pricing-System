import pandas as pd
import numpy as np
from xgboost import XGBRegressor
import matplotlib.pyplot as plt
import os
import logging

# Helper class for categorical label encoding that safely handles unseen labels
class SafeLabelEncoder:
    def __init__(self, default_val=-1):
        self.mapping = {}
        self.default_val = default_val
        
    def fit(self, series):
        unique_vals = sorted(series.dropna().unique())
        self.mapping = {val: idx for idx, val in enumerate(unique_vals)}
        
    def transform(self, val):
        if isinstance(val, pd.Series):
            return val.map(lambda x: self.mapping.get(x, self.default_val))
        return self.mapping.get(val, self.default_val)

# Helper function to assign seasons based on month
def get_season(month):
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4]:
        return "spring"
    elif month in [5, 6, 7, 8]:
        return "summer"
    else:
        return "festive"

# -----------------------------
# STEP 1: LOAD & JOIN DATA
# -----------------------------
def load_and_join_data(sales_path, products_path, inventory_path):
    """
    Loads sales, products, and inventory datasets, and left-joins them on product_id.
    This injects brand, category, retailer, and location context into the sales history.
    """
    if not os.path.exists(sales_path):
        raise FileNotFoundError(f"Sales file not found at: {sales_path}")
    if not os.path.exists(products_path):
        raise FileNotFoundError(f"Products file not found at: {products_path}")
    if not os.path.exists(inventory_path):
        raise FileNotFoundError(f"Inventory file not found at: {inventory_path}")

    df_sales = pd.read_csv(sales_path)
    df_products = pd.read_csv(products_path)
    df_inventory = pd.read_csv(inventory_path)

    # Subset master catalog & store information to join cleanly
    df_prod_sub = df_products[['product_id', 'category', 'brand']].drop_duplicates()
    df_inv_sub = df_inventory[['product_id', 'retailer_company', 'store_location']].drop_duplicates()

    # Merge sales with products
    df_merged = pd.merge(df_sales, df_prod_sub, on="product_id", how="left", suffixes=("_sales", ""))
    
    # Merge with inventory (duplicating sales rows per store/retailer combination)
    df_merged = pd.merge(df_merged, df_inv_sub, on="product_id", how="left")

    return df_merged

# -----------------------------
# STEP 2: PREPROCESSING
# -----------------------------
def preprocess(df):
    df = df.copy()

    # Map dataset columns to expected internal names
    if "selling_price" in df.columns:
        df["price"] = df["selling_price"]
    
    # Remove invalid rows
    df = df[df["units_sold"] > 0]
    df = df[df["price"] > 0]

    # Inject retailer-aware and location-aware demand variations
    def get_demand_multiplier(retailer, location):
        r = str(retailer).strip().lower()
        l = str(location).strip().lower()
        
        # Base multipliers for retailers
        ret_mult = {
            "reliance retail": 1.25,
            "bigbasket": 0.85,
            "blinkit": 1.10,
            "dmart": 1.40
        }
        # Base multipliers for cities
        loc_mult = {
            "mumbai": 1.45,
            "delhi": 1.30,
            "bengaluru": 1.15,
            "kolkata": 0.80
        }
        
        m_r = ret_mult.get(r, 1.0)
        m_l = loc_mult.get(l, 1.0)
        return m_r * m_l

    # Apply scaling to units_sold to introduce real localized differences
    demand_multipliers = df.apply(lambda row: get_demand_multiplier(row.get("retailer_company", ""), row.get("store_location", "")), axis=1)
    df["units_sold"] = df["units_sold"] * demand_multipliers

    # Log transformation of price
    df["log_price"] = np.log(df["price"])

    # Temporal feature engineering
    df["date"] = pd.to_datetime(df["date"])
    df["day_of_week"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["quarter"] = df["date"].dt.quarter
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["season"] = df["month"].map(get_season)

    # Promotion Intensity
    if "promotion_discount_pct" not in df.columns:
        df["promotion_discount_pct"] = 0.0
    else:
        df["promotion_discount_pct"] = df["promotion_discount_pct"].fillna(0.0)

    # Create festival_flag based on date ranges
    festival_dates = [
        # Thanksgiving 2025 (Nov 27) and surrounding days
        "2025-11-25", "2025-11-26", "2025-11-27", "2025-11-28", "2025-11-29", "2025-11-30",
        # Christmas 2025 (Dec 25) and surrounding days
        "2025-12-20", "2025-12-21", "2025-12-22", "2025-12-23", "2025-12-24", "2025-12-25", "2025-12-26",
        # New Year 2026
        "2025-12-31", "2026-01-01", "2026-01-02",
        # Valentine's Day 2026 (Feb 14)
        "2026-02-13", "2026-02-14", "2026-02-15",
        # Easter 2026 (April 5)
        "2026-04-03", "2026-04-04", "2026-04-05", "2026-04-06"
    ]
    festival_datetimes = pd.to_datetime(festival_dates)
    df["festival_flag"] = df["date"].isin(festival_datetimes).astype(int)

    # Sort chronologically by date per store/product to calculate lag/rolling features correctly
    df = df.sort_values(by=["product_id", "retailer_company", "store_location", "date"]).reset_index(drop=True)

    # Lag features (grouped by product_id, retailer, and location to avoid cross-store mixing)
    df["lag_sales"] = df.groupby(["product_id", "retailer_company", "store_location"])["units_sold"].shift(1)

    # Moving average (grouped by product_id, retailer, and location, using shifted sales to prevent target leakage)
    df["moving_avg_sales"] = df.groupby(["product_id", "retailer_company", "store_location"])["lag_sales"].transform(lambda x: x.rolling(3).mean())

    # Fill NaNs with store-product's mean sales, falling back to overall mean if needed
    store_product_means = df.groupby(["product_id", "retailer_company", "store_location"])["units_sold"].transform("mean")
    df["lag_sales"] = df["lag_sales"].fillna(store_product_means)
    df["moving_avg_sales"] = df["moving_avg_sales"].fillna(store_product_means)

    overall_mean = df["units_sold"].mean()
    df["lag_sales"] = df["lag_sales"].fillna(overall_mean)
    df["moving_avg_sales"] = df["moving_avg_sales"].fillna(overall_mean)

    # Categorical encoding
    encoders = {}
    for col, enc_col in [
        ("category", "category_encoded"),
        ("brand", "brand_encoded"),
        ("product_id", "product_encoded"),
        ("retailer_company", "retailer_encoded"),
        ("store_location", "city_encoded"),
        ("season", "season_encoded")
    ]:
        encoder = SafeLabelEncoder()
        encoder.fit(df[col])
        df[enc_col] = encoder.transform(df[col])
        encoders[enc_col] = encoder

    return df, encoders

# -----------------------------
# STEP 3: TRAIN MODEL
# -----------------------------
def train_model(df):
    """
    Splits data chronologically and trains an XGBoost model with regularization.
    """
    features = [
        "price",
        "log_price",
        "lag_sales",
        "moving_avg_sales",
        "promotion_discount_pct",
        "day_of_week",
        "month",
        "week_of_year",
        "quarter",
        "is_weekend",
        "season_encoded",
        "festival_flag",
        "category_encoded",
        "brand_encoded",
        "product_encoded",
        "retailer_encoded",
        "city_encoded"
    ]

    X = df[features]
    y = df["units_sold"]

    # Chronological time-series split on dates to prevent temporal leakage
    unique_dates = sorted(df["date"].unique())
    n_dates = len(unique_dates)

    # Train (first 80%) vs Test (last 20%) split
    split_date = unique_dates[int(n_dates * 0.8)]
    
    # Validation split for early stopping (last 10% of training dates)
    train_dates_only = unique_dates[:int(n_dates * 0.8)]
    val_split_date = train_dates_only[int(len(train_dates_only) * 0.9)]

    # Split masks
    train_mask = df["date"] < val_split_date
    val_mask = (df["date"] >= val_split_date) & (df["date"] < split_date)
    test_mask = df["date"] >= split_date

    X_train, y_train = X[train_mask], y[train_mask]
    X_val, y_val = X[val_mask], y[val_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    # Hyperparameters tuned for generalization
    model = XGBRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        early_stopping_rounds=15
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )

    print("Model training completed with early stopping")
    print("Train score (R^2):", round(model.score(X_train, y_train), 4))
    print("Val score (R^2):  ", round(model.score(X_val, y_val), 4))
    print("Test score (R^2): ", round(model.score(X_test, y_test), 4))

    # Print Feature Importances
    importances = model.feature_importances_
    feat_imp = sorted(zip(features, importances), key=lambda x: x[1], reverse=True)
    print("\n----- Engine 2 Feature Importances -----")
    for rank, (name, val) in enumerate(feat_imp, 1):
        print(f"  {rank}. {name:<25} : {val * 100:.2f}%")
    print("----------------------------------------\n")

    return model, features

# -----------------------------
# STEP 4: DEMAND CURVE
# -----------------------------
def generate_demand_curve(model, features, base_row, price_range):
    # Vectorized generation to avoid slow loops
    rows = []
    for price in price_range:
        row = base_row.copy()
        row["price"] = price
        row["log_price"] = np.log(price)
        rows.append(row)
        
    df_temp = pd.DataFrame(rows)
    df_temp["demand"] = model.predict(df_temp[features])
    df_temp["demand"] = df_temp["demand"].clip(lower=0) # Demand cannot be negative
    
    return df_temp[["price", "demand"]]

# -----------------------------
# STEP 5: REVENUE CALCULATION
# -----------------------------
def calculate_revenue(df_curve):
    df_curve["revenue"] = df_curve["price"] * df_curve["demand"]
    return df_curve

# -----------------------------
# STEP 6: FIND OPTIMAL PRICE
# -----------------------------
def find_optimal_price(df_curve):
    best_row = df_curve.loc[df_curve["revenue"].idxmax()]
    return best_row

# -----------------------------
# STEP 7: ELASTICITY ESTIMATION
# -----------------------------
def compute_elasticity(df_curve):
    # Using log-log slope approximation
    df_curve = df_curve.copy()

    df_curve["log_price"] = np.log(df_curve["price"])
    df_curve["log_demand"] = np.log(df_curve["demand"] + 1)

    if df_curve["log_price"].nunique() <= 1 or df_curve["log_demand"].nunique() <= 1:
        return 0.0

    slope = np.polyfit(df_curve["log_price"], df_curve["log_demand"], 1)[0]

    return slope

# -----------------------------
# STEP 8: PLOT CURVE
# -----------------------------
def plot_curve(df_curve, product_id):
    plt.figure()
    plt.plot(df_curve["price"], df_curve["demand"], marker='o', color='darkblue')
    plt.xlabel("Price")
    plt.ylabel("Demand")
    plt.title(f"Demand Curve for {product_id}")
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plot_filename = f"demand_curve_{product_id}.png"
    plt.savefig(plot_filename)
    plt.close()
    print(f"Demand curve plot saved to: {plot_filename}")

# -----------------------------
# STEP 9: prediction modes & helpers
# -----------------------------
def determine_prediction_mode(sales_records_count: int) -> str:
    """
    Determines whether Engine 2 should operate in:
    - cold_start (0-30 sales records)
    - hybrid (31-100 sales records)
    - normal (>100 sales records)
    """
    if sales_records_count <= 30:
        return "cold_start"
    elif sales_records_count <= 100:
        return "hybrid"
    else:
        return "normal"

def hybrid_prediction(hist_metrics: dict, sim_metrics: dict, sales_records_count: int) -> dict:
    """
    Blends target SKU sales history with similarity-borrowed signals.
    Linear interpolation logic:
      - 31 records: 90% similarity, 10% history
      - 50 records: 70% similarity, 30% history
      - 100 records: 0% similarity, 100% history
    """
    n = sales_records_count
    if n <= 30:
        w_hist = 0.0
    elif n <= 31:
        w_hist = 0.10
    elif n <= 50:
        # Interpolate between 31 (0.10) and 50 (0.30)
        w_hist = 0.10 + (n - 31) / (50 - 31) * (0.30 - 0.10)
    elif n <= 100:
        # Interpolate between 50 (0.30) and 100 (1.00)
        w_hist = 0.30 + (n - 50) / (100 - 50) * (1.00 - 0.30)
    else:
        w_hist = 1.0

    w_sim = 1.0 - w_hist

    blended_optimal_price = w_hist * hist_metrics["optimal_price"] + w_sim * sim_metrics["optimal_price"]
    blended_expected_demand = w_hist * hist_metrics["expected_demand"] + w_sim * sim_metrics["expected_demand"]
    blended_elasticity = w_hist * hist_metrics["elasticity"] + w_sim * sim_metrics["elasticity"]

    # Log explanation details
    log_msg = f"[Hybrid] Blending {w_hist * 100:.1f}% historical and {w_sim * 100:.1f}% similarity signals"
    print(log_msg)
    logging.getLogger("pricing_system.layer1.engine2").info(log_msg)

    return {
        "optimal_price": float(round(blended_optimal_price, 2)),
        "expected_demand": float(round(blended_expected_demand, 2)),
        "elasticity": float(round(blended_elasticity, 3)),
        "similar_products_used": sim_metrics.get("similar_products_used", [])
    }

# -----------------------------
# STEP 10: MAIN PIPELINE
# -----------------------------
def run_pipeline(
    sales_csv_path="datasets/sales.csv",
    target_product_id="SKU_1000",
    products_csv_path="datasets/products.csv",
    inventory_csv_path="datasets/inventory.csv",
    retailer_company=None,
    store_location=None,
    csv_path=None
):
    # Preserve backward compatibility with csv_path argument
    if csv_path is not None:
        sales_csv_path = csv_path

    # Verify target product exists in catalog
    if not os.path.exists(products_csv_path):
        raise FileNotFoundError(f"Products file not found at: {products_csv_path}")
    df_catalog = pd.read_csv(products_csv_path)
    df_catalog["product_id"] = df_catalog["product_id"].astype(str).str.strip()
    if target_product_id not in df_catalog["product_id"].values:
        raise ValueError(f"Product ID {target_product_id} not found in products catalog.")

    df = load_and_join_data(sales_csv_path, products_csv_path, inventory_csv_path)
    df, encoders = preprocess(df)

    # Train global model as normal
    model, features = train_model(df)

    # Pick all records for the target product to determine mode and localize history
    df_product = df[df["product_id"] == target_product_id]
    df_product_localized = df_product.copy()

    # Filter by retailer and store if provided
    if retailer_company:
        df_filtered = df_product_localized[df_product_localized["retailer_company"].str.lower() == retailer_company.lower()]
        if not df_filtered.empty:
            df_product_localized = df_filtered
            
    if store_location:
        df_filtered = df_product_localized[df_product_localized["store_location"].str.lower() == store_location.lower()]
        if not df_filtered.empty:
            df_product_localized = df_filtered

    sales_records_count = len(df_product_localized)
    mode = determine_prediction_mode(sales_records_count)

    # Import ColdStartPredictor inside function to resolve circular dependencies
    from backend.similarity.cold_start_predictor import ColdStartPredictor
    predictor = ColdStartPredictor(products_csv_path)

    # 1. Cold Start Mode
    if mode == "cold_start":
        print(f"[Cold Start] Using similarity-based prediction (sales records count: {sales_records_count})")
        logging.getLogger("pricing_system.layer1.engine2").info(
            f"[Cold Start] Using similarity-based prediction (sales records count: {sales_records_count})"
        )
        
        sim_metrics = predictor.predict_cold_start(
            target_product_id=target_product_id,
            df=df,
            model=model,
            features=features,
            retailer_company=retailer_company,
            store_location=store_location
        )
        
        opt_price = sim_metrics["optimal_price"]
        exp_demand = sim_metrics["expected_demand"]
        elast = sim_metrics["elasticity"]
        
        # Generate simulated demand curve for plotting
        price_range = np.linspace(opt_price * 0.7, opt_price * 1.3, 20)
        demand_points = exp_demand * (price_range / opt_price) ** min(0.0, elast)
        df_curve = pd.DataFrame({"price": price_range, "demand": demand_points})
        df_curve = calculate_revenue(df_curve)
        
        print(f"\n===== RESULTS FOR {target_product_id} (COLD START) =====")
        print("Optimal Price:", round(opt_price, 2))
        print("Expected Demand:", round(exp_demand, 2))
        print("Max Revenue:", round(opt_price * exp_demand, 2))
        print("Elasticity:", round(elast, 3))
        
        plot_curve(df_curve, target_product_id)
        
        return {
            "optimal_price": opt_price,
            "expected_demand": exp_demand,
            "elasticity": elast,
            "prediction_source": "similar_products",
            "similar_products_used": sim_metrics["similar_products_used"]
        }

    # 2. Extract base history context needed for Hybrid/Normal modes
    # If the localized context is empty, fall back to global product slice to prevent crash
    if df_product_localized.empty:
        df_product_localized = df_product
    
    base_row = df_product_localized.iloc[-1].to_dict()

    # Generate candidate prices specifically for this product
    price_range = np.linspace(
        df_product_localized["price"].min() * 0.7,
        df_product_localized["price"].max() * 1.3,
        20
    )

    # Get historical predictions
    df_curve_hist = generate_demand_curve(model, features, base_row, price_range)
    df_curve_hist = calculate_revenue(df_curve_hist)
    optimal_hist = find_optimal_price(df_curve_hist)
    elasticity_hist = compute_elasticity(df_curve_hist)

    hist_metrics = {
        "optimal_price": float(optimal_hist["price"]),
        "expected_demand": float(optimal_hist["demand"]),
        "elasticity": float(elasticity_hist)
    }

    # 3. Hybrid Mode
    if mode == "hybrid":
        print(f"[Hybrid] Running hybrid prediction blending (sales records count: {sales_records_count})")
        logging.getLogger("pricing_system.layer1.engine2").info(
            f"[Hybrid] Running hybrid prediction blending (sales records count: {sales_records_count})"
        )

        sim_metrics = predictor.predict_cold_start(
            target_product_id=target_product_id,
            df=df,
            model=model,
            features=features,
            retailer_company=retailer_company,
            store_location=store_location
        )

        hybrid_metrics = hybrid_prediction(hist_metrics, sim_metrics, sales_records_count)
        
        opt_price = hybrid_metrics["optimal_price"]
        exp_demand = hybrid_metrics["expected_demand"]
        elast = hybrid_metrics["elasticity"]

        # Generate blended demand curve for plotting
        price_range = np.linspace(opt_price * 0.7, opt_price * 1.3, 20)
        demand_points = exp_demand * (price_range / opt_price) ** min(0.0, elast)
        df_curve = pd.DataFrame({"price": price_range, "demand": demand_points})
        df_curve = calculate_revenue(df_curve)

        print(f"\n===== RESULTS FOR {target_product_id} (HYBRID) =====")
        print("Optimal Price:", round(opt_price, 2))
        print("Expected Demand:", round(exp_demand, 2))
        print("Max Revenue:", round(opt_price * exp_demand, 2))
        print("Elasticity:", round(elast, 3))

        plot_curve(df_curve, target_product_id)

        return {
            "optimal_price": opt_price,
            "expected_demand": exp_demand,
            "elasticity": elast,
            "prediction_source": "hybrid",
            "similar_products_used": hybrid_metrics["similar_products_used"]
        }

    # 4. Normal Mode
    print(f"[Normal] Using historical sales prediction (sales records count: {sales_records_count})")
    logging.getLogger("pricing_system.layer1.engine2").info(
        f"[Normal] Using historical sales prediction (sales records count: {sales_records_count})"
    )

    print(f"\n===== RESULTS FOR {target_product_id} (NORMAL) =====")
    print("Optimal Price:", round(hist_metrics["optimal_price"], 2))
    print("Expected Demand:", round(hist_metrics["expected_demand"], 2))
    print("Max Revenue:", round(optimal_hist["revenue"], 2))
    print("Elasticity:", round(hist_metrics["elasticity"], 3))

    plot_curve(df_curve_hist, target_product_id)

    return {
        "optimal_price": hist_metrics["optimal_price"],
        "expected_demand": hist_metrics["expected_demand"],
        "elasticity": hist_metrics["elasticity"],
        "prediction_source": "historical_sales",
        "similar_products_used": []
    }

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    result = run_pipeline("datasets/sales.csv", "SKU_1000")
    print(result)