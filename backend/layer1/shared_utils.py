import os
import pandas as pd

def load_csv(file_path):
    """
    Safely loads a CSV file from the given path.
    Raises FileNotFoundError if the file does not exist.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Required CSV file not found at: {file_path}")
    return pd.read_csv(file_path)

def encode_categorical(value, mapping, default=0.0):
    """
    Converts a categorical string (case-insensitive) to its mapped numeric representation.
    """
    if not isinstance(value, str):
        return default
    val_clean = value.strip().lower()
    return float(mapping.get(val_clean, default))
