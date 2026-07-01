import pytest
import backend.config as cfg
from backend.engines.event_engine import run_pipeline, EventEngine

def test_scenario_1_no_event():
    # Scenario 1: No Event -> Expected: no price change
    result = run_pipeline(
        event_active=False,
        projected_event_demand=100.0,
        available_inventory=50.0,
        elasticity=-1.5,
        base_market_price=60.0
    )
    assert result["recommended_price_increase_pct"] == 0.0
    assert result["decision"] == "No Price Increase"
    assert result["stock_sufficient"] is True

def test_scenario_2_large_event_high_inventory():
    # Scenario 2: Event active, high inventory -> expected: 100% coverage, no price change
    result = run_pipeline(
        event_active=True,
        projected_event_demand=50.0,
        available_inventory=100.0,
        elasticity=-1.5,
        base_market_price=60.0
    )
    assert result["inventory_coverage"] == 1.0
    assert result["recommended_price_increase_pct"] == 0.0
    assert result["decision"] == "No Price Increase"
    assert result["stock_sufficient"] is True

def test_scenario_3_large_event_low_inventory():
    # Scenario 3: Event active, low inventory -> expected: shortage and positive price increase
    result = run_pipeline(
        event_active=True,
        projected_event_demand=100.0,
        available_inventory=10.0,
        elasticity=-1.5,
        base_market_price=60.0
    )
    assert result["stock_sufficient"] is False
    assert result["inventory_shortage"] == 90.0
    assert result["inventory_coverage"] == 0.10
    assert result["recommended_price_increase_pct"] > 0.0
    assert result["decision"] in ["Increase Price", "Increase Capped"]

def test_scenario_4_highly_elastic_product():
    # Scenario 4: Highly elastic product -> expected: modest price increase compared to inelastic
    result_elastic = run_pipeline(
        event_active=True,
        projected_event_demand=50.0,
        available_inventory=40.0,
        elasticity=-4.0, # highly elastic
        base_market_price=15.0
    )
    result_inelastic = run_pipeline(
        event_active=True,
        projected_event_demand=50.0,
        available_inventory=40.0,
        elasticity=-0.5, # inelastic
        base_market_price=15.0
    )
    assert result_elastic["recommended_price_increase_pct"] < result_inelastic["recommended_price_increase_pct"]

def test_scenario_5_highly_inelastic_product():
    # Scenario 5: Highly inelastic product -> expected: calculated increase capped at MAX_EVENT_PRICE_INCREASE
    # By default MAX_EVENT_PRICE_INCREASE is 0.20
    result = run_pipeline(
        event_active=True,
        projected_event_demand=100.0,
        available_inventory=5.0,
        elasticity=-0.1,
        base_market_price=100.0
    )
    assert result["recommended_price_increase_pct"] == 0.20  # capped at 20%
    assert result["decision"] == "Increase Capped"
    assert result["constraint_applied"] == "Maximum Increase Cap"

def test_scenario_6_demand_sanity_warnings():
    # Scenario 6: Extremely high demand triggers warning
    result = run_pipeline(
        event_active=True,
        projected_event_demand=500.0,
        available_inventory=10.0,
        elasticity=-1.5,
        sales_velocity_per_day=1.0, # limit warning_mult=20 -> 20 * 1 = 20 units. 500 > 20 -> triggers warning
        base_market_price=60.0
    )
    assert len(result["warnings"]) > 0
    assert "Projected demand" in result["warnings"][0]

def test_scenario_7_none_elasticity():
    # Scenario 7: elasticity is None -> should fall back to cfg.DEFAULT_ELASTICITY
    result = run_pipeline(
        event_active=True,
        projected_event_demand=100.0,
        available_inventory=50.0,
        elasticity=None,
        base_market_price=60.0
    )
    assert result["elasticity"] == -cfg.DEFAULT_ELASTICITY

