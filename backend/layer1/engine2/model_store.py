import os
import joblib
import json
import logging

logger = logging.getLogger("pricing_system.layer1.engine2.model_store")

def ensure_dir_exists(filepath):
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

def save_model(model, features, encoders, filepath):
    ensure_dir_exists(filepath)
    joblib.dump({
        'model': model,
        'features': features,
        'encoders': encoders
    }, filepath)
    logger.info(f"Model saved successfully to {filepath}")

def load_model(filepath):
    if not os.path.exists(filepath):
        logger.error(f"Model file missing: {filepath}")
        raise FileNotFoundError(f"Model file not found: {filepath}")
    data = joblib.load(filepath)
    logger.info(f"Model loaded successfully from {filepath}")
    return data['model'], data['features'], data['encoders']

def save_metadata(metadata, filepath):
    ensure_dir_exists(filepath)
    with open(filepath, 'w') as f:
        json.dump(metadata, f, indent=4)
    logger.info(f"Metadata saved successfully to {filepath}")

def load_metadata(filepath):
    if not os.path.exists(filepath):
        logger.warning(f"Metadata file missing: {filepath}")
        return None
    with open(filepath, 'r') as f:
        metadata = json.load(f)
    return metadata
