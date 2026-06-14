FEATURE_COLUMNS = [
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
    "city_encoded",
    "retailer_strength",
    "city_strength"
]

MODEL_PARAMS = {
    "n_estimators": 300,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "random_state": 42,
    "early_stopping_rounds": 15
}

PRICE_RANGE_MULTIPLIERS = {
    "min_multiplier": 0.7,
    "max_multiplier": 1.3,
    "num_candidates": 20
}

MODE_THRESHOLDS = {
    "cold_start_max": 30,
    "hybrid_max": 100
}
