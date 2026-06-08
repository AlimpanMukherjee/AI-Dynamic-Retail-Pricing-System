# Pricing System Implementation Flow

## 1. Purpose

This project implements a coordinated pricing pipeline that calculates a final optimized price for a product-store-retailer context.

The system is built around three main pricing layers:

```text
Layer 1: Specialist Pricing Engines
    -> Layer 2: Dynamic Engine Weighting
        -> Layer 3: Candidate Price Optimization
            -> Final Optimized Price
```

It also contains onboarding validation utilities and a similarity-based cold-start path for products with limited sales history.

## 2. User-Level Inputs

The main pipeline starts from `run_coordinated_pricing()` in `backend/pipeline/pricing_pipeline.py`.

The current user/request inputs are:

```text
product_id
retailer_company
store_location
business_context.retailer_type
business_context.business_strategy
business_context.region
market_trend_score
currency_fluctuation_factor
target_supplier_id
```

The practical minimum for normal use is:

```text
product_id
retailer_company
store_location
retailer_type
business_strategy
region
```

The remaining values have defaults:

```text
market_trend_score = 0.5
currency_fluctuation_factor = 1.0
target_supplier_id = None
```

## 3. Runtime Data Sources

Runtime paths are resolved through `backend/config.py`.

By default, non-test runtime uses:

```text
customer_data/products.csv
customer_data/procurement.csv
customer_data/sales.csv
customer_data/inventory.csv
customer_data/competitors.csv
```

When tests run with `PRICING_TESTING=true` or `PYTEST_CURRENT_TEST`, the config routes to:

```text
datasets/products.csv
datasets/procurement.csv
datasets/sales.csv
datasets/inventory.csv
datasets/competitors.csv
```

Layer 2 model training still uses:

```text
datasets/layer2_training_data.csv
backend/layer2/layer2_model.pkl
```

## 4. Main Pipeline

File:

```text
backend/pipeline/pricing_pipeline.py
```

Main function:

```python
run_coordinated_pricing(...)
```

The pipeline performs these steps:

```text
1. Resolve data paths from config.
2. Build default business context if none is provided.
3. Run Engine 1: procurement and supply risk.
4. Run Engine 2: demand elasticity and demand optimum.
5. Run Engine 3: inventory dynamics.
6. Run Engine 4: competitor market intelligence.
7. Assemble all Layer 1 outputs into pricing_state.
8. Convert pricing_state + business_context into a Layer 2 feature vector.
9. Predict dynamic weights for E1, E2, E3, E4 using the saved Layer 2 model.
10. Run Layer 3 optimization using pricing_state and predicted weights.
11. Return final price, confidence, score breakdown, decision summary, and explanation.
```

## 5. Layer 1: Specialist Engines

Layer 1 produces the raw pricing intelligence.

### E1: Procurement and Supply Risk

File:

```text
backend/layer1/engine1.py
```

Inputs:

```text
products.csv
procurement.csv
product_id
target_supplier_id
currency_fluctuation_factor
```

Main outputs:

```text
true_landed_cost
cost_volatility
supply_risk
minimum_safe_price
```

Main formula:

```text
minimum_safe_price =
    true_landed_cost
    + risk_buffer
    + category_minimum_margin
```

### E2: Demand Elasticity

File:

```text
backend/layer1/engine2.py
```

Inputs:

```text
sales.csv
products.csv
inventory.csv
product_id
retailer_company
store_location
```

Main outputs:

```text
optimal_price
expected_demand
elasticity
prediction_source
similar_products_used
```

Engine 2 trains an XGBoost demand model at runtime, generates a demand curve, calculates revenue at candidate prices, and selects the revenue-maximizing price.

It has three modes:

```text
cold_start: 0-30 localized sales records
hybrid:     31-100 localized sales records
normal:     more than 100 localized sales records
```

Cold-start and hybrid modes use product similarity to borrow pricing intelligence from similar products.

### E3: Inventory Dynamics

File:

```text
backend/layer1/engine3.py
```

Inputs:

```text
inventory.csv
product_id
retailer_company
store_location
```

Main outputs:

```text
stockout_risk
inventory_pressure
urgency_score
recommended_multiplier
```

Inventory pressure is calculated from:

```text
net_stock = current_stock - reserved_stock
```

Then:

```text
net_stock > reorder_point  -> positive overstock pressure
net_stock = reorder_point  -> balanced pressure of 0
net_stock < reorder_point  -> negative understock pressure
```

The recommended multiplier lowers price when overstocked and raises price when understocked.

### E4: Competitor Market Intelligence

File:

```text
backend/layer1/engine4.py
```

Inputs:

```text
competitors.csv
sales.csv
product_id
store_location as market_region
market_trend_score
```

Main outputs:

```text
competitor_band
market_pressure
competitive_gap
recommended_multiplier
```

Market pressure blends:

```text
competitor promotion rate
average competitor rating
market trend score
```

## 6. Layer 2: Dynamic Weighting

Layer 2 decides how important each Layer 1 engine should be for the current pricing context.

### Feature Builder

File:

```text
backend/layer2/feature_builder.py
```

It converts `pricing_state` plus `business_context` into this ordered 11-value vector:

```text
minimum_safe_price
supply_risk
optimal_price
elasticity
inventory_pressure
urgency_score
market_pressure
competitive_gap
retailer_type_encoded
business_strategy_encoded
region_encoded
```

### Weight Prediction

File:

```text
backend/layer2/predict_weights.py
```

It loads:

```text
backend/layer2/layer2_model.pkl
```

Then predicts:

```text
E1_weight
E2_weight
E3_weight
E4_weight
```

The raw model outputs are clipped and normalized so the weights sum to 1.0.

### Training Data Generation

File:

```text
backend/layer2/generate_training_data.py
```

It samples inventory rows, runs all Layer 1 engines, builds feature vectors, and creates target weights using heuristic rules.

Output:

```text
datasets/layer2_training_data.csv
```

### Model Training

File:

```text
backend/layer2/train_layer2.py
```

It trains a multi-output XGBoost regressor to predict all four engine weights.

Output:

```text
backend/layer2/layer2_model.pkl
```

## 7. Layer 3: Candidate Optimization

Layer 3 turns Layer 1 signals and Layer 2 weights into one final price.

### Optimizer

File:

```text
backend/layer3/optimizer.py
```

Main class:

```python
PriceOptimizer
```

Current pipeline configuration:

```python
PriceOptimizer({"candidate_step_size": 0.15})
```

The optimizer orchestrates:

```text
candidate generation
constraint filtering
candidate scoring
final price selection
```

### Candidate Generation

File:

```text
backend/layer3/candidate_generator.py
```

Candidate prices are generated around anchors:

```text
E1 minimum_safe_price
E2 optimal_price
E4 competitor band min
E4 competitor band max
E4 competitor band midpoint
E2 optimal_price * E3 recommended_multiplier
E2 optimal_price * E4 recommended_multiplier
```

The current step size is `0.15`, so candidates can be decimal prices such as:

```text
10.50
10.65
10.80
```

### Constraints

File:

```text
backend/layer3/constraints.py
```

It rejects candidates that violate rules such as:

```text
below procurement safety floor
below configured minimum price
below configured minimum margin
above max safe multiplier
above configured maximum price
```

If all candidates fail, it falls back to `minimum_safe_price`.

### Scoring

File:

```text
backend/layer3/scoring_engine.py
```

Each valid price receives:

```text
procurement_score
elasticity_score
inventory_score
market_score
final_score
```

Final score:

```text
final_score =
    E1_weight * procurement_score
    + E2_weight * elasticity_score
    + E3_weight * inventory_score
    + E4_weight * market_score
```

### Final Selection

File:

```text
backend/layer3/final_price_selector.py
```

It selects the candidate with the highest final score and returns:

```text
final_price
confidence
selected_price_score
winning_candidate
price_breakdown
decision_summary
explanation
```

## 8. Cold-Start Similarity

Files:

```text
backend/similarity/product_similarity_engine.py
backend/similarity/cold_start_predictor.py
backend/similarity/similarity_utils.py
```

This module helps Engine 2 when a product has too little sales history.

Similarity is based on:

```text
category match
subcategory match
pack size similarity
```

The cold-start predictor finds similar products, generates demand curves for those products, and uses similarity-weighted averages for:

```text
optimal_price
expected_demand
elasticity
```

## 9. Onboarding

Files:

```text
backend/onboarding/validators.py
backend/onboarding/upload_products.py
backend/onboarding/upload_procurement.py
backend/onboarding/upload_sales.py
backend/onboarding/upload_inventory.py
backend/onboarding/upload_competitors.py
```

These scripts validate uploaded CSV files and save them into `customer_data/`.

Validators check required columns, null values, duplicates, negative stock, negative sales, and invalid prices/costs.

## 10. End-to-End Flow

```text
User selects product and business context
        |
        v
run_coordinated_pricing()
        |
        v
Resolve customer data paths
        |
        v
Run Layer 1 engines
        |
        |-- E1: procurement floor and supply risk
        |-- E2: demand optimum and elasticity
        |-- E3: inventory pressure and urgency
        `-- E4: competitor pressure and market gap
        |
        v
Build pricing_state
        |
        v
Build 11-feature Layer 2 vector
        |
        v
Predict E1/E2/E3/E4 weights
        |
        v
Generate price candidates
        |
        v
Filter unsafe candidates
        |
        v
Score candidates using weighted engine scores
        |
        v
Select highest-scoring candidate
        |
        v
Return final optimized price and explanation
```

## 11. Current Validation Status

Checked:

```text
python -m compileall backend
```

Result:

```text
Backend compiled successfully.
```

Checked:

```text
python -m backend.pipeline.pricing_pipeline
```

Result:

```text
Pipeline completed successfully and returned a final optimized price.
```

Checked:

```text
pytest -q
```

Initial result:

```text
Import collection failed unless PYTHONPATH includes the project root.
```

With project root on `PYTHONPATH`:

```text
19 tests passed
2 tests errored because pytest could not access its temp directory
```

The remaining test errors appear environment/permission-related, not direct pricing logic failures.
