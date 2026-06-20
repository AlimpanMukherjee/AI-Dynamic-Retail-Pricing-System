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

def predict_engine_weights(feature_vector, event_active=False):
    """
    Predicts normalized weights for E1, E2, E3, E4, and E5 based on the retail feature vector.
    
    Parameters:
        feature_vector (list or np.ndarray): Flat float array (normally length 12).
        event_active (bool): Whether a special event is active nearby.
        
    Returns:
        dict: Predicted weights mapping like:
              {
                "E1_weight": 0.2375,
                "E2_weight": 0.2375,
                "E3_weight": 0.2375,
                "E4_weight": 0.2375,
                "E5_weight": 0.05
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

    return {
        "E1_weight": float(round(normalized_weights[0] * remaining_weight, 4)),
        "E2_weight": float(round(normalized_weights[1] * remaining_weight, 4)),
        "E3_weight": float(round(normalized_weights[2] * remaining_weight, 4)),
        "E4_weight": float(round(normalized_weights[3] * remaining_weight, 4)),
        "E5_weight": float(round(E5_weight, 4))
    }
