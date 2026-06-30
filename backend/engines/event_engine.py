import logging
from backend.engines.event_category_mapper import normalize_category

logger = logging.getLogger("pricing_system.engines.event_engine")

# =====================================================
# CONFIGURATION
# =====================================================
MIN_EVENT_PRICE_INCREASE = 0.01  # 1% minimum uplift
MAX_EVENT_PRICE_INCREASE = 0.20  # 20% maximum uplift
DEFAULT_ELASTICITY = 1.5
PRICE_ROUNDING = 0.005  # round price increase to nearest 0.5%
STORE_OPERATING_HOURS = 12.0
MIN_SHORTAGE_UNITS = 0.0

# Event Strength weights (Category relevance is applied directly to demand multiplier instead of strength)
ATTENDANCE_WEIGHT = 0.40
DISTANCE_WEIGHT = 0.25
DURATION_WEIGHT = 0.15
EVENT_TYPE_WEIGHT = 0.20

# Standard Decisions Dictionary
DECISIONS = {
    "NO_CHANGE": "No Price Increase",
    "PRICE_INCREASE": "Increase Price",
    "PRICE_CAPPED": "Increase Capped"
}

EVENT_TIME_FACTORS = {
    "Morning": 0.8,
    "Afternoon": 1.0,
    "Evening": 1.3,
    "Night": 0.6
}

# =====================================================
# EVENT MAPPINGS
# =====================================================
EVENT_TYPE_MULTIPLIERS = {
    "Festival": 1.40,
    "Religious Gathering": 1.35,
    "Sports Match": 1.30,
    "Concert": 1.20,
    "Political Rally": 1.15,
    "Local Fair": 1.15,
    "Marathon": 1.10,
    "Other": 1.00
}

EVENT_TYPE_SCORES = {
    "Festival": 1.00,
    "Religious Gathering": 0.90,
    "Sports Match": 0.75,
    "Concert": 0.60,
    "Political Rally": 0.40,
    "Local Fair": 0.35,
    "Marathon": 0.25,
    "Other": 0.00
}

CATEGORY_RELEVANCE = {
    "Soft Drinks": 1.00,
    "Beverages": 1.00,
    "Ice Cream": 1.00,
    "Snacks": 0.90,
    "Bakery": 0.80,
    "Dairy": 0.60,
    "Staples": 0.30,
    "Electronics": 0.40,
    "Furniture": 0.10,
    "Medicines": 0.20,
    "Other": 0.50
}

ATTENDANCE_CURVE = [
    (0.0, 0.00),
    (500.0, 0.20),
    (2000.0, 0.45),
    (10000.0, 0.75),
    (50000.0, 1.00)
]

DISTANCE_CURVE = [
    (0.0, 1.00),
    (1.0, 0.95),
    (3.0, 0.85),
    (5.0, 0.65),
    (10.0, 0.40),
    (30.0, 0.10)
]

DURATION_CURVE = [
    (0.0, 0.00),
    (1.0, 0.20),
    (2.0, 0.40),
    (4.0, 0.65),
    (8.0, 0.85),
    (12.0, 1.00)
]

# =====================================================
# INTERPOLATION UTILITY
# =====================================================
def interpolate_value(value: float, curve: list) -> float:
    """
    Linearly interpolates a value using a curve list of (x_val, y_val) tuples.
    Assumes curve is sorted by x_val.
    """
    if not curve:
        return 0.0
    if value <= curve[0][0]:
        return curve[0][1]
    if value >= curve[-1][0]:
        return curve[-1][1]
    for i in range(len(curve) - 1):
        x0, y0 = curve[i]
        x1, y1 = curve[i+1]
        if x0 <= value <= x1:
            if x1 == x0:
                return y0
            return y0 + (value - x0) / (x1 - x0) * (y1 - y0)
    return curve[-1][1]

def get_category_relevance_score(product_category: str) -> float:
    """
    Retrieves category relevance score mapped from config.
    """
    normalized_cat = normalize_category(product_category)
    score = CATEGORY_RELEVANCE.get(normalized_cat)
    if score is None:
        for k, v in CATEGORY_RELEVANCE.items():
            if k.lower() in normalized_cat.lower() or normalized_cat.lower() in k.lower():
                score = v
                break
    return score if score is not None else 0.50

# =====================================================
# MAIN EVENT ENGINE
# =====================================================
class EventEngine:
    """
    E5: Event Intelligence Engine (V8 - Demand-Driven Event Pricing).
    Post-optimization price adjustment based on event strength, category relevance,
    store operating hours window demand, stock checks, and elasticity.
    """
    def __init__(self):
        pass

    def run(
        self,
        event_active: bool = False,
        event_type: str = "Other",
        attendance: int = 0,
        distance_km: float = 2.0,
        duration_hours: float = 4.0,
        event_time_of_day: str = "Evening",
        product_category: str = "Other",
        elasticity: float = -1.5,
        expected_demand: float = 0.0,
        available_inventory: float = 0.0,
        base_price: float = 0.0,
        base_market_price: float = 9999.0
    ) -> dict:
        """
        Runs the V8 Event Engine calculations.
        """
        # Determine prediction confidence score
        if not event_active or event_type == "Other":
            confidence = "Low"
        elif elasticity is None or elasticity == 0.0 or expected_demand < 5.0:
            confidence = "Medium"
        else:
            confidence = "High"

        # Return 0 parameters if event is inactive
        if not event_active:
            calculation_steps = {
                "attendance_score": 0.0,
                "distance_score": 0.0,
                "duration_score": 0.0,
                "event_strength": 0.0,
                "category_relevance": get_category_relevance_score(product_category),
                "event_multiplier": 1.0,
                "daily_demand": float(expected_demand),
                "event_window_demand": float(expected_demand),
                "predicted_event_demand": float(expected_demand),
                "inventory": float(available_inventory),
                "expected_shortage": 0.0,
                "required_demand_reduction": 0.0,
                "elasticity": abs(elasticity) if elasticity is not None else DEFAULT_ELASTICITY,
                "required_price_increase": 0.0,
                "rounded_price_increase": 0.0,
                "mrp_constraint": "None",
                "final_price": base_price
            }

            return {
                "event_active": False,
                "event_type": event_type,
                "event_strength": 0.0,
                "event_multiplier": 1.0,
                "expected_demand": float(expected_demand),
                "predicted_event_demand": float(expected_demand),
                "available_inventory": float(available_inventory),
                "expected_shortage": 0.0,
                "required_demand_reduction": 0.0,
                "elasticity": abs(elasticity) if elasticity is not None else DEFAULT_ELASTICITY,
                "recommended_uplift_pct": 0.0,
                "event_price_increase": 0.0,
                "final_price": base_price,
                "decision": DECISIONS["NO_CHANGE"],
                "constraint_applied": "None",
                "reason": "Event is inactive.",
                "calculation_steps": calculation_steps,
                "confidence": confidence,
                "product_category": product_category,
                
                # Backward compatibility:
                "event_score": 0.0,
                "event_opportunity_score": 0.0,
                "business_impact_score": 0.0,
                "impact_level": "LOW",
                "reasoning": [],
                "attendance": int(attendance),
                "distance_km": float(distance_km),
                "duration_hours": float(duration_hours),
                "category_multiplier": 1.0,
                "event_relevance": 1.0
            }

        # 1. Step 1 & 2: Event Analysis & Event Strength
        A_score = interpolate_value(float(attendance), ATTENDANCE_CURVE)
        Dist_score = interpolate_value(float(distance_km), DISTANCE_CURVE)
        Dur_score = interpolate_value(float(duration_hours), DURATION_CURVE)
        
        event_type_multiplier = EVENT_TYPE_MULTIPLIERS.get(event_type, 1.00)
        event_type_score = EVENT_TYPE_SCORES.get(event_type, 0.00)
        category_relevance_score = get_category_relevance_score(product_category)

        event_strength = (
            ATTENDANCE_WEIGHT * A_score +
            DISTANCE_WEIGHT * Dist_score +
            DURATION_WEIGHT * Dur_score +
            EVENT_TYPE_WEIGHT * event_type_score
        )
        event_strength = min(1.0, max(0.0, event_strength))

        # 2. Step 3: Demand Prediction (Event Window)
        # Apply Event Time Factor if the event is within daily store hours
        if duration_hours <= STORE_OPERATING_HOURS:
            time_factor = EVENT_TIME_FACTORS.get(event_time_of_day, 1.0)
        else:
            time_factor = 1.0

        duration_fraction = duration_hours / STORE_OPERATING_HOURS
        demand_during_event = expected_demand * max(0.25, duration_fraction) * time_factor

        # 3. Step 4: Demand Multiplier
        event_demand_multiplier = 1.0 + (event_strength * category_relevance_score) * (event_type_multiplier - 1.0)
        predicted_event_demand = demand_during_event * event_demand_multiplier

        # 4. Step 5: Inventory Analysis
        effective_inventory = available_inventory
        expected_shortage = max(0.0, predicted_event_demand - effective_inventory)

        print("Expected Demand:", expected_demand)
        print("Inventory:", available_inventory)
        print("Predicted Event Demand:", predicted_event_demand)
        print("Shortage:", expected_shortage)

        # Early exit if shortage is less than minimum units check
        if expected_shortage <= MIN_SHORTAGE_UNITS:
            calculation_steps = {
                "attendance_score": float(round(A_score, 4)),
                "distance_score": float(round(Dist_score, 4)),
                "duration_score": float(round(Dur_score, 4)),
                "event_strength": float(round(event_strength, 4)),
                "category_relevance": float(round(category_relevance_score, 4)),
                "event_multiplier": float(round(event_demand_multiplier, 4)),
                "daily_demand": float(round(expected_demand, 2)),
                "event_window_demand": float(round(demand_during_event, 2)),
                "predicted_event_demand": float(round(predicted_event_demand, 2)),
                "inventory": float(round(available_inventory, 2)),
                "expected_shortage": float(round(expected_shortage, 2)),
                "required_demand_reduction": 0.0,
                "elasticity": abs(elasticity) if elasticity is not None else DEFAULT_ELASTICITY,
                "required_price_increase": 0.0,
                "rounded_price_increase": 0.0,
                "mrp_constraint": "None",
                "final_price": base_price
            }

            return {
                "event_active": True,
                "event_type": event_type,
                "event_strength": float(round(event_strength, 4)),
                "event_multiplier": float(round(event_demand_multiplier, 4)),
                "expected_demand": float(expected_demand),
                "predicted_event_demand": float(round(predicted_event_demand, 2)),
                "available_inventory": float(round(available_inventory, 2)),
                "expected_shortage": float(round(expected_shortage, 2)),
                "required_demand_reduction": 0.0,
                "elasticity": abs(elasticity) if elasticity is not None else DEFAULT_ELASTICITY,
                "recommended_uplift_pct": 0.0,
                "event_price_increase": 0.0,
                "final_price": base_price,
                "decision": DECISIONS["NO_CHANGE"],
                "constraint_applied": "None",
                "reason": (
                    f"Inventory ({available_inventory:.0f} units) exceeds predicted event demand "
                    f"({predicted_event_demand:.0f} units). No shortage expected. Price remains unchanged."
                ),
                "calculation_steps": calculation_steps,
                "confidence": confidence,
                "product_category": product_category,
                
                # Backward compatibility:
                "event_score": float(round(event_strength, 4)),
                "event_opportunity_score": float(round(event_strength * 100.0, 2)),
                "business_impact_score": 0.0,
                "impact_level": "LOW" if event_strength < 0.30 else "MEDIUM" if event_strength < 0.55 else "HIGH" if event_strength < 0.80 else "EXTREME",
                "reasoning": [event_type, "Sufficient stock: No scarcity."],
                "attendance": int(attendance),
                "distance_km": float(distance_km),
                "duration_hours": float(duration_hours),
                "category_multiplier": float(category_relevance_score),
                "event_relevance": float(category_relevance_score)
            }

        # 5. Step 6: Required Demand Reduction
        required_demand_reduction = expected_shortage / predicted_event_demand

        # 6. Step 7: Elasticity-Based Pricing
        if elasticity is None or elasticity == 0.0:
            elasticity_val = DEFAULT_ELASTICITY
        else:
            elasticity_val = abs(elasticity)
        elasticity_abs = max(0.2, elasticity_val)
        required_price_increase = required_demand_reduction / elasticity_abs

        # 7. Step 8: Apply Business Constraints
        if required_price_increase < MIN_EVENT_PRICE_INCREASE:
            decision = DECISIONS["NO_CHANGE"]
            constraint_applied = "Below Minimum Threshold"
            recommended_uplift_pct = 0.0
        elif required_price_increase > MAX_EVENT_PRICE_INCREASE:
            decision = DECISIONS["PRICE_CAPPED"]
            constraint_applied = "Maximum Increase Cap"
            recommended_uplift_pct = MAX_EVENT_PRICE_INCREASE
        else:
            decision = DECISIONS["PRICE_INCREASE"]
            constraint_applied = "None"
            recommended_uplift_pct = required_price_increase

        # Apply Price Rounding
        recommended_uplift_pct = round(recommended_uplift_pct / PRICE_ROUNDING) * PRICE_ROUNDING

        # Re-verify minimum threshold post-rounding
        if recommended_uplift_pct < MIN_EVENT_PRICE_INCREASE:
            recommended_uplift_pct = 0.0
            decision = DECISIONS["NO_CHANGE"]
            constraint_applied = "Below Minimum Threshold"

        # 8. Step 9: Final Price Calculation (MRP constraint bypassed as requested)
        final_price = base_price * (1.0 + recommended_uplift_pct)
        event_price_increase = base_price * recommended_uplift_pct

        reason = (
            f"Predicted event demand exceeds available inventory by {expected_shortage:.0f} units. "
            f"A {recommended_uplift_pct*100:.1f}% price increase is recommended to reduce demand and avoid stock-out."
        )

        # Impact level
        if event_strength < 0.30:
            impact_level = "LOW"
        elif event_strength < 0.55:
            impact_level = "MEDIUM"
        elif event_strength < 0.80:
            impact_level = "HIGH"
        else:
            impact_level = "EXTREME"

        # Calculation steps dictionary
        calculation_steps = {
            "attendance_score": float(round(A_score, 4)),
            "distance_score": float(round(Dist_score, 4)),
            "duration_score": float(round(Dur_score, 4)),
            "event_strength": float(round(event_strength, 4)),
            "category_relevance": float(round(category_relevance_score, 4)),
            "event_multiplier": float(round(event_demand_multiplier, 4)),
            "daily_demand": float(round(expected_demand, 2)),
            "event_window_demand": float(round(demand_during_event, 2)),
            "predicted_event_demand": float(round(predicted_event_demand, 2)),
            "inventory": float(round(available_inventory, 2)),
            "expected_shortage": float(round(expected_shortage, 2)),
            "required_demand_reduction": float(round(required_demand_reduction, 4)),
            "elasticity": float(round(elasticity_abs, 4)),
            "required_price_increase": float(round(required_price_increase, 4)),
            "rounded_price_increase": float(round(recommended_uplift_pct, 4)),
            "mrp_constraint": "None",
            "final_price": float(round(final_price, 2))
        }

        # Log pricing results
        logger.info(
            f"Executed V8 Event Engine: strength={event_strength:.2f}, "
            f"uplift={recommended_uplift_pct:.2%}, decision={decision} (Constraint: {constraint_applied})"
        )

        return {
            "event_active": True,
            "event_type": event_type,
            "event_strength": float(round(event_strength, 4)),
            "event_multiplier": float(round(event_demand_multiplier, 4)),
            "expected_demand": float(expected_demand),
            "predicted_event_demand": float(round(predicted_event_demand, 2)),
            "available_inventory": float(round(available_inventory, 2)),
            "expected_shortage": float(round(expected_shortage, 2)),
            "required_demand_reduction": float(round(required_demand_reduction, 4)),
            "elasticity": float(round(elasticity_abs, 4)),
            "recommended_uplift_pct": float(round(recommended_uplift_pct, 4)),
            "event_price_increase": float(round(event_price_increase, 2)),
            "final_price": float(round(final_price, 2)),
            "decision": decision,
            "constraint_applied": constraint_applied,
            "reason": reason,
            "calculation_steps": calculation_steps,
            "confidence": confidence,
            "product_category": product_category,
            
            # Backward compatibility:
            "event_score": float(round(event_strength, 4)),
            "event_opportunity_score": float(round(event_strength * 100.0, 2)),
            "business_impact_score": float(round(recommended_uplift_pct / MAX_EVENT_PRICE_INCREASE, 4)),
            "impact_level": impact_level,
            "reasoning": [event_type, f"Scarcity: expected shortage of {expected_shortage:.0f} units."],
            "attendance": int(attendance),
            "distance_km": float(distance_km),
            "duration_hours": float(duration_hours),
            "category_multiplier": float(category_relevance_score),
            "event_relevance": float(category_relevance_score)
        }

# Module-level run helper
def run_pipeline(
    event_active: bool = False,
    event_type: str = "Other",
    attendance: int = 0,
    distance_km: float = 2.0,
    duration_hours: float = 4.0,
    event_time_of_day: str = "Evening",
    product_category: str = "Other",
    elasticity: float = -1.5,
    expected_demand: float = 0.0,
    available_inventory: float = 0.0,
    base_price: float = 0.0,
    base_market_price: float = 9999.0
) -> dict:
    engine = EventEngine()
    return engine.run(
        event_active=event_active,
        event_type=event_type,
        attendance=attendance,
        distance_km=distance_km,
        duration_hours=duration_hours,
        event_time_of_day=event_time_of_day,
        product_category=product_category,
        elasticity=elasticity,
        expected_demand=expected_demand,
        available_inventory=available_inventory,
        base_price=base_price,
        base_market_price=base_market_price
    )
