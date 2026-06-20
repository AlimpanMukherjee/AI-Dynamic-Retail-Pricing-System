import logging

logger = logging.getLogger("pricing_system.engines.event_engine")

class EventEngine:
    """
    E5: Event Intelligence Engine.
    Captures temporary demand surges caused by crowd-based events near a store.
    """
    def __init__(self):
        pass

    def run(
        self,
        event_active: bool = False,
        event_type: str = "Other",
        attendance: int = 0,
        distance_km: float = 2.0,
        duration_hours: float = 4.0
    ) -> dict:
        """
        Calculates the event score and impact level based on event parameters.
        """
        # Return 0 score if event is not active
        if not event_active:
            return {
                "event_score": 0.0,
                "event_type": event_type,
                "attendance": int(attendance),
                "distance_km": float(distance_km),
                "duration_hours": float(duration_hours),
                "impact_level": "LOW"
            }

        # Base scores mapping by event type
        base_scores = {
            "Festival": 0.80,
            "Sports Match": 0.70,
            "Concert": 0.65,
            "Political Rally": 0.50,
            "Local Fair": 0.40,
            "Other": 0.30
        }
        
        base_score = base_scores.get(event_type, 0.30)
        
        # Calculate sub-factors
        # 1. Attendance factor: standard 50k attendance saturates factor to 1.0
        attendance_factor = min(1.0, float(attendance) / 50000.0) if attendance > 0 else 0.0
        
        # 2. Distance factor: reciprocal decay
        distance_factor = 1.0 / (1.0 + max(0.0, float(distance_km)))
        
        # 3. Duration factor: standard 24 hours saturates factor to 1.0
        duration_factor = min(1.0, float(duration_hours) / 24.0) if duration_hours > 0 else 0.0
        
        # Weighted event score formula
        raw_score = base_score * (
            0.4 * attendance_factor +
            0.4 * distance_factor +
            0.2 * duration_factor
        )
        
        event_score = min(1.0, max(0.0, float(raw_score)))
        event_score = round(event_score, 4)

        # Classification of impact level
        if event_score < 0.25:
            impact_level = "LOW"
        elif event_score < 0.50:
            impact_level = "MEDIUM"
        elif event_score < 0.85:
            impact_level = "HIGH"
        else:
            impact_level = "EXTREME"

        logger.info(f"Executed Event Engine: score={event_score}, level={impact_level} for type={event_type}")

        return {
            "event_score": event_score,
            "event_type": event_type,
            "attendance": int(attendance),
            "distance_km": float(distance_km),
            "duration_hours": float(duration_hours),
            "impact_level": impact_level
        }

# Module-level run helper
def run_pipeline(
    event_active: bool = False,
    event_type: str = "Other",
    attendance: int = 0,
    distance_km: float = 2.0,
    duration_hours: float = 4.0
) -> dict:
    engine = EventEngine()
    return engine.run(
        event_active=event_active,
        event_type=event_type,
        attendance=attendance,
        distance_km=distance_km,
        duration_hours=duration_hours
    )
