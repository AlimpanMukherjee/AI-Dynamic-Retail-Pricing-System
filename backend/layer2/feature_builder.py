import numpy as np
from backend.layer1.shared_utils import encode_categorical

# Mappings for categorical business context features
RETAILER_TYPE_MAP = {
    "discount": 0.0,
    "standard": 1.0,
    "premium": 2.0
}

BUSINESS_STRATEGY_MAP = {
    "volume_first": 0.0,
    "balanced": 1.0,
    "margin_first": 2.0
}

REGION_MAP = {
    "urban": 0.0,
    "suburban": 1.0,
    "rural": 2.0
}

# The ordered names of features in our vector (used for documentation and XGBoost modeling)
FEATURE_NAMES = [
    "minimum_safe_price",
    "supply_risk",
    "optimal_price",
    "elasticity",
    "inventory_pressure",
    "urgency_score",
    "market_pressure",
    "competitive_gap",
    "retailer_type_encoded",
    "business_strategy_encoded",
    "region_encoded",
    "event_score"
]

def build_feature_vector(pricing_state, business_context):
    """
    Constructs an ML-ready numeric feature vector from the unified pricing state
    and business context.
    
    Parameters:
        pricing_state (dict): Output from Layer 1 specialist engines.
        business_context (dict): Dictionary with keys: retailer_type, business_strategy, region.
        
    Returns:
        np.ndarray: A flat float array of length 12.
    """
    # 1. Extract Layer 1 Engine Signals (defaults used in case of missing keys)
    e1_data = pricing_state.get("E1", {})
    e2_data = pricing_state.get("E2", {})
    e3_data = pricing_state.get("E3", {})
    e4_data = pricing_state.get("E4", {})
    e5_data = pricing_state.get("E5", {})

    min_safe_price = float(e1_data.get("minimum_safe_price", 0.0))
    supply_risk = float(e1_data.get("supply_risk", 0.0))
    
    optimal_price = float(e2_data.get("optimal_price", min_safe_price if min_safe_price > 0 else 0.0))
    elasticity = float(e2_data.get("elasticity", 0.0))
    
    inventory_pressure = float(e3_data.get("inventory_pressure", 0.0))
    urgency_score = float(e3_data.get("urgency_score", 0.0))
    
    market_pressure = float(e4_data.get("market_pressure", 0.0))
    competitive_gap = float(e4_data.get("competitive_gap", 0.0))
    event_score = float(e5_data.get("event_score", 0.0))

    # 2. Encode Business Context Signals
    retailer_type = business_context.get("retailer_type", "standard")
    # Supporting both potential keys: business_strategy or business_mode
    business_strategy = business_context.get("business_strategy", business_context.get("business_mode", "balanced"))
    region = business_context.get("region", "urban")

    retailer_enc = encode_categorical(retailer_type, RETAILER_TYPE_MAP, default=1.0)
    strategy_enc = encode_categorical(business_strategy, BUSINESS_STRATEGY_MAP, default=1.0)
    region_enc = encode_categorical(region, REGION_MAP, default=0.0)

    # 3. Assemble final flat vector
    feature_vector = np.array([
        min_safe_price,
        supply_risk,
        optimal_price,
        elasticity,
        inventory_pressure,
        urgency_score,
        market_pressure,
        competitive_gap,
        retailer_enc,
        strategy_enc,
        region_enc,
        event_score
    ], dtype=np.float32)

    return feature_vector

def get_feature_names():
    """
    Returns the ordered list of feature names.
    """
    return FEATURE_NAMES
