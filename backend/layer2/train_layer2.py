import os
import joblib
import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_squared_error, r2_score

# Import feature metadata
from backend.layer2.feature_builder import get_feature_names

def train_model():
    print("Initializing Layer 2 Meta-Learning training...")
    
    # Define file paths
    data_path = "datasets/layer2_training_data.csv"
    model_path = "backend/layer2/layer2_model.pkl"

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Training data not found at: {data_path}. Please run generate_training_data first.")

    # 1. Load Dataset
    df = pd.read_csv(data_path)
    
    # Retrieve feature column names and target weight column names
    feature_cols = get_feature_names()
    target_cols = ["target_E1_weight", "target_E2_weight", "target_E3_weight", "target_E4_weight"]

    X = df[feature_cols]
    y = df[target_cols]

    print(f"Loaded dataset with {len(df)} rows.")
    print(f"Features: {feature_cols}")
    print(f"Targets: {target_cols}")

    # 2. Train-Test Split (80% Train, 20% Test)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3. Model Definition
    # We use a MultiOutputRegressor wrapping XGBRegressor to predict the four weights independently.
    # Hyperparameters are tuned to prevent overfitting on the heuristic rules.
    base_xgboost = XGBRegressor(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.05,
        random_state=42,
        verbosity=1
    )
    
    model = MultiOutputRegressor(base_xgboost)

    # 4. Train Model
    print("Fitting Multi-Output XGBoost Regressor...")
    model.fit(X_train, y_train)
    print("Model training completed successfully.")

    # 5. Evaluate Model
    y_pred = model.predict(X_test)
    
    print("\n================ EVALUATION METRICS ================")
    for i, target_name in enumerate(target_cols):
        mse = mean_squared_error(y_test.iloc[:, i], y_pred[:, i])
        r2 = r2_score(y_test.iloc[:, i], y_pred[:, i])
        print(f"Target: {target_name.replace('target_', '')}")
        print(f"  Mean Squared Error (MSE): {mse:.6f}")
        print(f"  R^2 Accuracy Score:       {r2:.4f}")
    print("====================================================")

    # 6. Feature Importance Explanation
    # Since we have a MultiOutputRegressor, we can inspect feature importances for each engine target.
    print("\n================ FEATURE IMPORTANCES ===============")
    for i, target_name in enumerate(target_cols):
        engine_label = target_name.replace('target_', '').replace('_weight', '')
        estimator = model.estimators_[i]
        importances = estimator.feature_importances_
        
        # Pair feature names with their importance values and sort
        feat_imp = sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True)
        
        print(f"\nTop Features driving {engine_label} weight:")
        for rank, (name, val) in enumerate(feat_imp[:4], 1):
            if val > 0.001:
                print(f"  {rank}. {name:<30} : {val * 100:.2f}%")
    print("\n====================================================")

    # 7. Print Sample Predictions Comparison
    print("\n================ SAMPLE PREDICTIONS ================")
    sample_indices = [0, 5, 10]  # Pick three sample indices from the test set
    for idx in sample_indices:
        real_vals = y_test.iloc[idx].values
        pred_vals = y_pred[idx]
        
        # Post-process predictions to sum to 1.0 (to show how prediction normalization looks)
        pred_clipped = np.clip(pred_vals, 0.05, None)
        pred_normalized = pred_clipped / np.sum(pred_clipped)
        
        # Get corresponding feature values for context
        feat_vals = X_test.iloc[idx].to_dict()
        
        # Decode strategy and type for printout readability
        strategy_lbl = ["volume_first", "balanced", "margin_first"][int(feat_vals["business_strategy_encoded"])]
        type_lbl = ["discount", "standard", "premium"][int(feat_vals["retailer_type_encoded"])]
        
        print(f"\nScenario: {type_lbl} retailer | {strategy_lbl} strategy")
        print(f"Key signals: Supply Risk={feat_vals['supply_risk']:.2f}, Urgency={feat_vals['urgency_score']:.2f}, Competitor Gap={feat_vals['competitive_gap']:.2f}")
        print("Weights comparison:")
        print(f"  E1 (Procurement) -> Target: {real_vals[0]:.3f} | Pred: {pred_normalized[0]:.3f}")
        print(f"  E2 (Elasticity)  -> Target: {real_vals[1]:.3f} | Pred: {pred_normalized[1]:.3f}")
        print(f"  E3 (Inventory)   -> Target: {real_vals[2]:.3f} | Pred: {pred_normalized[2]:.3f}")
        print(f"  E4 (Market)      -> Target: {real_vals[3]:.3f} | Pred: {pred_normalized[3]:.3f}")
    print("====================================================")

    # 8. Save Model
    joblib.dump(model, model_path)
    print(f"\nTrained model successfully serialized and saved to: {model_path}")

if __name__ == "__main__":
    train_model()
