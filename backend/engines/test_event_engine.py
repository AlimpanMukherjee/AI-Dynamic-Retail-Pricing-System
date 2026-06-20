import pytest
from backend.engines.event_engine import run_pipeline, EventEngine

def test_event_engine_inactive():
    # When event is not active, score must be 0 and level LOW
    result = run_pipeline(
        event_active=False,
        event_type="Sports Match",
        attendance=50000,
        distance_km=0.5,
        duration_hours=3.0
    )
    assert result["event_score"] == 0.0
    assert result["impact_level"] == "LOW"

def test_event_engine_active_extreme():
    # Strong event: Festival, 100k people, very close (0.1km), long duration (48h)
    result = run_pipeline(
        event_active=True,
        event_type="Festival",
        attendance=100000,
        distance_km=0.1,
        duration_hours=48.0
    )
    assert result["event_score"] > 0.6
    assert result["impact_level"] in ["HIGH", "EXTREME"]
    assert result["event_type"] == "Festival"
    assert result["attendance"] == 100000
    assert result["distance_km"] == 0.1
    assert result["duration_hours"] == 48.0

def test_event_engine_active_low():
    # Weak event: Local Fair, 100 people, far away (10km), short duration (1h)
    result = run_pipeline(
        event_active=True,
        event_type="Local Fair",
        attendance=100,
        distance_km=10.0,
        duration_hours=1.0
    )
    assert result["event_score"] < 0.25
    assert result["impact_level"] == "LOW"

def test_event_engine_impact_levels():
    engine = EventEngine()
    # Test low classification
    res_low = engine.run(event_active=True, event_type="Other", attendance=0, distance_km=10.0, duration_hours=1.0)
    assert res_low["impact_level"] == "LOW"
    
    # Test high/extreme classification
    res_high = engine.run(event_active=True, event_type="Festival", attendance=50000, distance_km=0.1, duration_hours=24.0)
    assert res_high["impact_level"] in ["HIGH", "EXTREME"]
