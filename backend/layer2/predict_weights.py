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

def predict_engine_weights(feature_vector):
    """
    Predicts normalized weights for E1, E2, E3, and E4 based on the retail feature vector.
    
    Parameters:
        feature_vector (list or np.ndarray): Flat float array of length 11.
        
    Returns:
        dict: Predicted weights mapping like:
              {
                "E1_weight": 0.25,
                "E2_weight": 0.25,
                "E3_weight": 0.25,
                "E4_weight": 0.25
              }
    """
    model = load_layer2_model()

    # Ensure input is shape (1, n_features) for scikit-learn
    X_in = np.array(feature_vector, dtype=np.float32).reshape(1, -1)
    
    # Predict weights (returns a numpy array of shape (1, 4))
    raw_predictions = model.predict(X_in)[0]

    # Post-processing:
    # 1. Clip weights to prevent negative predictions or extremely low contributions
    clipped = np.clip(raw_predictions, 0.05, None)
    
    # 2. Normalize weights to sum to exactly 1.0
    total = np.sum(clipped)
    normalized_weights = clipped / total

    return {
        "E1_weight": float(round(normalized_weights[0], 4)),
        "E2_weight": float(round(normalized_weights[1], 4)),
        "E3_weight": float(round(normalized_weights[2], 4)),
        "E4_weight": float(round(normalized_weights[3], 4))
    }
