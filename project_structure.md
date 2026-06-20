# Project Structure

```text
pricing-system/
|-- app.py                              # Main entry point for the Streamlit application
|-- project_overview.md                 # System overview and architectural guidelines
|-- project_structure.md                # Project directory tree and module explanations
|-- requirement.txt                     # Package dependencies
|-- requirements.txt                    # Duplicate package dependencies file
|-- backend/
|   |-- config.py                       # Global path mapping and environment configurations
|   |-- alerts/
|   |   |-- alert_engine.py             # Generates business and stock level warnings
|   |   `-- test_alerts.py              # Unit tests for the alert system
|   |-- onboarding/
|   |   |-- validators.py               # Ingestion CSV schema and row validator logic
|   |   `-- test_validators.py          # Unit tests for the onboarding validator
|   |-- data_ingestion/
|   |   `-- ingest_data.py              # Ingests sales and competitor data
|   |-- inventory/
|   |   |-- inventory_ingestion.py      # Operations logic for stock level tracking
|   |   `-- test_inventory_ops.py       # Unit tests for current and historic stock logic
|   |-- similarity/
|   |   |-- cold_start_predictor.py     # Fallback demand estimation for new items
|   |   `-- test_cold_start.py          # Unit tests for cold start similarity
|   |-- retraining/
|   |   |-- retrain_model.py            # Workflow for training and activating models
|   |   `-- test_retraining.py          # Unit tests for XGBoost model retraining
|   |-- engines/                        # Specialist core engines
|   |   |-- event_engine.py             # [NEW] E5 Event Intelligence Engine
|   |   `-- test_event_engine.py        # [NEW] E5 Event Intelligence Engine unit tests
|   |-- layer1/                         # Core Specialists Pricing Engines
|   |   |-- engine1.py                  # Calculates procurement floor and supply risk
|   |   |-- engine2/                    # Sub-modules for Engine 2 demand forecasting
|   |   |-- engine2.py                  # Models demand elasticity and optimal price
|   |   |-- engine3.py                  # Models inventory pressure & stockout urgency
|   |   |-- engine4.py                  # Evaluates competitor pricing and region gaps
|   |   `-- shared_utils.py             # Common math, CSV load, and encoding helpers
|   |-- layer2/                         # Dynamic Coordinated Weighting
|   |   |-- feature_builder.py          # Builds XGBoost-ready ML feature vectors
|   |   |-- generate_training_data.py   # Generates simulated states for model training
|   |   |-- heuristic_weight_generator.py # Baseline expert heuristics weight generator
|   |   |-- layer2_model.pkl            # Serialized XGBoost multi-output model
|   |   |-- predict_weights.py          # Predicts E1-E5 weights using the model
|   |   `-- train_layer2.py             # Model fitting script
|   |-- layer3/                         # Price Arbitration & Grid Scoring
|   |   |-- candidate_generator.py      # Generates candidate prices around anchors
|   |   |-- constraints.py              # Filters candidates by safety thresholds
|   |   |-- scoring_engine.py           # Evaluates candidate scores with weights
|   |   |-- final_price_selector.py     # Arbitrates and chooses winning candidate
|   |   `-- optimizer.py                # Layer 3 optimizer coordinator orchestrator
|   `-- pipeline/
|       `-- pricing_pipeline.py         # Runs Layers 1, 2, and 3 coordinated pipeline
|-- frontend/                           # Streamlit Web App Interface
|   |-- components/
|   |   |-- metrics.py                  # UI metrics styling
|   |   |-- sidebar.py                  # Sidebar navigation menu
|   |   `-- tables.py                   # Styled custom dataframe tables
|   |-- pages/
|   |   |-- alerts.py                   # Stock warnings alerts dashboard
|   |   |-- dashboard.py                # Main inventory health statistics dashboard
|   |   |-- inventory_upload.py         # CSV inventory ingestion page
|   |   |-- model_management.py         # ML retraining dashboard
|   |   |-- pricing_history.py          # Audit history and Event Uplift dashboard
|   |   |-- product_search.py           # Catalog search panel
|   |   |-- run_pricing.py              # Optimizations executor form page
|   |   `-- sales_upload.py             # Historical sales upload manager
|   `-- services/
|       |-- alert_service.py            # Interfaces with alert data
|       |-- inventory_service.py        # Interfaces with stock details
|       |-- pricing_history_service.py  # Handles decision history persistence
|       |-- pricing_service.py          # Runs the coordinator service wrapper
|       |-- retraining_service.py       # Interfaces with registry parameters
|       `-- sales_service.py            # Interfaces with sales data summaries
|-- datasets/                           # Persistent Catalog & Storage CSVs
|   |-- competitors.csv                 # Competitor price snapshots
|   |-- inventory.csv                   # Historical initial stock details
|   |-- layer2_training_data.csv        # Dynamic coordinated weighting training data
|   |-- procurement.csv                 # Supplier metrics and landed costs
|   |-- products.csv                    # Product catalog master list
|   `-- sales.csv                       # Store sales logs
`-- customer_data/                      # Customer runtime operational data
```

---

## Folder Descriptions

### backend/engines/
- `event_engine.py`: Dynamic event intelligence pricing engine (E5) which quantifies demand surges near store locations and adjusts pricing weights.
- `test_event_engine.py`: Unit tests mapping event metrics, classification thresholds, and inactive state fallbacks.

### backend/layer1/
- `engine1.py`: Computes minimum safe margins based on landed cost and supply risk.
- `engine2.py`: Fits and runs local demand curves to identify optimal price.
- `engine3.py`: Evaluates on-hand levels to recommend stock clearing multipliers.
- `engine4.py`: Matches price against competitor bands.

### backend/layer2/
- `feature_builder.py`: Packs engine outputs and business goals into a structured array.
- `predict_weights.py`: Trims feature inputs to prevent XGBoost mismatch and runs meta-weights prediction.

### backend/layer3/
- `scoring_engine.py`: Weighted blending score, incorporating dynamic upward event rewards.
- `final_price_selector.py`: Selection logic and explainability narrator.

### frontend/
- `pages/`: Independent panels for run pricing, history lookup, stock uploads, and analytics charts.
- `services/`: Data provider adapters interfacing databases and operational csv files.
