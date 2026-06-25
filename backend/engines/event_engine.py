import logging
from backend.engines.event_config import EVENT_BASE_MULTIPLIERS
from backend.engines.event_category_mapper import get_category_relevance_multiplier, normalize_category

logger = logging.getLogger("pricing_system.engines.event_engine")

class EventEngine:
    """
    E5: Event Intelligence Engine.
    Evaluates temporary demand surges caused by crowd-based events near a store.
    Acts as a post-optimization business opportunity adjustment.
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
        product_category: str = "Other",
        elasticity: float = -1.0
    ) -> dict:
        """
        Calculates the event score, opportunity metrics, and post-optimization uplift.
        """
        # Return 0 score and empty impact if event is not active
        if not event_active:
            return {
                "event_active": False,
                "event_type": event_type,
                "attendance": int(attendance),
                "distance_km": float(distance_km),
                "duration_hours": float(duration_hours),
                "impact_level": "LOW",
                "event_relevance": 1.0,
                "event_opportunity_score": 0.0,
                "effective_uplift_pct": 0.0,
                "event_score": 0.0,
                "reasoning": []
            }

        # 1. Look up base multipliers
        event_multiplier = EVENT_BASE_MULTIPLIERS.get(event_type, 0.80)
        category_multiplier = get_category_relevance_multiplier(product_category, event_type)

        # 2. Calculate sub-factors
        attendance_factor = min(1.0, float(attendance) / 50000.0) if attendance > 0 else 0.0
        distance_factor = max(0.8, 1.0 - float(distance_km) / 50.0)
        duration_factor = min(float(duration_hours) / 8.0, 1.0) if duration_hours > 0 else 0.0

        # 3. New opportunity formula
        base_opportunity = 0.45 * attendance_factor + 0.30 * distance_factor + 0.25 * duration_factor
        event_score = base_opportunity * event_multiplier * category_multiplier
        event_score = round(max(0.0, event_score), 4)

        # 4. Opportunity score and uplift pct
        event_opportunity_score = round(min(100.0, event_score * 100.0), 1)
        effective_uplift_pct = round(min(0.20, event_score * 0.14), 4)

        # 5. Impact level mapping
        if event_score < 0.25:
            impact_level = "LOW"
        elif event_score < 0.50:
            impact_level = "MEDIUM"
        elif event_score < 0.85:
            impact_level = "HIGH"
        else:
            impact_level = "EXTREME"

        # 6. Generate reasoning narrative
        reasoning = []
        reasoning.append(event_type)

        # Attendance logic
        if attendance >= 40000:
            reasoning.append("Large Attendance")
        elif attendance >= 15000:
            reasoning.append("Moderate Attendance")
        else:
            reasoning.append("Small Attendance")

        # Category logic
        norm_cat = normalize_category(product_category)
        reasoning.append(f"{norm_cat} Category")

        # Distance proximity
        if distance_km <= 1.0:
            reasoning.append("Very Close To Venue")
        elif distance_km <= 3.0:
            reasoning.append("Close To Venue")
        else:
            reasoning.append("Moderate Proximity To Venue")

        # Add detail log
        logger.info(
            f"Executed Event Engine: opportunity_score={event_opportunity_score}%, "
            f"level={impact_level}, uplift={effective_uplift_pct:.2%} for type={event_type}"
        )

        return {
            "event_active": True,
            "event_type": event_type,
            "attendance": int(attendance),
            "distance_km": float(distance_km),
            "duration_hours": float(duration_hours),
            "impact_level": impact_level,
            "event_relevance": float(category_multiplier),
            "event_opportunity_score": event_opportunity_score,
            "effective_uplift_pct": effective_uplift_pct,
            "event_score": event_score,
            "reasoning": reasoning
        }

# Module-level run helper
def run_pipeline(
    event_active: bool = False,
    event_type: str = "Other",
    attendance: int = 0,
    distance_km: float = 2.0,
    duration_hours: float = 4.0,
    product_category: str = "Other",
    elasticity: float = -1.0
) -> dict:
    engine = EventEngine()
    return engine.run(
        event_active=event_active,
        event_type=event_type,
        attendance=attendance,
        distance_km=distance_km,
        duration_hours=duration_hours,
        product_category=product_category,
        elasticity=elasticity
    )
