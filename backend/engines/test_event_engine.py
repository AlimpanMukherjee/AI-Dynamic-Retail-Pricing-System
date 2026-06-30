import pytest
from backend.engines.event_engine import run_pipeline, EventEngine

def test_scenario_1_no_event():
    # Scenario 1: No Event -> Expected: no price change
    result = run_pipeline(
        event_active=False,
        event_type="Festival",
        attendance=50000,
        distance_km=2.0,
        duration_hours=4.0,
        event_time_of_day="Evening",
        product_category="Soft Drinks",
        expected_demand=100.0,
        available_inventory=50.0,
        base_price=50.0,
        base_market_price=60.0
    )
    assert result["recommended_uplift_pct"] == 0.0
    assert result["event_price_increase"] == 0.0
    assert result["decision"] == "No Price Increase"

def test_scenario_2_large_event_high_inventory():
    # Scenario 2: Large event, high inventory -> expected: increased demand, but no price change
    # expected_demand = 120.0, duration = 3.0 hr, store operational hours = 12 -> demand_during_event = 30
    # multiplier will increase it, but inventory = 1000 is ample.
    result = run_pipeline(
        event_active=True,
        event_type="Festival",
        attendance=50000,
        distance_km=1.0,
        duration_hours=3.0,
        event_time_of_day="Evening",
        product_category="Soft Drinks",
        expected_demand=120.0,
        available_inventory=1000.0,
        elasticity=-1.5,
        base_price=50.0,
        base_market_price=60.0
    )
    assert result["expected_shortage"] == 0.0
    assert result["recommended_uplift_pct"] == 0.0
    assert result["decision"] == "No Price Increase"

def test_scenario_3_large_event_low_inventory():
    # Scenario 3: Large event, low inventory -> expected: positive price increase
    result = run_pipeline(
        event_active=True,
        event_type="Festival",
        attendance=50000,
        distance_km=1.0,
        duration_hours=3.0,
        event_time_of_day="Evening",
        product_category="Soft Drinks",
        expected_demand=120.0,
        available_inventory=10.0,
        elasticity=-1.5,
        base_price=50.0,
        base_market_price=60.0
    )
    assert result["expected_shortage"] >= 5.0
    assert result["recommended_uplift_pct"] > 0.0
    assert result["decision"] in ["Increase Price", "Increase Capped"]

def test_scenario_4_highly_elastic_product():
    # Scenario 4: Highly elastic product -> expected: modest price increase
    # High elasticity = -4.0, should suppress price increase
    result_elastic = run_pipeline(
        event_active=True,
        event_type="Concert",
        attendance=20000,
        distance_km=1.0,
        duration_hours=4.0,
        event_time_of_day="Evening",
        product_category="Soft Drinks",
        expected_demand=100.0,
        available_inventory=30.0,
        elasticity=-4.0,
        base_price=10.0,
        base_market_price=15.0
    )
    result_inelastic = run_pipeline(
        event_active=True,
        event_type="Concert",
        attendance=20000,
        distance_km=1.0,
        duration_hours=4.0,
        event_time_of_day="Evening",
        product_category="Soft Drinks",
        expected_demand=100.0,
        available_inventory=30.0,
        elasticity=-1.0,
        base_price=10.0,
        base_market_price=15.0
    )
    assert result_elastic["recommended_uplift_pct"] < result_inelastic["recommended_uplift_pct"]

def test_scenario_5_highly_inelastic_product():
    # Scenario 5: Highly inelastic product -> expected: calculated increase capped at 20%
    # Low elasticity = -0.1 -> safeguarded to 0.2
    # expected_demand = 100, inventory = 5 -> shortage will be severe -> required demand reduction high
    result = run_pipeline(
        event_active=True,
        event_type="Sports Match",
        attendance=50000,
        distance_km=0.5,
        duration_hours=6.0,
        event_time_of_day="Evening",
        product_category="Soft Drinks",
        expected_demand=100.0,
        available_inventory=5.0,
        elasticity=-0.1,
        base_price=50.0,
        base_market_price=100.0
    )
    assert result["recommended_uplift_pct"] == 0.20  # capped at 20%
    assert result["decision"] == "Increase Capped"
    assert result["constraint_applied"] == "Maximum Increase Cap"

def test_scenario_6_low_relevance_category():
    # Scenario 6: Low relevance category (Furniture) during Sports Match -> minimal demand increase
    result = run_pipeline(
        event_active=True,
        event_type="Sports Match",
        attendance=50000,
        distance_km=0.5,
        duration_hours=3.0,
        event_time_of_day="Evening",
        product_category="Furniture",
        expected_demand=10.0,
        available_inventory=5.0,
        elasticity=-1.5,
        base_price=1000.0,
        base_market_price=1200.0
    )
    # Event strength might be high, but demand multiplier will be scaled down by Furniture relevance (0.10)
    assert result["event_multiplier"] < 1.05

def test_scenario_7_high_relevance_category():
    # Scenario 7: High relevance category (Soft Drinks) during Festival -> significant increase
    result = run_pipeline(
        event_active=True,
        event_type="Festival",
        attendance=50000,
        distance_km=1.0,
        duration_hours=6.0,
        event_time_of_day="Evening",
        product_category="Soft Drinks",
        expected_demand=100.0,
        available_inventory=10.0,
        elasticity=-1.5,
        base_price=50.0,
        base_market_price=60.0
    )
    assert result["event_multiplier"] > 1.15
    assert result["decision"] in ["Increase Price", "Increase Capped"]


