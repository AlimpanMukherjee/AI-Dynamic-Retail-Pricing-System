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

# ==========================================
# Business Configuration
# ==========================================

# --- Reference Data & Mappings ---

# Target profit margin by category (Engine 1)
CATEGORY_MARGINS = {
    "staples": 0.05,
    "packaged foods": 0.10,
    "dairy": 0.05,
    "beverages": 0.10,
    "snacks": 0.15,
    "personal care": 0.15
}

# Fallback supplier lead time in days by warehouse location (Engine 3 fallback)
LOCATION_LEAD_TIMES = {
    "Mumbai": 5,
    "Delhi": 6,
    "Kolkata": 7,
    "Bengaluru": 8
}


# --- Procurement Engine (Engine 1) ---

# Default target profit margin percentage
DEFAULT_TARGET_MARGIN = 0.10

# Default supplier procurement lead time in days
DEFAULT_LEAD_TIME = 5.0

# Normalization scale divisor for lead time risk calculations
LEAD_TIME_RISK_SCALE = 15.0

# Reliability risk weight in supply risk scoring
SUPPLY_RISK_RELIABILITY_WEIGHT = 0.70

# Lead time risk weight in supply risk scoring
SUPPLY_RISK_LEAD_TIME_WEIGHT = 0.30

# Supply risk weight in risk margin buffer calculations
RISK_BUFFER_SUPPLY_WEIGHT = 0.10

# Cost volatility weight in risk margin buffer calculations
RISK_BUFFER_VOLATILITY_WEIGHT = 0.05


# --- Demand Forecasting (Engine 2) ---

# Maximum sales records before exiting Cold Start mode
COLD_START_THRESHOLD = 30

# Minimum sales records required before Hybrid mode ends (and Normal mode begins)
HYBRID_START_THRESHOLD = 100

# Minimum price boundary multiplier for optimal search candidate price range
PRICE_RANGE_MIN_MULTIPLIER = 0.70

# Maximum price boundary multiplier for optimal search candidate price range
PRICE_RANGE_MAX_MULTIPLIER = 1.30

# Number of price points generated for elasticity and optimal search curves
PRICE_RANGE_NUM_CANDIDATES = 20


# --- Inventory Engine (Engine 3) ---

# Days of supply boundaries representing inventory availability states
INVENTORY_THRESHOLDS = {
    "critical": 3.0,
    "understock": 7.0,
    "shortage": 15.0,
    "healthy": 30.0,
    "overstock": 60.0,
    "heavy_overstock": 120.0,
    "extreme_overstock": 180.0,
    "max_saturation": 360.0
}

# Target pressure output mapping corresponding to DOS keypoints
INVENTORY_PRESSURE_KEYPOINTS = [-1.0, -1.0, -0.7, -0.45, 0.0, 0.3, 0.6, 0.8, 1.0]

# Default safety stock ratio multiplier applied on safety calculations
SAFETY_STOCK_FACTOR = 0.40

# Fallback safety days when safety stock calculations are zero
DEFAULT_SAFETY_DAYS = 3.0

# Default stock age divisor for overstock liquidation urgency calculations
LIQUIDATION_AGE_FACTOR = 180.0

# Maximum markdown discount applied due to high inventory pressure
MAX_INVENTORY_DISCOUNT = 0.15

# Maximum markup premium applied due to low inventory pressure
MAX_INVENTORY_PREMIUM = 0.10


# --- Competitor Intelligence (Engine 4) ---

# Maximum competitor rating scale limit (e.g. 5-star rating)
MAX_COMPETITOR_RATING = 5.0

# Weights applied to competitor metrics to score market pressure
MARKET_PRESSURE_WEIGHTS = {
    "promotion": 0.40,
    "rating": 0.40,
    "trend": 0.20
}

# Maximum competitor-driven price adjustment bounds (±15%)
MAX_COMPETITIVENESS_ADJUSTMENT = 0.15


# --- Event Pricing (Engine 5) ---

# Maximum allowed increase during demand surge pricing
MAX_EVENT_PRICE_INCREASE = 0.20

# Minimum allowed increase to apply during demand surge pricing
MIN_EVENT_PRICE_INCREASE = 0.01

# Sanity-check threshold multiplier comparing event demand to sales velocity
EVENT_WARNING_MULTIPLIER = 20

# Flag to activate validation warnings on demand surges
ENABLE_EVENT_DEMAND_SANITY_CHECK = True

# Fallback price elasticity coefficient if missing
DEFAULT_ELASTICITY = 1.5

# Price rounding increment
PRICE_ROUNDING_INCREMENT = 0.005

# Elasticity adjustment multiplier clamps
ELASTICITY_FACTOR_LIMITS = {
    "min": 0.5,
    "max": 1.5
}


# --- MRP Validation Layer ---

# Flag to enable/disable Maximum Retail Price validation safeguards
ENABLE_MRP_VALIDATION = True

# Fail fast and raise ValueError on missing/invalid product MRP entries
STRICT_MRP_VALIDATION = True


# --- Layer 3 Competition Scoring ---
# Enable competitive score adjustment during candidate scoring
ENABLE_COMPETITIVE_PRICING_ADJUSTMENT = True

# Base adjustment weight
COMPETITIVE_PRICING_ADJUSTMENT_WEIGHT = 0.35

# Ignore very small pricing differences below this percentage (tolerance)
COMPETITIVE_PRICING_GAP_TOLERANCE = 0.02

# Maximum adjustment score reduction allowed
MAX_COMPETITIVE_PRICING_ADJUSTMENT = 0.15

# Minimum competitor price samples required to apply adjustment
MIN_COMPETITOR_SAMPLE_SIZE = 3

# Competitive gap severity thresholds
COMPETITIVE_GAP_LEVELS = {
    "low": 0.05,
    "medium": 0.10,
    "high": 0.20
}

# Severity multipliers
COMPETITIVE_GAP_MULTIPLIERS = {
    "low": 1.0,
    "medium": 1.35,
    "high": 1.75
}



# Developer/Base Model Training Datasets Directory (Preserved for ML Dev/Testing/Training)
DEV_DATA_DIR = os.path.join(PROJECT_ROOT, "datasets")
DEV_PRODUCTS_PATH = os.path.join(DEV_DATA_DIR, "products.csv")
DEV_SALES_PATH = os.path.join(DEV_DATA_DIR, "sales.csv")
DEV_INVENTORY_PATH = os.path.join(DEV_DATA_DIR, "inventory_current.csv")
DEV_PROCUREMENT_PATH = os.path.join(DEV_DATA_DIR, "procurement.csv")

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
