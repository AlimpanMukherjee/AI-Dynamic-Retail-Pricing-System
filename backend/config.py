import os

# Centralized configuration and file paths for the pricing system

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Developer/Base Model Training Datasets Directory (Preserved for ML Dev/Testing/Training)
DEV_DATA_DIR = os.path.join(PROJECT_ROOT, "datasets")
DEV_PRODUCTS_PATH = os.path.join(DEV_DATA_DIR, "products.csv")
DEV_SALES_PATH = os.path.join(DEV_DATA_DIR, "sales.csv")
DEV_INVENTORY_PATH = os.path.join(DEV_DATA_DIR, "inventory.csv")
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
        return os.path.join(_get_customer_data_dir(), "sales.csv")
    elif name == "CUSTOMER_INVENTORY_PATH":
        return os.path.join(_get_customer_data_dir(), "inventory.csv")
    elif name == "CUSTOMER_PROCUREMENT_PATH":
        return os.path.join(_get_customer_data_dir(), "procurement.csv")
    elif name == "CUSTOMER_COMPETITOR_PATH":
        return os.path.join(_get_customer_data_dir(), "competitors.csv")
    elif name == "CUSTOMER_DATA_DIR":
        return _get_customer_data_dir()
    raise AttributeError(f"module {__name__} has no attribute {name}")
