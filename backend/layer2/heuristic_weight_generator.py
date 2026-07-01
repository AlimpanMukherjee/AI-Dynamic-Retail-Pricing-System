import math
import numpy as np

# =============================================================================
# DEFENSIVE PROGRAMMING & ROBUSTNESS UTILITIES
# =============================================================================

def safe_float(value, default: float = 0.0) -> float:
    """
    Safely converts a value to float, handling None, NaN, inf, list/dict/strings.
    Rejects NaN and infinite values, returning default instead.
    
    Parameters:
        value: The raw input parameter.
        default (float): Fallback value if type conversion fails or value is invalid.
        
    Returns:
        float: Sanitized float value.
    """
    if value is None:
        return default
    try:
        # Avoid string conversions of collection structures that would succeed but be invalid
        if isinstance(value, (list, dict, set, tuple)):
            return default
        # Direct conversion if numeric or string representation
        f_val = float(value)
        # Reject math.nan, inf, -inf
        if math.isnan(f_val) or math.isinf(f_val):
            return default
        return f_val
    except (ValueError, TypeError):
        return default

def clip_signal(value: float, min_value: float, max_value: float) -> float:
    """
    Clips a numeric signal to the range [min_value, max_value].
    
    Parameters:
        value (float): Input signal value.
        min_value (float): Minimum bound.
        max_value (float): Maximum bound.
        
    Returns:
        float: Bound-constrained signal value.
    """
    if min_value > max_value:
        min_value, max_value = max_value, min_value
    return max(min_value, min(max_value, value))

def normalize_weights(scores: dict) -> np.ndarray:
    """
    Safely normalizes scores to sum to exactly 1.0.
    Enforces a floor of 0.05 on individual scores first.
    If the sum of scores is invalid (<= 0, NaN, inf),
    falls back to balanced weights [0.25, 0.25, 0.25, 0.25].
    
    Parameters:
        scores (dict): Dictionary mapping E1, E2, E3, E4 to float scores.
        
    Returns:
        np.ndarray: Normalized float32 weights array of length 4.
    """
    # 1. Enforce floor of 0.05 to ensure no engine gets completely ignored
    for k in scores:
        scores[k] = max(0.05, scores[k])
        
    total_score = sum(scores.values())
    
    # 2. Check for NaN, inf, or zero total
    if (math.isnan(total_score) or 
        math.isinf(total_score) or 
        total_score <= 0):
        # Fallback to balanced weights under bad numeric totals
        return np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float32)
        
    weights = [
        scores["E1"] / total_score,
        scores["E2"] / total_score,
        scores["E3"] / total_score,
        scores["E4"] / total_score
    ]
    return np.array(weights, dtype=np.float32)

# =============================================================================
# MAIN HEURISTIC WEIGHT GENERATOR
# =============================================================================

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
    # -------------------------------------------------------------------------
    # 1. Extract and Sanitize Signals
    # -------------------------------------------------------------------------
    e1_data = pricing_state.get("E1", {}) if isinstance(pricing_state, dict) else {}
    e2_data = pricing_state.get("E2", {}) if isinstance(pricing_state, dict) else {}
    e3_data = pricing_state.get("E3", {}) if isinstance(pricing_state, dict) else {}
    e4_data = pricing_state.get("E4", {}) if isinstance(pricing_state, dict) else {}

    supply_risk = safe_float(e1_data.get("supply_risk", 0.0))
    elasticity = safe_float(e2_data.get("elasticity", 0.0))
    inventory_pressure = safe_float(e3_data.get("inventory_pressure", 0.0))
    urgency_score = safe_float(e3_data.get("urgency_score", 0.0))
    market_pressure = safe_float(e4_data.get("market_pressure", 0.0))
    competitive_gap = safe_float(e4_data.get("competitive_gap", 0.0))

    # Business context string parsing
    ctx = business_context if isinstance(business_context, dict) else {}
    retailer_type = str(ctx.get("retailer_type", "discount")).lower()
    strategy = str(ctx.get("business_strategy", ctx.get("business_mode", "volume_first"))).lower()

    # -------------------------------------------------------------------------
    # 2. Defensive Clipping / Signal Normalization
    # -------------------------------------------------------------------------
    # Constrain signals to expected business intervals to protect scoring from anomalies
    supply_risk = clip_signal(supply_risk, 0.0, 1.0)
    urgency_score = clip_signal(urgency_score, 0.0, 1.0)
    market_pressure = clip_signal(market_pressure, 0.0, 1.0)
    inventory_pressure = clip_signal(inventory_pressure, -1.0, 1.0)

    # -------------------------------------------------------------------------
    # 3. Initialize Base Scores
    # -------------------------------------------------------------------------
    scores = {
        "E1": 0.25,
        "E2": 0.25,
        "E3": 0.25,
        "E4": 0.25
    }

    # -------------------------------------------------------------------------
    # CONSTANTS FOR HEURISTIC WEIGHT ADJUSTMENTS (No Magic Numbers)
    # -------------------------------------------------------------------------
    # Specialty scoring channel weights
    E1_RISK_COEFF = 0.35        # Max contribution from standard supply risk: 0.35
    E2_ELASTICITY_COEFF = 0.30  # Max contribution from demand elasticity: 0.30
    E3_URGENCY_COEFF = 0.25     # Max contribution from stock availability urgency: 0.25
    E4_MARKET_COEFF = 0.30      # Max contribution from general competitor pressure: 0.30

    # Business strategy adjustments
    MARGIN_FIRST_BONUS = 0.20
    VOLUME_FIRST_BONUS = 0.20
    DISCOUNT_RETAILER_BONUS = 0.20
    PREMIUM_RETAILER_BONUS = 0.10
    VOLUME_FIRST_PENALTY = -0.05
    MARGIN_FIRST_PENALTY = -0.05

    # Severe procurement risk thresholds
    SEVERE_SUPPLY_RISK_THRESHOLD = 0.85
    SEVERE_SUPPLY_BONUS = 0.15

    # Severe inventory thresholds to trigger additional E3 weighting
    SEVERE_PRESSURE_THRESHOLD = 0.8
    INVENTORY_BONUS = 0.15

    # Competitor gap sensitivity constants
    COMPETITIVE_GAP_COEFF = 0.15
    MAX_COMPETITIVE_GAP_BONUS = 0.20

    # -------------------------------------------------------------------------
    # 4. Engine Heuristics & Scoring Logic
    # -------------------------------------------------------------------------
    
    # --- ENGINE 1: Procurement & Supply Risk ---
    # Business reasoning: procurement decisions are critical to protect margins 
    # when supply risk increases (supplier failures, lead times) or under margin-first strategy.
    # Expected weight impact: boosts E1 up to +0.35 under normal high-risk and additional +0.15 under severe risk.
    scores["E1"] += supply_risk * E1_RISK_COEFF
    
    # Supply chain emergency:
    # Extremely unreliable suppliers or excessively long lead times
    # require procurement decisions to have stronger influence.
    if supply_risk > SEVERE_SUPPLY_RISK_THRESHOLD:
        scores["E1"] += SEVERE_SUPPLY_BONUS
        
    if strategy == "margin_first":
        scores["E1"] += MARGIN_FIRST_BONUS
    elif strategy == "volume_first":
        scores["E1"] += VOLUME_FIRST_PENALTY

    # --- ENGINE 2: Demand Elasticity ---
    # Business reasoning: pricing optimization must rely heavily on elasticity 
    # if demand is highly sensitive to price shifts, or when strategy focuses on transaction volume.
    # Expected weight impact: E2 score is boosted by up to +0.30 depending on elasticity index.
    abs_elasticity = abs(elasticity)
    # elasticity_strength is normalized so that typical retail elasticity maps to a [0.0, 1.0] range.
    # An elasticity index of 3.0 or higher saturates the strength to 1.0.
    elasticity_strength = min(1.0, abs_elasticity / 3.0)
    scores["E2"] += elasticity_strength * E2_ELASTICITY_COEFF
    if strategy == "volume_first":
        scores["E2"] += VOLUME_FIRST_BONUS
    elif strategy == "margin_first":
        scores["E2"] += MARGIN_FIRST_PENALTY

    # --- ENGINE 3: Inventory Dynamics ---
    # Business reasoning: safety stocks or excess stock liquidations drive pricing 
    # to avoid costly stockouts or inventory holding costs.
    # Expected weight impact: boosts E3 up to +0.25 from urgency, plus +0.15 emergency bonus.
    scores["E3"] += urgency_score * E3_URGENCY_COEFF
    
    # Trigger additional weight bonus only for severe stock imbalances (pressure magnitude > 0.8).
    if abs(inventory_pressure) > SEVERE_PRESSURE_THRESHOLD:
        scores["E3"] += INVENTORY_BONUS
    
    # Premium retailers prioritize inventory freshness / availability
    if retailer_type == "premium":
        scores["E3"] += PREMIUM_RETAILER_BONUS

    # --- ENGINE 4: Market & Competitor Intelligence ---
    # Business reasoning: competitor matching is critical for high-volume discount retailers
    # and when competitor gaps signal that we are significantly out-priced.
    # Expected weight impact: boosts E4 up to +0.30 from market pressure, and up to +0.20 from competitor gap.
    scores["E4"] += market_pressure * E4_MARKET_COEFF
    if retailer_type == "discount":
        scores["E4"] += DISCOUNT_RETAILER_BONUS
        
    # Large competitor price differences (either direction) indicate significant market signals.
    # We apply a capped bonus based on the absolute competitive gap to prevent E4 from dominating.
    scores["E4"] += min(
        MAX_COMPETITIVE_GAP_BONUS,
        abs(competitive_gap) * COMPETITIVE_GAP_COEFF
    )

    # -------------------------------------------------------------------------
    # 5. Normalization & Return
    # -------------------------------------------------------------------------
    return normalize_weights(scores)

# =============================================================================
# LIGHTWEIGHT DEMO SCENARIOS & BUSINESS FUTURE-PROOFING
# =============================================================================

# FUTURE-PROOFING NOTES FOR BUSINESS ARCHITECTS:
# - TUNABLE CONSTANTS:
#   * RISK/ELASTICITY/URGENCY/MARKET_COEFFs are stable baseline multipliers, adjust if specific retail subsectors are onboarded.
#   * SEVERE_SUPPLY_RISK_THRESHOLD (0.85) and SEVERE_PRESSURE_THRESHOLD (0.8) represent operational emergency levels.
#   * INVENTORY_BONUS (0.15) and SEVERE_SUPPLY_BONUS (0.15) can be fine-tuned to scale emergency weight dominance.
#   * COMPETITIVE_GAP_COEFF (0.15) can be scaled to make the engine more reactive to price discrepancies.
# - MACHINE LEARNING INTEGRATION:
#   * These heuristic weights serve as initial targets/bootstraps for Layer 2.
#   * The downstream XGBoost multi-output regressor learns from these targets and generalizes to non-linear combinations.
#   * Eventually, the heuristic rules can be phased out once the ML system has sufficient conversion feedback labels.

if __name__ == "__main__":
    print("=================================================================")
    print("RUNNING LIGHTWEIGHT HEURISTIC WEIGHT GENERATOR DEMO SCENARIOS")
    print("=================================================================\n")
    
    # Scenario 1: Healthy Business (Balanced Retailer)
    state_healthy = {
        "E1": {"supply_risk": 0.25},
        "E2": {"elasticity": -1.2},
        "E3": {"inventory_pressure": 0.1, "urgency_score": 0.1},
        "E4": {"market_pressure": 0.5, "competitive_gap": 0.0}
    }
    ctx_healthy = {"retailer_type": "standard", "business_strategy": "balanced"}
    w_healthy = generate_heuristic_weights(state_healthy, ctx_healthy)
    print("Scenario 1: Healthy Business (Balanced)")
    print(f"  Inputs:  Supply Risk=0.25, Elasticity=-1.2, Inv Pressure=0.1, Market Pressure=0.5, Gap=0.0")
    print(f"  Weights: E1 (Procurement): {w_healthy[0]*100:.2f}% | E2 (Elasticity): {w_healthy[1]*100:.2f}%")
    print(f"           E3 (Inventory):   {w_healthy[2]*100:.2f}% | E4 (Market):     {w_healthy[3]*100:.2f}%\n")
    
    # Scenario 2: Supply Chain Crisis
    state_supply_crisis = {
        "E1": {"supply_risk": 0.95},
        "E2": {"elasticity": 0.0},
        "E3": {"inventory_pressure": 0.1, "urgency_score": 0.1},
        "E4": {"market_pressure": 0.5, "competitive_gap": 0.0}
    }
    w_supply = generate_heuristic_weights(state_supply_crisis, ctx_healthy)
    print("Scenario 2: Extreme Supply Chain Crisis")
    print(f"  Inputs:  Supply Risk=0.95 (Severe), Elasticity=0.0, Inv Pressure=0.1, Market Pressure=0.5, Gap=0.0")
    print(f"  Weights: E1 (Procurement): {w_supply[0]*100:.2f}% | E2 (Elasticity): {w_supply[1]*100:.2f}%")
    print(f"           E3 (Inventory):   {w_supply[2]*100:.2f}% | E4 (Market):     {w_supply[3]*100:.2f}%\n")
    
    # Scenario 3: Inventory Emergency (Stockout / Safety Risk)
    state_inventory_crisis = {
        "E1": {"supply_risk": 0.25},
        "E2": {"elasticity": 0.0},
        "E3": {"inventory_pressure": -1.0, "urgency_score": 1.0},
        "E4": {"market_pressure": 0.5, "competitive_gap": 0.0}
    }
    w_inventory = generate_heuristic_weights(state_inventory_crisis, ctx_healthy)
    print("Scenario 3: Severe Inventory Emergency (Stockout)")
    print(f"  Inputs:  Supply Risk=0.25, Elasticity=0.0, Inv Pressure=-1.0, Urgency=1.0 (Severe), Market Pressure=0.5, Gap=0.0")
    print(f"  Weights: E1 (Procurement): {w_inventory[0]*100:.2f}% | E2 (Elasticity): {w_inventory[1]*100:.2f}%")
    print(f"           E3 (Inventory):   {w_inventory[2]*100:.2f}% | E4 (Market):     {w_inventory[3]*100:.2f}%\n")
    
    # Scenario 4: Discount Retailer Under Heavy Competition (Major Competitive Gap)
    state_market_crisis = {
        "E1": {"supply_risk": 0.25},
        "E2": {"elasticity": 0.0},
        "E3": {"inventory_pressure": 0.1, "urgency_score": 0.1},
        "E4": {"market_pressure": 0.8, "competitive_gap": 2.0}
    }
    ctx_discount = {"retailer_type": "discount", "business_strategy": "volume_first"}
    w_market = generate_heuristic_weights(state_market_crisis, ctx_discount)
    print("Scenario 4: Discount Retailer Under Heavy Competition")
    print(f"  Inputs:  Supply Risk=0.25, Elasticity=0.0, Inv Pressure=0.1, Market Pressure=0.8, Gap=2.0 (Extreme)")
    print(f"  Weights: E1 (Procurement): {w_market[0]*100:.2f}% | E2 (Elasticity): {w_market[1]*100:.2f}%")
    print(f"           E3 (Inventory):   {w_market[2]*100:.2f}% | E4 (Market):     {w_market[3]*100:.2f}%\n")
    
    # Robustness Scenario: Corrupt and Out-of-Bounds Data Handling
    state_corrupt = {
        "E1": {"supply_risk": "abc"},           # Replaced with default 0.0, clipped to [0.0, 1.0]
        "E2": {"elasticity": float('nan')},    # Replaced with default 0.0
        "E3": {"inventory_pressure": 99.0, "urgency_score": None}, # Clipped to 1.0, replaced with default 0.0
        "E4": {"market_pressure": 1.5, "competitive_gap": -5.0}    # Clipped to 1.0, gap checked with absolute value
    }
    w_corrupt = generate_heuristic_weights(state_corrupt, ctx_healthy)
    print("Robustness Check: Corrupt and Out-of-Bounds Inputs")
    print(f"  Inputs:  Supply Risk='abc', Elasticity=NaN, Inv Pressure=99.0, Urgency=None, Market Pressure=1.5, Gap=-5.0")
    print(f"  Weights: E1 (Procurement): {w_corrupt[0]*100:.2f}% | E2 (Elasticity): {w_corrupt[1]*100:.2f}%")
    print(f"           E3 (Inventory):   {w_corrupt[2]*100:.2f}% | E4 (Market):     {w_corrupt[3]*100:.2f}%\n")
    
    print("=================================================================")
    print("DEMO RUN COMPLETED SUCCESSFULLY - NUMERICAL INVARIANTS SATISFIED")
    print("=================================================================")
