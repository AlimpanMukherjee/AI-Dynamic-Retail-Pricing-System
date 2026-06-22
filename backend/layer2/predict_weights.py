import os
import joblib
import numpy as np

# Absolute path of the trained model file relative to project root
MODEL_PATH = os.path.join("backend", "layer2", "layer2_model.pkl")

# Keep the model cached in memory to avoid repeated disk reads during production API calls
_MODEL_CACHE = None

def load_layer2_model():
    """
    Loads the serialized XGBoost multi-output regressor model.
    """
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Layer 2 model file not found at: {MODEL_PATH}. "
                "Please train the model first by running `python -m backend.layer2.train_layer2`."
            )
        _MODEL_CACHE = joblib.load(MODEL_PATH)
    return _MODEL_CACHE

def predict_engine_weights(feature_vector, event_active=False, confidence=1.0):
    """
    Predicts normalized weights for E1, E2, E3, E4, and E5 based on the retail feature vector,
    then applies confidence scaling to E2 based on historical sales data.
    
    Parameters:
        feature_vector (list or np.ndarray): Flat float array (normally length 12).
        event_active (bool): Whether a special event is active nearby.
        confidence (float): Confidence score for Engine 2 (between 0.10 and 1.0).
        
    Returns:
        dict: Predicted and adjusted weights mapping like:
              {
                "E1_weight": 0.32,
                "E2_weight": 0.04,
                "E3_weight": 0.32,
                "E4_weight": 0.24,
                "E5_weight": 0.08
              }
    """
    model = load_layer2_model()

    # Gracefully determine how many features the model expects to prevent mismatch crash
    try:
        n_features = model.estimators_[0].n_features_in_
    except Exception:
        n_features = 11

    # Slice feature vector to match model expectations (normally first 11 features)
    X_in = np.array(feature_vector[:n_features], dtype=np.float32).reshape(1, -1)
    
    # Predict weights (returns a numpy array of shape (1, 4))
    raw_predictions = model.predict(X_in)[0]

    # Post-processing:
    # 1. Clip weights to prevent negative predictions or extremely low contributions
    clipped = np.clip(raw_predictions, 0.05, None)
    
    # 2. Normalize weights to sum to exactly 1.0
    total = np.sum(clipped)
    normalized_weights = clipped / total

    # Retrieve event_score from feature_vector (index 11 if length 12)
    event_score = float(feature_vector[11]) if len(feature_vector) > 11 else 0.0

    # Calculate dynamic E5 weight: min(0.15, event_score * 0.15) if active
    if event_active:
        E5_weight = min(0.15, event_score * 0.15)
    else:
        E5_weight = 0.0

    # Distribute the remaining weight to E1-E4
    remaining_weight = 1.0 - E5_weight

    # Calculate initial baseline weights
    weights = {
        "E1_weight": float(normalized_weights[0] * remaining_weight),
        "E2_weight": float(normalized_weights[1] * remaining_weight),
        "E3_weight": float(normalized_weights[2] * remaining_weight),
        "E4_weight": float(normalized_weights[3] * remaining_weight),
        "E5_weight": float(E5_weight)
    }

    # Apply Confidence Scaling Step
    pred_e2 = weights["E2_weight"]
    adjusted_e2 = pred_e2 * confidence
    weights["E2_weight"] = adjusted_e2

    # Remaining weight from E2 to redistribute proportionally
    redist_weight = pred_e2 - adjusted_e2
    other_sum = weights["E1_weight"] + weights["E3_weight"] + weights["E4_weight"] + weights["E5_weight"]

    if other_sum > 0.0:
        for key in ["E1_weight", "E3_weight", "E4_weight", "E5_weight"]:
            weights[key] += redist_weight * (weights[key] / other_sum)
    else:
        for key in ["E1_weight", "E3_weight", "E4_weight", "E5_weight"]:
            weights[key] += redist_weight / 4.0

    # Re-normalize and round
    sum_total = sum(weights.values())
    if sum_total > 0.0:
        for key in weights:
            weights[key] = float(round(weights[key] / sum_total, 4))

    # Adjust rounding discrepancy
    sum_w = sum(weights.values())
    diff = round(1.0 - sum_w, 4)
    if diff != 0:
        weights["E1_weight"] = float(round(weights["E1_weight"] + diff, 4))

    return weights
