import os
import pandas as pd
import numpy as np

# Import Layer 1 engines
from backend.layer1 import engine1
from backend.layer1 import engine2
from backend.layer1 import engine3
from backend.layer1 import engine4

# Import Layer 2 modules
from backend.layer2.feature_builder import build_feature_vector
from backend.layer2.predict_weights import predict_engine_weights

# Import Layer 3 modules
from backend.layer3.optimizer import PriceOptimizer

def run_coordinated_pricing(
    product_id="SKU_1000",
    retailer_company=None,
    store_location=None,
    business_context=None,
    market_trend_score=0.5,
    currency_fluctuation_factor=1.0,
    target_supplier_id=None
):
    """
    Executes the end-to-end pricing pipeline:
    1. Executes E1, E2, E3, and E4 engines.
    2. Builds a unified pricing state.
    3. Builds the dynamic feature vector.
    4. Predicts the dynamic coordinated engine weights.
    
    Parameters:
        product_id (str): SKU to evaluate.
        retailer_company (str): Retailer name (e.g. "Reliance Retail").
        store_location (str): Store city (e.g. "Bengaluru").
        business_context (dict): Business environment overrides.
        market_trend_score (float): Macro market trend factor.
        currency_fluctuation_factor (float): Exchange rate volatility factor.
        target_supplier_id (str): Overrides default primary supplier search.
        
    Returns:
        dict: Coordinated pricing report containing:
              - product_id
              - pricing_state (unified engine metrics)
              - feature_vector (flat ML inputs)
              - coordinated_weights (predicted weights)
    """
    import backend.config as cfg
    products_csv = cfg.CUSTOMER_PRODUCTS_PATH
    procurement_csv = cfg.CUSTOMER_PROCUREMENT_PATH
    sales_csv = cfg.CUSTOMER_SALES_PATH
    inventory_csv = cfg.CUSTOMER_INVENTORY_PATH
    competitors_csv = cfg.CUSTOMER_COMPETITOR_PATH

    # 1. Fallback to default business context if not provided
    if business_context is None:
        business_context = {
            "retailer_type": "standard",
            "business_strategy": "balanced",
            "region": "urban"
        }

    # 2. Run Engine 1: Procurement & Supply Risk
    e1_output = engine1.run_pipeline(
        products_csv_path=products_csv,
        procurement_csv_path=procurement_csv,
        target_product_id=product_id,
        target_supplier_id=target_supplier_id,
        currency_fluctuation_factor=currency_fluctuation_factor
    )

    # 3. Run Engine 2: Demand Elasticity
    e2_output = engine2.run_pipeline(
        sales_csv_path=sales_csv,
        target_product_id=product_id,
        products_csv_path=products_csv,
        inventory_csv_path=inventory_csv,
        retailer_company=retailer_company,
        store_location=store_location
    )

    # 4. Run Engine 3: Inventory Dynamics
    e3_output = engine3.run_pipeline(
        csv_path=inventory_csv,
        target_product_id=product_id,
        retailer_company=retailer_company,
        store_location=store_location
    )

    # 5. Run Engine 4: Competitor Market Intelligence
    # Map store_location to market_region for engine 4
    e4_output = engine4.run_pipeline(
        competitors_csv=competitors_csv,
        sales_csv=sales_csv,
        target_product_id=product_id,
        market_region=store_location,
        market_trend_score=market_trend_score
    )

    # 6. Assemble Unified Pricing State
    pricing_state = {
        "product_id": product_id,
        "E1": e1_output,
        "E2": e2_output,
        "E3": e3_output,
        "E4": e4_output
    }

    # 7. Convert nested pricing state and context into feature vector
    feature_vector = build_feature_vector(pricing_state, business_context)

    # 8. Predict coordinated weights from the feature vector using the Layer 2 model
    coordinated_weights = predict_engine_weights(feature_vector)

    # 9. Execute Layer 3 Price Optimization
    optimizer = PriceOptimizer({"candidate_step_size": 0.15})
    optimization_report = optimizer.optimize_price(pricing_state, coordinated_weights)

    return {
        "product_id": product_id,
        "pricing_state": pricing_state,
        "feature_vector": feature_vector.tolist(),
        "coordinated_weights": coordinated_weights,
        
        # Layer 3 Optimization outputs
        "final_price": optimization_report["final_price"],
        "confidence": optimization_report["confidence"],
        "selected_price_score": optimization_report["selected_price_score"],
        "winning_candidate": optimization_report["winning_candidate"],
        "price_breakdown": optimization_report["price_breakdown"],
        "decision_summary": optimization_report["decision_summary"],
        "explanation": optimization_report["explanation"]
    }

if __name__ == "__main__":
    # Test end-to-end pricing pipeline run
    import json
    
    sku = "SKU_1056"
    retailer = "Reliance Retail"
    store = "Hyderabad"
    
    context = {
        "retailer_type": "standard",
        "business_strategy": "balanced",
        "region": "urban"
    }
    
    print("\n========================================================")
    print("STARTING COORDINATED PIPELINE RUN (E1+E2+E3+E4 -> L2)")
    print("========================================================")
    print(f"Target SKU:      {sku}")
    print(f"Retailer:        {retailer}")
    print(f"Location:        {store}")
    print(f"Context:         {context}")
    
    result = run_coordinated_pricing(
        product_id=sku,
        retailer_company=retailer,
        store_location=store,
        business_context=context
    )
    
    print("\n========================================================")
    print("COORDINATED PIPELINE REPORT")
    print("========================================================")
    print("Unified Pricing State:")
    print(json.dumps(result["pricing_state"], indent=2))
    
    print("\nFeature Vector:")
    print(result["feature_vector"])
    
    print("\nCoordinated Engine Weights:")
    for eng_weight, val in result["coordinated_weights"].items():
        print(f"  {eng_weight:<10}: {val * 100:.2f}%")
        
    print("\n========================================================")
    print("LAYER 3 FINAL PRICE OPTIMIZATION DECISION")
    print("========================================================")
    print(f"Winning Candidate Price:  ${result['winning_candidate']:.2f}")
    print(f"Final Optimized Price:    ${result['final_price']:.2f}")
    print(f"Selection Score (Conf):   {result['selected_price_score']:.4f} ({result['confidence']:.2%})")
    
    print("\nPrice Score Breakdown:")
    for score_name, score_val in result["price_breakdown"].items():
        print(f"  - {score_name:<18}: {score_val:.4f}")
        
    print("\nDecision Qualitative Summary:")
    for key, val in result["decision_summary"].items():
        print(f"  - {key:<18}: {val.upper()}")
        
    print("\nStakeholder Explanation:")
    print(result["explanation"])
    print("========================================================")
