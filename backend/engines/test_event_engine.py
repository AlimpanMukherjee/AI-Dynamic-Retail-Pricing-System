import pytest
from backend.engines.event_engine import run_pipeline, EventEngine

def test_event_engine_inactive():
    # When event is not active, score must be 0 and level LOW
    result = run_pipeline(
        event_active=False,
        event_type="Sports Match",
        attendance=50000,
        distance_km=0.5,
        duration_hours=3.0,
        product_category="Beverages"
    )
    assert result["event_score"] == 0.0
    assert result["impact_level"] == "LOW"
    assert result["effective_uplift_pct"] == 0.0
    assert result["event_opportunity_score"] == 0.0

def test_event_engine_active_extreme():
    # Strong event: Festival, 100k people, very close (0.1km), long duration (48h), Beverages
    result = run_pipeline(
        event_active=True,
        event_type="Festival",
        attendance=100000,
        distance_km=0.1,
        duration_hours=48.0,
        product_category="Beverages"
    )
    assert result["event_score"] > 0.6
    assert result["impact_level"] == "EXTREME"
    assert result["event_type"] == "Festival"
    assert result["attendance"] == 100000
    assert result["event_relevance"] == 1.5
    assert "Soft Drinks Category" in result["reasoning"]

def test_event_engine_active_low():
    # Weak event: Local Fair, 100 people, far away (10km), short duration (1h), Staples
    result = run_pipeline(
        event_active=True,
        event_type="Local Fair",
        attendance=100,
        distance_km=10.0,
        duration_hours=1.0,
        product_category="Staples"
    )
    assert result["event_score"] < 0.25
    assert result["impact_level"] == "LOW"

def test_event_engine_impact_levels():
    engine = EventEngine()
    # Test low classification
    res_low = engine.run(
        event_active=True, 
        event_type="Other", 
        attendance=0, 
        distance_km=10.0, 
        duration_hours=1.0,
        product_category="Staples"
    )
    assert res_low["impact_level"] == "LOW"
    
    # Test high/extreme classification
    res_high = engine.run(
        event_active=True, 
        event_type="Festival", 
        attendance=50000, 
        distance_km=0.1, 
        duration_hours=24.0,
        product_category="Beverages"
    )
    assert res_high["impact_level"] in ["HIGH", "EXTREME"]
