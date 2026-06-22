import os
import logging
from datetime import datetime
import pandas as pd
import numpy as np

import backend.config as cfg
from backend.layer1.engine2.config import FEATURE_COLUMNS, PRICE_RANGE_MULTIPLIERS
from backend.layer1.engine2.data_loader import load_and_join_data
from backend.layer1.engine2.preprocessing import preprocess
from backend.layer1.engine2.trainer import train_model
from backend.layer1.engine2.predictor import (
    generate_demand_curve,
    calculate_revenue,
    find_optimal_price,
    plot_curve
)
from backend.layer1.engine2.elasticity import compute_elasticity
from backend.layer1.engine2.cold_start_handler import (
    determine_prediction_mode,
    hybrid_prediction
)
from backend.layer1.engine2.model_store import (
    save_model,
    load_model,
    save_metadata,
    load_metadata
)
from backend.layer1.engine2.utils import store_prediction_history

logger = logging.getLogger("pricing_system.layer1.engine2")

MODEL_DIR = os.path.join(cfg.PROJECT_ROOT, "backend", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "engine2_model.pkl")
METADATA_PATH = os.path.join(MODEL_DIR, "engine2_metadata.json")

def run_pipeline(
    sales_csv_path=None,
    target_product_id="SKU_1000",
    products_csv_path=None,
    inventory_csv_path=None,
    retailer_company=None,
    store_location=None,
    csv_path=None,
    run_ablation=False,
    run_permutation=False,
    force_retrain=False,
    generate_plot=False
):
    if csv_path is not None:
        sales_csv_path = csv_path

    # Dynamically resolve path defaults
    if sales_csv_path is None:
        sales_csv_path = cfg.CUSTOMER_SALES_PATH
    if products_csv_path is None:
        products_csv_path = cfg.CUSTOMER_PRODUCTS_PATH
    if inventory_csv_path is None:
        inventory_csv_path = cfg.CUSTOMER_INVENTORY_PATH

    from backend.onboarding.customer_profile import get_customer_profile
    profile = get_customer_profile()
    sales_history_count = profile["sales_records"]
    engine2_confidence = profile["engine2_confidence"]

    # Verify target product exists in catalog
    if not os.path.exists(products_csv_path):
        raise FileNotFoundError(f"Products file not found at: {products_csv_path}")
    df_catalog = pd.read_csv(products_csv_path)
    df_catalog["product_id"] = df_catalog["product_id"].astype(str).str.strip()
    if target_product_id not in df_catalog["product_id"].values:
        raise ValueError(f"Product ID {target_product_id} not found in products catalog.")

    # Check model presence and retraining flag
    model_loaded = False
    model, features, encoders = None, None, None
    metadata = None

    if not force_retrain and os.path.exists(MODEL_PATH) and os.path.exists(METADATA_PATH):
        try:
            model, features, encoders = load_model(MODEL_PATH)
            metadata = load_metadata(METADATA_PATH)
            model_loaded = True
            logger.info("Model loaded")
            print("Model loaded from disk")
            print("Train R²:", metadata.get("train_r2"))
            print("Validation R²:", metadata.get("validation_r2"))
            print("Test R²:", metadata.get("test_r2"))
        except Exception as e:
            logger.warning(f"Error loading model from disk: {str(e)}. Retraining instead.")
            model_loaded = False

    df = load_and_join_data(sales_csv_path, products_csv_path, inventory_csv_path)

    if not model_loaded:
        if len(df) >= 35:
            logger.info("Retraining started")
            # Preprocess fits and encodes
            df_preprocessed, encoders = preprocess(df)
            model, features, eval_stats = train_model(df_preprocessed)
            
            # Save model and metadata
            save_model(model, features, encoders, MODEL_PATH)
            metadata = {
                "model_version": "1.0",
                "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "training_rows": len(df),
                "train_r2": eval_stats["train_r2"],
                "validation_r2": eval_stats["validation_r2"],
                "test_r2": eval_stats["test_r2"]
            }
            save_metadata(metadata, METADATA_PATH)
            model_loaded = True
        else:
            logger.warning("Insufficient data to auto-train Engine 2 model. Using cold start / fallback mode.")
            model = None
            features = []
            encoders = None
            if not df.empty:
                df_preprocessed, _ = preprocess(df)
            else:
                df_preprocessed = df.copy()
    else:
        # Preprocess transfers pre-fitted encoders to match loaded model
        if not df.empty:
            df_preprocessed, _ = preprocess(df, encoders=encoders)
        else:
            df_preprocessed = df.copy()

    # Pick target product records to localize history context
    df_product = df_preprocessed[df_preprocessed["product_id"] == target_product_id]
    df_product_localized = df_product.copy()

    # Look up target store multipliers
    def get_strengths(retailer, location):
        r = str(retailer).strip().lower()
        l = str(location).strip().lower()
        ret_mult = {"reliance retail": 1.25, "bigbasket": 0.85, "blinkit": 1.10, "dmart": 1.40}
        loc_mult = {"mumbai": 1.45, "delhi": 1.30, "bengaluru": 1.15, "kolkata": 0.80}
        return ret_mult.get(r, 1.0), loc_mult.get(l, 1.0)
        
    target_ret_strength, target_loc_strength = get_strengths(retailer_company, store_location)

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

    from backend.similarity.cold_start_predictor import ColdStartPredictor
    predictor_engine = ColdStartPredictor(products_csv_path)

    # 1. Cold Start Mode
    if mode == "cold_start":
        logger.info(f"[Cold Start] Using similarity prediction (sales count: {sales_records_count})")
        
        sim_metrics = predictor_engine.predict_cold_start(
            target_product_id=target_product_id,
            df=df_preprocessed,
            model=model,
            features=features,
            retailer_company=retailer_company,
            store_location=store_location
        )
        
        opt_price = sim_metrics["optimal_price"]
        exp_demand = sim_metrics["expected_demand"]
        elast = sim_metrics["elasticity"]
        
        identity_features = ["retailer_encoded", "city_encoded", "retailer_strength", "city_strength"]
        if not any(f in features for f in identity_features):
            exp_demand = exp_demand * target_ret_strength * target_loc_strength
            
        price_range = np.linspace(opt_price * PRICE_RANGE_MULTIPLIERS["min_multiplier"], opt_price * PRICE_RANGE_MULTIPLIERS["max_multiplier"], PRICE_RANGE_MULTIPLIERS["num_candidates"])
        demand_points = exp_demand * (price_range / opt_price) ** min(0.0, elast)
        df_curve = pd.DataFrame({"price": price_range, "demand": demand_points})
        df_curve = calculate_revenue(df_curve)
        
        print("Prediction mode:", mode)
        print("Optimal price:", round(opt_price, 2))
        print("Expected demand:", round(exp_demand, 2))
        print("Elasticity:", round(elast, 3))
        
        if generate_plot:
            plot_curve(df_curve, target_product_id)
            
        store_prediction_history(target_product_id, opt_price, exp_demand, elast, "similar_products")
        
        return {
            "optimal_price": opt_price,
            "expected_demand": exp_demand,
            "elasticity": elast,
            "prediction_source": "similar_products",
            "similar_products_used": sim_metrics["similar_products_used"],
            "sales_history_count": sales_history_count,
            "engine2_confidence": engine2_confidence
        }

    # 2. Extract base history context for Hybrid/Normal modes
    if df_product_localized.empty:
        df_product_localized = df_product
    
    base_row = df_product_localized.iloc[-1].to_dict()
    base_row["retailer_strength"] = target_ret_strength
    base_row["city_strength"] = target_loc_strength

    # Generate candidate prices specifically for this product
    price_range = np.linspace(
        df_product_localized["price"].min() * PRICE_RANGE_MULTIPLIERS["min_multiplier"],
        df_product_localized["price"].max() * PRICE_RANGE_MULTIPLIERS["max_multiplier"],
        PRICE_RANGE_MULTIPLIERS["num_candidates"]
    )

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
        logger.info(f"[Hybrid] Running hybrid prediction (sales count: {sales_records_count})")

        sim_metrics = predictor_engine.predict_cold_start(
            target_product_id=target_product_id,
            df=df_preprocessed,
            model=model,
            features=features,
            retailer_company=retailer_company,
            store_location=store_location
        )

        hybrid_metrics = hybrid_prediction(hist_metrics, sim_metrics, sales_records_count)
        
        opt_price = hybrid_metrics["optimal_price"]
        exp_demand = hybrid_metrics["expected_demand"]
        elast = hybrid_metrics["elasticity"]

        price_range = np.linspace(opt_price * PRICE_RANGE_MULTIPLIERS["min_multiplier"], opt_price * PRICE_RANGE_MULTIPLIERS["max_multiplier"], PRICE_RANGE_MULTIPLIERS["num_candidates"])
        demand_points = exp_demand * (price_range / opt_price) ** min(0.0, elast)
        df_curve = pd.DataFrame({"price": price_range, "demand": demand_points})
        df_curve = calculate_revenue(df_curve)

        print("Prediction mode:", mode)
        print("Optimal price:", round(opt_price, 2))
        print("Expected demand:", round(exp_demand, 2))
        print("Elasticity:", round(elast, 3))

        if generate_plot:
            plot_curve(df_curve, target_product_id)

        store_prediction_history(target_product_id, opt_price, exp_demand, elast, "hybrid")

        return {
            "optimal_price": opt_price,
            "expected_demand": exp_demand,
            "elasticity": elast,
            "prediction_source": "hybrid",
            "similar_products_used": hybrid_metrics["similar_products_used"],
            "sales_history_count": sales_history_count,
            "engine2_confidence": engine2_confidence
        }

    # 4. Normal Mode
    logger.info(f"[Normal] Using historical sales prediction (sales count: {sales_records_count})")

    opt_price = hist_metrics["optimal_price"]
    exp_demand = hist_metrics["expected_demand"]
    elast = hist_metrics["elasticity"]

    print("Prediction mode:", mode)
    print("Optimal price:", round(opt_price, 2))
    print("Expected demand:", round(exp_demand, 2))
    print("Elasticity:", round(elast, 3))

    if generate_plot:
        plot_curve(df_curve_hist, target_product_id)

    store_prediction_history(target_product_id, opt_price, exp_demand, elast, "historical_sales")

    return {
        "optimal_price": opt_price,
        "expected_demand": exp_demand,
        "elasticity": elast,
        "prediction_source": "historical_sales",
        "similar_products_used": [],
        "sales_history_count": sales_history_count,
        "engine2_confidence": engine2_confidence
    }
