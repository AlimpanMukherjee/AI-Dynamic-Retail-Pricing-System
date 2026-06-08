# Project Structure

```text
pricing-system/
|-- backend/
|   |-- layer1/
|   |   |-- engine1.py
|   |   |-- engine2.py
|   |   |-- engine3.py
|   |   |-- engine4.py
|   |   `-- shared_utils.py
|   |-- layer2/
|   |   |-- feature_builder.py
|   |   |-- generate_training_data.py
|   |   |-- heuristic_weight_generator.py
|   |   |-- layer2_model.pkl
|   |   |-- predict_weights.py
|   |   `-- train_layer2.py
|   |-- layer3/
|   |   |-- candidate_generator.py
|   |   |-- constraints.py
|   |   |-- final_price_selector.py
|   |   |-- optimizer.py
|   |   `-- scoring_engine.py
|   `-- pipeline/
|       `-- pricing_pipeline.py
|-- datasets/
|   |-- competitors.csv
|   |-- inventory.csv
|   |-- layer2_training_data.csv
|   |-- procurement.csv
|   |-- products.csv
|   `-- sales.csv
|-- demand_curve_SKU_*.png
|-- docPriceSystem.pdf
|-- project_overview.md
|-- project_structure.md
|-- requirement.txt
`-- .pytest_cache/
```

## Backend

### Layer 1: Specialist Pricing Engines

- `engine1.py`: Calculates procurement costs, supply risk, and minimum safe price.
- `engine2.py`: Models demand elasticity and estimates the demand-optimal price.
- `engine3.py`: Calculates inventory pressure, stockout risk, urgency, and inventory price adjustment.
- `engine4.py`: Evaluates competitor pricing and market pressure.
- `shared_utils.py`: Contains shared CSV, normalization, division, and categorical-encoding helpers.

### Layer 2: Dynamic Weighting

- `feature_builder.py`: Converts Layer 1 outputs and business context into an ML feature vector.
- `generate_training_data.py`: Generates `layer2_training_data.csv` from the source datasets.
- `heuristic_weight_generator.py`: Generates target engine weights used during training.
- `train_layer2.py`: Trains and saves the Layer 2 XGBoost model.
- `predict_weights.py`: Loads the trained model and predicts normalized engine weights.
- `layer2_model.pkl`: Serialized trained Layer 2 model.

### Layer 3: Arbitration and Optimization

- `candidate_generator.py`: Generates possible prices around Layer 1 pricing anchors.
- `constraints.py`: Rejects candidates that violate pricing and safety constraints.
- `scoring_engine.py`: Scores valid candidates using Layer 1 signals and Layer 2 weights.
- `final_price_selector.py`: Selects the highest-scoring candidate and creates the decision report.
- `optimizer.py`: Coordinates the complete Layer 3 workflow.

### Pipeline

- `pricing_pipeline.py`: Runs Layers 1, 2, and 3 to produce the final optimized price.

## Datasets

- `products.csv`: Product master data.
- `procurement.csv`: Supplier, cost, reliability, and lead-time data.
- `sales.csv`: Historical sales data used for demand modeling.
- `inventory.csv`: Store-level inventory data.
- `competitors.csv`: Competitor pricing data.
- `layer2_training_data.csv`: Generated training dataset for the Layer 2 model.

## Other Files

- `demand_curve_SKU_*.png`: Generated demand-curve charts. There are currently 88 files.
- `docPriceSystem.pdf`: Project documentation PDF.
- `project_overview.md`: High-level project and architecture overview.
- `requirement.txt`: Python package dependencies.
- `.pytest_cache/` and `__pycache__/`: Generated Python testing and bytecode cache directories.
