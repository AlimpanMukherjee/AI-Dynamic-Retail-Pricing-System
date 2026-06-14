import pandas as pd
import numpy as np

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

def preprocess(df, encoders=None):
    df = df.copy()

    # Map dataset columns to expected internal names
    if "selling_price" in df.columns:
        df["price"] = df["selling_price"]
    
    # Remove invalid rows
    df = df[df["units_sold"] > 0]
    df = df[df["price"] > 0]

    # Calculate retailer and city multiplier strengths
    def get_strengths(retailer, location):
        r = str(retailer).strip().lower()
        l = str(location).strip().lower()
        ret_mult = {
            "reliance retail": 1.25,
            "bigbasket": 0.85,
            "blinkit": 1.10,
            "dmart": 1.40
        }
        loc_mult = {
            "mumbai": 1.45,
            "delhi": 1.30,
            "bengaluru": 1.15,
            "kolkata": 0.80
        }
        return ret_mult.get(r, 1.0), loc_mult.get(l, 1.0)

    strengths = df.apply(lambda row: get_strengths(row.get("retailer_company", ""), row.get("store_location", "")), axis=1)
    df["retailer_strength"] = [s[0] for s in strengths]
    df["city_strength"] = [s[1] for s in strengths]

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
        "2025-11-25", "2025-11-26", "2025-11-27", "2025-11-28", "2025-11-29", "2025-11-30",
        "2025-12-20", "2025-12-21", "2025-12-22", "2025-12-23", "2025-12-24", "2025-12-25", "2025-12-26",
        "2025-12-31", "2026-01-01", "2026-01-02",
        "2026-02-13", "2026-02-14", "2026-02-15",
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
    if encoders is None:
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
    else:
        for col, enc_col in [
            ("category", "category_encoded"),
            ("brand", "brand_encoded"),
            ("product_id", "product_encoded"),
            ("retailer_company", "retailer_encoded"),
            ("store_location", "city_encoded"),
            ("season", "season_encoded")
        ]:
            encoder = encoders[enc_col]
            df[enc_col] = encoder.transform(df[col])

    return df, encoders
