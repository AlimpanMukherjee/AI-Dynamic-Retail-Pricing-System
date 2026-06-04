import pandas as pd
import numpy as np
import os

def load_csv(file_path):
    """
    Safely loads a CSV file from the given path.
    Raises FileNotFoundError if the file does not exist.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Required CSV file not found at: {file_path}")
    return pd.read_csv(file_path)

def normalize(value, min_val, max_val):
    """
    Performs standard min-max normalization, mapping a value to the [0.0, 1.0] range.
    Clips outputs to ensure they stay strictly within bounds.
    """
    if min_val == max_val:
        return 0.5
    normalized = (value - min_val) / (max_val - min_val)
    return float(np.clip(normalized, 0.0, 1.0))

def safe_divide(numerator, denominator, fallback=0.0):
    """
    Safely divides numerator by denominator. Returns fallback if denominator is 0.
    """
    if denominator == 0 or pd.isna(denominator) or pd.isna(numerator):
        return fallback
    return float(numerator / denominator)

def encode_categorical(value, mapping, default=0.0):
    """
    Converts a categorical string (case-insensitive) to its mapped numeric representation.
    """
    if not isinstance(value, str):
        return default
    val_clean = value.strip().lower()
    return float(mapping.get(val_clean, default))
