import os

# Centralized configuration and file paths for the pricing system

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Progressive Learning Thresholds
LOW_DATA_THRESHOLD = 500
MEDIUM_DATA_THRESHOLD = 1000
HIGH_DATA_THRESHOLD = 5000
MIN_ENGINE2_CONFIDENCE = 0.10


# Developer/Base Model Training Datasets Directory (Preserved for ML Dev/Testing/Training)
DEV_DATA_DIR = os.path.join(PROJECT_ROOT, "datasets")
DEV_PRODUCTS_PATH = os.path.join(DEV_DATA_DIR, "products.csv")
DEV_SALES_PATH = os.path.join(DEV_DATA_DIR, "sales.csv")
DEV_INVENTORY_PATH = os.path.join(DEV_DATA_DIR, "inventory_current.csv")
DEV_INVENTORY_CURRENT_PATH = os.path.join(DEV_DATA_DIR, "inventory_current.csv")
DEV_INVENTORY_HISTORY_PATH = os.path.join(DEV_DATA_DIR, "inventory_history.csv")
DEV_PROCUREMENT_PATH = os.path.join(DEV_DATA_DIR, "procurement.csv")
DEV_COMPETITORS_PATH = os.path.join(DEV_DATA_DIR, "competitors.csv")

def _get_customer_data_dir() -> str:
    # Dynamically determine the data directory.
    # If running under pytest, route to DEV_DATA_DIR to satisfy:
    # "Keep datasets/ for Testing" and isolate test modifications.
    if "PYTEST_CURRENT_TEST" in os.environ or os.environ.get("PRICING_TESTING") == "true":
        return DEV_DATA_DIR
    return os.path.join(PROJECT_ROOT, "customer_data")

def __getattr__(name: str):
    if name == "CUSTOMER_PRODUCTS_PATH":
        return os.path.join(_get_customer_data_dir(), "products.csv")
    elif name == "CUSTOMER_SALES_PATH":
        if "PYTEST_CURRENT_TEST" in os.environ or os.environ.get("PRICING_TESTING") == "true":
            return os.path.join(_get_customer_data_dir(), "sales.csv")
        return os.path.join(_get_customer_data_dir(), "sales_history.csv")
    elif name == "CUSTOMER_INVENTORY_PATH":
        return os.path.join(_get_customer_data_dir(), "inventory_current.csv")
    elif name == "CUSTOMER_INVENTORY_CURRENT_PATH":
        return os.path.join(_get_customer_data_dir(), "inventory_current.csv")
    elif name == "CUSTOMER_INVENTORY_HISTORY_PATH":
        return os.path.join(_get_customer_data_dir(), "inventory_history.csv")
    elif name == "CUSTOMER_PRICING_HISTORY_PATH":
        return os.path.join(_get_customer_data_dir(), "pricing_history.csv")
    elif name == "CUSTOMER_MODEL_REGISTRY_PATH":
        return os.path.join(_get_customer_data_dir(), "model_registry.csv")
    elif name == "CUSTOMER_ALERTS_PATH":
        return os.path.join(_get_customer_data_dir(), "alerts.csv")
    elif name == "MODELS_DIR":
        return os.path.join(PROJECT_ROOT, "models")
    elif name == "BACKUP_INVENTORY_DIR":
        return os.path.join(PROJECT_ROOT, "backend", "uploads", "inventory")
    elif name == "CUSTOMER_PROCUREMENT_PATH":
        return os.path.join(_get_customer_data_dir(), "procurement.csv")
    elif name == "CUSTOMER_COMPETITOR_PATH":
        return os.path.join(_get_customer_data_dir(), "competitors.csv")
    elif name == "CUSTOMER_DATA_DIR":
        return _get_customer_data_dir()
    raise AttributeError(f"module {__name__} has no attribute {name}")
