import numpy as np

def generate_heuristic_weights(pricing_state, business_context):
    """
    Bootstraps Layer 2 importance weights using expert heuristic rules.
    Guarantees weights are positive and sum to exactly 1.0.
    
    Parameters:
        pricing_state (dict): Nested dictionary of E1, E2, E3, and E4 outputs.
        business_context (dict): Dictionary containing retailer_type, business_strategy, region.
        
    Returns:
        np.ndarray: Normalized weights [E1_weight, E2_weight, E3_weight, E4_weight]
    """
    # 1. Extract signals from the state
    e1_data = pricing_state.get("E1", {})
    e2_data = pricing_state.get("E2", {})
    e3_data = pricing_state.get("E3", {})
    e4_data = pricing_state.get("E4", {})

    supply_risk = float(e1_data.get("supply_risk", 0.0))
    elasticity = float(e2_data.get("elasticity", 0.0))
    inventory_pressure = float(e3_data.get("inventory_pressure", 0.0))
    urgency_score = float(e3_data.get("urgency_score", 0.0))
    market_pressure = float(e4_data.get("market_pressure", 0.0))
    competitive_gap = float(e4_data.get("competitive_gap", 0.0))

    # Business context strings
    retailer_type = str(business_context.get("retailer_type", "standard")).lower()
    strategy = str(business_context.get("business_strategy", business_context.get("business_mode", "balanced"))).lower()

    # 2. Base scores for each engine (equal starting point)
    scores = {
        "E1": 0.25,
        "E2": 0.25,
        "E3": 0.25,
        "E4": 0.25
    }

    # 3. Rule Adjustments
    
    # E1: Procurement Margin Protection
    # Increase weight when supply risk is high to avoid risky pricing, or when strategy is margin-first.
    scores["E1"] += supply_risk * 0.3
    if strategy == "margin_first":
        scores["E1"] += 0.20
    elif strategy == "volume_first":
        scores["E1"] -= 0.05  # Slight de-prioritization

    # E2: Demand Elasticity
    # Increase weight when demand is highly elastic (very negative elasticity) or if strategy is volume-first.
    abs_elasticity = abs(elasticity)
    scores["E2"] += min(0.3, abs_elasticity * 0.08)
    if strategy == "volume_first":
        scores["E2"] += 0.20
    elif strategy == "margin_first":
        scores["E2"] -= 0.05

    # E3: Inventory Liquidation / Safety
    # Increase weight if there is critical stockout risk (high urgency) or major overstock (high pressure).
    scores["E3"] += urgency_score * 0.4
    if abs(inventory_pressure) > 0.6:
        scores["E3"] += 0.20
    # Premium retailers prioritize inventory freshness / availability
    if retailer_type == "premium":
        scores["E3"] += 0.10

    # E4: Market / Competitor Matching
    # Increase weight when competitor promotion rate/pressure is high, or for discount retailers.
    scores["E4"] += market_pressure * 0.3
    if retailer_type == "discount":
        scores["E4"] += 0.20
    # If competitor prices are lower than ours (we have positive gap), pay more attention to market matching.
    if competitive_gap > 0:
        scores["E4"] += min(0.2, (competitive_gap / 10.0) * 0.1)

    # 4. Enforce floor of 0.05 to ensure no engine gets completely ignored
    for k in scores:
        scores[k] = max(0.05, scores[k])

    # 5. Normalization
    total_score = sum(scores.values())
    weights = [
        scores["E1"] / total_score,
        scores["E2"] / total_score,
        scores["E3"] / total_score,
        scores["E4"] / total_score
    ]

    return np.array(weights, dtype=np.float32)
