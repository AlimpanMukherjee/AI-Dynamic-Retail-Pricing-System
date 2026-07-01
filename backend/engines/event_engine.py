import os
import logging
import numpy as np
import backend.config as cfg

logger = logging.getLogger("pricing_system.engines.event_engine")

# Event pricing engine logic using configs from config.py

class EventEngine:
    """
    E5: Event Pricing Engine.
    Post-optimization price adjustment percentage recommendation based on 
    projected demand surge, available inventory, and product price elasticity.
    """
    def __init__(self):
        pass

    def run(
        self,
        event_active: bool = False,
        projected_event_demand: float = 0.0,
        available_inventory: float = 0.0,
        elasticity: float = -1.5,
        sales_velocity_per_day: float = 0.0,
        # Keep old metadata parameters for backward compatibility:
        event_type: str = "Other",
        attendance: int = 0,
        distance_km: float = 2.0,
        duration_hours: float = 4.0,
        event_time_of_day: str = "Evening",
        product_category: str = "Other",
        base_market_price: float = 9999.0,
        **kwargs
    ) -> dict:
        """
        Runs the demand-driven scarcity pricing analysis.
        """
        # Load configs
        max_increase = cfg.MAX_EVENT_PRICE_INCREASE
        min_increase = cfg.MIN_EVENT_PRICE_INCREASE
        warning_mult = cfg.EVENT_WARNING_MULTIPLIER
        sanity_check_enabled = cfg.ENABLE_EVENT_DEMAND_SANITY_CHECK

        warnings = []
        reasoning = []

        # If event is inactive or demand is 0/negative
        if not event_active or projected_event_demand <= 0:
            reasoning.append("✓ Event pricing is inactive or projected demand is zero.")
            return {
                "event_active": False,
                "projected_demand": 0.0,
                "available_inventory": float(available_inventory),
                "inventory_shortage": 0.0,
                "inventory_coverage": 1.0,
                "scarcity_score": 0.0,
                "elasticity": float(elasticity) if elasticity is not None else -cfg.DEFAULT_ELASTICITY,
                "elasticity_factor": 1.0,
                "recommended_price_increase_pct": 0.0,
                "estimated_demand_after_increase": 0.0,
                "projected_inventory_coverage": 1.0,
                "stock_sufficient": True,
                "warnings": warnings,
                "reasoning": reasoning,
                
                # Backward compatibility keys:
                "event_type": event_type,
                "attendance": attendance,
                "distance_km": distance_km,
                "duration_hours": duration_hours,
                "event_time_of_day": event_time_of_day,
                "product_category": product_category,
                "event_strength": 0.0,
                "event_multiplier": 1.0,
                "expected_demand": 0.0,
                "predicted_event_demand": 0.0,
                "expected_shortage": 0.0,
                "required_demand_reduction": 0.0,
                "recommended_uplift_pct": 0.0,
                "event_price_increase": 0.0,
                "final_price": 0.0,
                "decision": "No Price Increase",
                "constraint_applied": "None",
                "reason": "Event is inactive.",
                "confidence": "Low",
                "event_score": 0.0,
                "event_opportunity_score": 0.0,
                "business_impact_score": 0.0,
                "impact_level": "LOW",
                "category_multiplier": 1.0,
                "event_relevance": 1.0
            }

        # 1. Validation Sanity Check
        if sanity_check_enabled and sales_velocity_per_day > 0 and projected_event_demand > warning_mult * sales_velocity_per_day:
            warnings.append(f"⚠ Projected demand ({projected_event_demand:.0f} units) is significantly higher than historical sales velocity ({sales_velocity_per_day:.2f} units/day).")

        # 2. Inventory Coverage & Scarcity Score
        effective_inventory = float(available_inventory)
        projected_demand = float(projected_event_demand)

        inventory_coverage = min(1.0, effective_inventory / projected_demand) if projected_demand > 0 else 1.0
        scarcity_score = 1.0 - inventory_coverage
        stock_sufficient = (effective_inventory >= projected_demand)
        inventory_shortage = max(0.0, projected_demand - effective_inventory)

        # 3. Elasticity adjustment factor (2.0 - abs(elasticity) clamped to min/max limits)
        elasticity_abs = abs(elasticity) if elasticity is not None else cfg.DEFAULT_ELASTICITY
        elasticity_factor = max(cfg.ELASTICITY_FACTOR_LIMITS["min"], min(cfg.ELASTICITY_FACTOR_LIMITS["max"], 2.0 - elasticity_abs))

        # 4. Scarcity and Elasticity-Based Uplift
        raw_increase_pct = scarcity_score * elasticity_factor
        constraint_applied = "None"

        if raw_increase_pct < min_increase:
            recommended_price_increase_pct = 0.0
            decision = "No Price Increase"
            constraint_applied = "Below Minimum Threshold"
        elif raw_increase_pct > max_increase:
            recommended_price_increase_pct = max_increase
            decision = "Increase Capped"
            constraint_applied = "Maximum Increase Cap"
        else:
            recommended_price_increase_pct = raw_increase_pct
            decision = "Increase Price"

        # Apply Price Rounding increment
        recommended_price_increase_pct = round(recommended_price_increase_pct / cfg.PRICE_ROUNDING_INCREMENT) * cfg.PRICE_ROUNDING_INCREMENT

        # Recheck minimum threshold post-rounding
        if recommended_price_increase_pct < min_increase:
            recommended_price_increase_pct = 0.0
            decision = "No Price Increase"
            constraint_applied = "Below Minimum Threshold"

        # 5. Demand Reduction Estimate
        demand_change_pct = -1.0 * elasticity_abs * recommended_price_increase_pct
        estimated_demand_after_increase = max(0.0, projected_demand * (1.0 + demand_change_pct))

        if estimated_demand_after_increase > 0:
            projected_inventory_coverage = min(1.0, effective_inventory / estimated_demand_after_increase)
        else:
            projected_inventory_coverage = 1.0

        # 6. Generate Reasoning Bullets
        reasoning.append("✓ Event pricing is enabled.")
        if stock_sufficient:
            reasoning.append(f"✓ Current inventory ({effective_inventory:.0f} units) satisfies the projected demand ({projected_demand:.0f} units).")
            reasoning.append("✓ No price increase recommended.")
        else:
            reasoning.append(f"✓ Projected demand exceeds available inventory by {inventory_shortage:.0f} units.")
            reasoning.append(f"✓ Current inventory can satisfy only {inventory_coverage * 100:.0f}% of projected demand.")
            if elasticity_abs < 1.0:
                reasoning.append(f"✓ Product shows relatively inelastic demand (elasticity: -{elasticity_abs:.2f}).")
            else:
                reasoning.append(f"✓ Product shows relatively elastic demand (elasticity: -{elasticity_abs:.2f}).")

            if constraint_applied == "Maximum Increase Cap":
                reasoning.append(f"✓ Recommended price increase capped at {max_increase * 100:.0f}%.")
            else:
                reasoning.append(f"✓ Recommended price increase: {recommended_price_increase_pct * 100:.1f}%.")

            # Estimated demand correction statement
            demand_reduction = projected_demand - estimated_demand_after_increase
            reasoning.append(f"✓ Price adjustment is estimated to reduce demand by {demand_reduction:.0f} units (approx. {estimated_demand_after_increase:.0f} units remaining).")
            reasoning.append(f"✓ Projected inventory coverage is expected to improve to {projected_inventory_coverage * 100:.0f}%.")

        confidence = "High" if len(warnings) == 0 else "Medium"
        impact_level = "LOW" if recommended_price_increase_pct < 0.05 else "MEDIUM" if recommended_price_increase_pct < 0.12 else "HIGH" if recommended_price_increase_pct < 0.18 else "EXTREME"

        reason = (
            f"Expected event demand exceeds available inventory. "
            f"A {recommended_price_increase_pct*100:.1f}% price increase is recommended to reduce demand."
        ) if not stock_sufficient else "Sufficient inventory. No change."

        return {
            "event_active": True,
            "projected_demand": projected_demand,
            "available_inventory": effective_inventory,
            "inventory_shortage": inventory_shortage,
            "inventory_coverage": inventory_coverage,
            "scarcity_score": scarcity_score,
            "elasticity": float(elasticity) if elasticity is not None else -cfg.DEFAULT_ELASTICITY,
            "elasticity_factor": elasticity_factor,
            "recommended_price_increase_pct": recommended_price_increase_pct,
            "estimated_demand_after_increase": estimated_demand_after_increase,
            "projected_inventory_coverage": projected_inventory_coverage,
            "stock_sufficient": stock_sufficient,
            "warnings": warnings,
            "reasoning": reasoning,

            # Backward compatibility keys:
            "event_type": event_type,
            "attendance": attendance,
            "distance_km": distance_km,
            "duration_hours": duration_hours,
            "event_time_of_day": event_time_of_day,
            "product_category": product_category,
            "event_strength": scarcity_score,
            "event_multiplier": 1.0 + recommended_price_increase_pct,
            "expected_demand": float(projected_demand),
            "predicted_event_demand": float(projected_demand),
            "expected_shortage": inventory_shortage,
            "required_demand_reduction": float(scarcity_score),
            "recommended_uplift_pct": recommended_price_increase_pct,
            "event_price_increase": 0.0,  # Pipeline will populate
            "final_price": 0.0,            # Pipeline will populate
            "decision": decision,
            "constraint_applied": constraint_applied,
            "reason": reason,
            "confidence": confidence,
            "event_score": scarcity_score,
            "event_opportunity_score": recommended_price_increase_pct * 100.0,
            "business_impact_score": recommended_price_increase_pct / max_increase if max_increase > 0 else 0.0,
            "impact_level": impact_level,
            "category_multiplier": 1.0,
            "event_relevance": 1.0
        }

# Module-level run helper
def run_pipeline(
    event_active: bool = False,
    projected_event_demand: float = 0.0,
    available_inventory: float = 0.0,
    elasticity: float = -1.5,
    sales_velocity_per_day: float = 0.0,
    # Old parameters for backward compatibility:
    event_type: str = "Other",
    attendance: int = 0,
    distance_km: float = 2.0,
    duration_hours: float = 4.0,
    event_time_of_day: str = "Evening",
    product_category: str = "Other",
    base_market_price: float = 9999.0,
    **kwargs
) -> dict:
    engine = EventEngine()
    return engine.run(
        event_active=event_active,
        projected_event_demand=projected_event_demand,
        available_inventory=available_inventory,
        elasticity=elasticity,
        sales_velocity_per_day=sales_velocity_per_day,
        event_type=event_type,
        attendance=attendance,
        distance_km=distance_km,
        duration_hours=duration_hours,
        event_time_of_day=event_time_of_day,
        product_category=product_category,
        base_market_price=base_market_price,
        **kwargs
    )
