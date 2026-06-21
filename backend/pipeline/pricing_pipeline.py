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
    target_supplier_id=None,
    event_active=False,
    event_type="Other",
    attendance=0,
    distance_km=2.0,
    duration_hours=4.0
):
    """
    Executes the end-to-end pricing pipeline:
    1. Loads target product's base price from catalog.
    2. Executes E1, E2, E3, E4, and E5 specialist engines.
    3. Builds a unified pricing state.
    4. Builds the dynamic feature vector.
    5. Predicts the dynamic coordinated engine weights.
    6. Runs Layer 3 optimization.
    """
    import backend.config as cfg
    products_csv = cfg.CUSTOMER_PRODUCTS_PATH
    procurement_csv = cfg.CUSTOMER_PROCUREMENT_PATH
    sales_csv = cfg.CUSTOMER_SALES_PATH
    inventory_csv = cfg.CUSTOMER_INVENTORY_PATH
    competitors_csv = cfg.CUSTOMER_COMPETITOR_PATH

    # Log inventory source and target SKU stock levels
    import logging
    logger = logging.getLogger("pricing_system.pipeline")
    from backend.inventory.inventory_repository import get_product_inventory, get_current_inventory_path
    
    inv_path = get_current_inventory_path()
    prod_inv = get_product_inventory(product_id)
    current_stock = prod_inv.get("current_stock", 0)
    logger.info(f"Pricing Coordinated Pipeline execution started for Product: {product_id}. Inventory Path: {inv_path}. Current Stock: {current_stock}")

    # Load target product base_market_price early to set as current_price
    current_price = 0.0
    try:
        df_prod = pd.read_csv(products_csv)
        product_row = df_prod[df_prod["product_id"].astype(str).str.strip() == str(product_id).strip()]
        if not product_row.empty:
            current_price = float(product_row.iloc[0].get("base_market_price", 0.0))
    except Exception as e:
        print(f"Error loading base_market_price for current_price: {str(e)}")

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
    e4_output = engine4.run_pipeline(
        competitors_csv=competitors_csv,
        sales_csv=sales_csv,
        target_product_id=product_id,
        market_region=store_location,
        market_trend_score=market_trend_score
    )

    # 6. Run Engine 5: Event Intelligence
    from backend.engines.event_engine import run_pipeline as run_event_engine
    e5_output = run_event_engine(
        event_active=event_active,
        event_type=event_type,
        attendance=attendance,
        distance_km=distance_km,
        duration_hours=duration_hours
    )

    # Assemble Unified Pricing State
    pricing_state = {
        "product_id": product_id,
        "current_price": current_price,
        "event_active": event_active,
        "event_type": event_type,
        "attendance": attendance,
        "distance_km": distance_km,
        "duration_hours": duration_hours,
        "E1": e1_output,
        "E2": e2_output,
        "E3": e3_output,
        "E4": e4_output,
        "E5": e5_output
    }

    # 7. Convert nested pricing state and context into feature vector
    feature_vector = build_feature_vector(pricing_state, business_context)

    # 8. Predict coordinated weights from the feature vector using the Layer 2 model
    coordinated_weights = predict_engine_weights(feature_vector, event_active=event_active)

    # 9. Execute Layer 3 Price Optimization
    optimizer = PriceOptimizer({"candidate_step_size": 0.15})
    optimization_report = optimizer.optimize_price(pricing_state, coordinated_weights)

    pipeline_result = {
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
        "explanation": optimization_report["explanation"],
        "price_journey": optimization_report.get("price_journey"),
        "price_confidence": optimization_report.get("price_confidence")
    }

    # Automatically persist pricing decision to pricing history
    try:
        from frontend.services.pricing_history_service import save_pricing_decision
        journey = optimization_report.get("price_journey", {})
        conf_data = optimization_report.get("price_confidence", {})
        save_pricing_decision(
            product_id=product_id,
            retailer=retailer_company or "N/A",
            location=store_location or "N/A",
            engine1_price=pricing_state["E1"].get("minimum_safe_price", 0.0),
            engine2_price=pricing_state["E2"].get("optimal_price", 0.0),
            engine3_multiplier=pricing_state["E3"].get("recommended_multiplier", 1.0),
            engine4_multiplier=pricing_state["E4"].get("recommended_multiplier", 1.0),
            final_price=optimization_report["final_price"],
            confidence=optimization_report["confidence"],
            supply_risk=pricing_state["E1"].get("supply_risk", 0.0),
            inventory_pressure=pricing_state["E3"].get("inventory_pressure", 0.0),
            market_pressure=pricing_state["E4"].get("market_pressure", 0.0),
            event_active=event_active,
            event_type=event_type,
            attendance=attendance,
            event_score=e5_output.get("event_score", 0.0),
            event_influence=coordinated_weights.get("E5_weight", 0.0),
            distance_km=distance_km,
            duration_hours=duration_hours,
            impact_level=e5_output.get("impact_level", "LOW"),
            base_price=journey.get("procurement_floor"),
            e2_contribution_raw=journey.get("demand_effect_raw"),
            e2_contribution=journey.get("demand_effect"),
            e3_contribution_raw=journey.get("inventory_effect_raw"),
            e3_contribution=journey.get("inventory_effect"),
            e4_contribution_raw=journey.get("competitor_effect_raw"),
            e4_contribution=journey.get("competitor_effect"),
            e5_contribution_raw=journey.get("event_effect_raw"),
            e5_contribution=journey.get("event_effect"),
            total_uplift=journey.get("total_uplift"),
            confidence_score=conf_data.get("confidence_score"),
            confidence_level=conf_data.get("confidence_level")
        )
    except Exception as e:
        # Graceful error handling - avoid crashing pipeline
        import logging
        logging.getLogger("pricing_system.pipeline").error(f"Error saving pricing history: {str(e)}")

    # Automatically generate any alerts triggered by pipeline outputs
    try:
        from backend.alerts.alert_engine import generate_alerts
        generate_alerts(product_id, pipeline_result)
    except Exception as e:
        import logging
        logging.getLogger("pricing_system.pipeline").error(f"Error generating alerts: {str(e)}")

    return pipeline_result

if __name__ == "__main__":
    # Test end-to-end pricing pipeline run
    import sys
    import json
    
    # Reconfigure stdout to support unicode/utf-8 encoding in Windows terminal
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
            
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
    print("\nPrice Journey:")
    print(json.dumps(result.get("price_journey"), indent=2))
    print("\nPrice Confidence:")
    print(json.dumps(result.get("price_confidence"), indent=2))
    print("========================================================")
