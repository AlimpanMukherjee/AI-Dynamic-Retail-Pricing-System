import os
import io
import sys
import contextlib
import pandas as pd
import numpy as np

# Import Layer 1 engines
from backend.layer1 import engine1
from backend.layer1 import engine2
from backend.layer1 import engine3
from backend.layer1 import engine4

# Import Layer 2 modules
from backend.layer2.feature_builder import build_feature_vector, get_feature_names
from backend.layer2.heuristic_weight_generator import generate_heuristic_weights

# Simple dictionary cache to avoid retraining Engine 2's XGBoost model repeatedly for the same SKU
_E2_CACHE = {}

def cached_run_e2(sales_csv, product_id, retailer_company, store_location):
    """
    Executes Engine 2 and caches the result.
    Since Engine 2's output depends on the SKU, retailer, and location context,
    we key the cache on a 3-tuple to avoid collisions and support localized demand.
    """
    cache_key = (product_id, retailer_company, store_location)
    if cache_key not in _E2_CACHE:
        # Redirect stdout to suppress print logs
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            _E2_CACHE[cache_key] = engine2.run_pipeline(
                sales_csv_path=sales_csv,
                target_product_id=product_id,
                retailer_company=retailer_company,
                store_location=store_location
            )
    return _E2_CACHE[cache_key]

def main():
    print("Starting Layer 2 training data generation...")
    
    # Define paths
    products_csv = "datasets/products.csv"
    procurement_csv = "datasets/procurement.csv"
    sales_csv = "datasets/sales.csv"
    inventory_csv = "datasets/inventory.csv"
    competitors_csv = "datasets/competitors.csv"
    output_csv = "datasets/layer2_training_data.csv"

    # Verify paths exist
    for path in [products_csv, procurement_csv, sales_csv, inventory_csv, competitors_csv]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing required dataset: {path}")

    # Load inventory records to get real combinations of product_id, retailer, and location
    df_inv = pd.read_csv(inventory_csv)
    
    # To keep generation fast and representative, we sample up to 200 inventory rows
    sample_size = min(200, len(df_inv))
    df_samples = df_inv.sample(n=sample_size, random_state=42)
    
    # We will overlay 4 different simulated business contexts on each inventory record
    # to teach the ML model how different strategies affect pricing weights.
    simulated_contexts = [
        {"retailer_type": "discount", "business_strategy": "volume_first", "region": "urban"},
        {"retailer_type": "standard", "business_strategy": "balanced", "region": "suburban"},
        {"retailer_type": "premium", "business_strategy": "margin_first", "region": "urban"},
        {"retailer_type": "standard", "business_strategy": "margin_first", "region": "rural"}
    ]

    records = []
    
    success_count = 0
    error_count = 0

    print(f"Running {sample_size} scenarios with {len(simulated_contexts)} contexts each (total {sample_size * len(simulated_contexts)} records)...")
    
    for idx, row in df_samples.iterrows():
        product_id = row["product_id"]
        retailer = row["retailer_company"]
        location = row["store_location"]
        
        # Run specialist engines inside a suppressed output block
        try:
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                # Run E1 (Procurement)
                e1_out = engine1.run_pipeline(
                    products_csv_path=products_csv,
                    procurement_csv_path=procurement_csv,
                    target_product_id=product_id
                )
                
                # Run E2 (Elasticity) - Cached with retailer and location
                e2_out = cached_run_e2(sales_csv, product_id, retailer, location)
                
                # Run E3 (Inventory)
                e3_out = engine3.run_pipeline(
                    csv_path=inventory_csv,
                    target_product_id=product_id,
                    retailer_company=retailer,
                    store_location=location
                )
                
                # Run E4 (Market)
                e4_out = engine4.run_pipeline(
                    competitors_csv=competitors_csv,
                    sales_csv=sales_csv,
                    target_product_id=product_id,
                    market_region=location
                )
            
            # Combine into unified pricing state
            pricing_state = {
                "product_id": product_id,
                "E1": e1_out,
                "E2": e2_out,
                "E3": e3_out,
                "E4": e4_out
            }

            # Generate training inputs and labels for each context
            import copy
            for c_idx, context in enumerate(simulated_contexts):
                state_copy = copy.deepcopy(pricing_state)
                
                # To train the XGBoost model on extreme scenarios, we inject synthetic extreme
                # states for a subset of the generated data. This allows the model to learn the
                # heuristic thresholds and generalize correctly under extreme business events.
                if c_idx == 0:
                    # Inject severe procurement risk (supply_risk > 0.85)
                    state_copy["E1"]["supply_risk"] = float(np.random.uniform(0.86, 0.99))
                elif c_idx == 1:
                    # Inject severe inventory crisis (abs(pressure) > 0.8, high urgency)
                    state_copy["E3"]["inventory_pressure"] = float(np.random.choice([-1.0, 1.0]))
                    state_copy["E3"]["urgency_score"] = 1.0
                elif c_idx == 2:
                    # Inject major competitor gap (abs(gap) > 1.5)
                    state_copy["E4"]["competitive_gap"] = float(np.random.choice([
                        np.random.uniform(-3.0, -1.5),
                        np.random.uniform(1.5, 3.0)
                    ]))
                # c_idx == 3 remains completely unmodified as a baseline sample

                # Get feature vector
                features = build_feature_vector(state_copy, context)
                
                # Get heuristic target weights
                targets = generate_heuristic_weights(state_copy, context)
                
                record = {
                    "product_id": product_id,
                    "retailer_company": retailer,
                    "store_location": location,
                    "retailer_type": context["retailer_type"],
                    "business_strategy": context["business_strategy"],
                    "region": context["region"]
                }
                
                # Map features to column names
                feature_names = get_feature_names()
                for name, val in zip(feature_names, features):
                    record[name] = val
                    
                # Map target weights
                record["target_E1_weight"] = targets[0]
                record["target_E2_weight"] = targets[1]
                record["target_E3_weight"] = targets[2]
                record["target_E4_weight"] = targets[3]
                
                records.append(record)
                
            success_count += 1
            if success_count % 20 == 0:
                print(f"Processed {success_count}/{sample_size} product-store nodes...")
                
        except Exception as e:
            error_count += 1
            # Suppressed exceptions during generation to prevent total pipeline crash
            continue

    print(f"Data generation complete. Successful nodes: {success_count}, Errors: {error_count}")
    
    if len(records) == 0:
        print("Error: No training data generated.")
        return

    df_out = pd.DataFrame(records)
    df_out.to_csv(output_csv, index=False)
    print(f"Saved {len(df_out)} training rows to: {output_csv}")

if __name__ == "__main__":
    main()
