import pytest
import numpy as np
from backend.layer2.heuristic_weight_generator import generate_heuristic_weights

def test_scenario1_healthy_business():
    # Healthy business scenario: low supply risk, normal stock pressure, normal market pressure
    pricing_state = {
        "E1": {"supply_risk": 0.25},
        "E2": {"elasticity": -1.2},
        "E3": {"inventory_pressure": 0.1, "urgency_score": 0.1},
        "E4": {"market_pressure": 0.5, "competitive_gap": 0.0}
    }
    business_context = {
        "retailer_type": "standard",
        "business_strategy": "balanced",
        "region": "suburban"
    }
    
    weights = generate_heuristic_weights(pricing_state, business_context)
    
    assert len(weights) == 4
    assert np.all(weights > 0.0)
    assert np.isclose(np.sum(weights), 1.0)
    # Balanced weights: no single engine dominates excessively
    assert all(w < 0.45 for w in weights)

def test_scenario2_procurement_crisis():
    # Severe procurement risk scenario: supply_risk = 0.95
    pricing_state = {
        "E1": {"supply_risk": 0.95},
        "E2": {"elasticity": 0.0},
        "E3": {"inventory_pressure": 0.1, "urgency_score": 0.1},
        "E4": {"market_pressure": 0.5, "competitive_gap": 0.0}
    }
    business_context = {
        "retailer_type": "standard",
        "business_strategy": "balanced"
    }
    
    weights = generate_heuristic_weights(pricing_state, business_context)
    
    assert np.isclose(np.sum(weights), 1.0)
    # E1 should be noticeably more influential (E1 weight should be high, > 0.40)
    # E1 weight is index 0
    assert weights[0] > 0.40
    
    # Compare against standard scenario (supply_risk = 0.25)
    pricing_state_normal = {
        "E1": {"supply_risk": 0.25},
        "E2": {"elasticity": 0.0},
        "E3": {"inventory_pressure": 0.1, "urgency_score": 0.1},
        "E4": {"market_pressure": 0.5, "competitive_gap": 0.0}
    }
    weights_normal = generate_heuristic_weights(pricing_state_normal, business_context)
    assert weights[0] > weights_normal[0] + 0.10

def test_scenario3_inventory_crisis():
    # Severe inventory crisis scenario: inventory_pressure = -1.0, urgency_score = 1.0
    pricing_state = {
        "E1": {"supply_risk": 0.25},
        "E2": {"elasticity": 0.0},
        "E3": {"inventory_pressure": -1.0, "urgency_score": 1.0},
        "E4": {"market_pressure": 0.5, "competitive_gap": 0.0}
    }
    business_context = {
        "retailer_type": "standard",
        "business_strategy": "balanced"
    }
    
    weights = generate_heuristic_weights(pricing_state, business_context)
    
    assert np.isclose(np.sum(weights), 1.0)
    # E3 should be dominant (index 2)
    assert weights[2] == max(weights)
    assert weights[2] > 0.38

def test_scenario4_major_competitor_price_gap():
    # Major competitor gap scenario: competitive_gap = 2.0
    pricing_state = {
        "E1": {"supply_risk": 0.25},
        "E2": {"elasticity": 0.0},
        "E3": {"inventory_pressure": 0.1, "urgency_score": 0.1},
        "E4": {"market_pressure": 0.5, "competitive_gap": 2.0}
    }
    business_context = {
        "retailer_type": "standard",
        "business_strategy": "balanced"
    }
    
    weights = generate_heuristic_weights(pricing_state, business_context)
    
    assert np.isclose(np.sum(weights), 1.0)
    # E4 (index 3) should increase noticeably compared to gap = 0
    pricing_state_no_gap = {
        "E1": {"supply_risk": 0.25},
        "E2": {"elasticity": 0.0},
        "E3": {"inventory_pressure": 0.1, "urgency_score": 0.1},
        "E4": {"market_pressure": 0.5, "competitive_gap": 0.0}
    }
    weights_no_gap = generate_heuristic_weights(pricing_state_no_gap, business_context)
    
    assert weights[3] > weights_no_gap[3] + 0.05
    
    # Test negative gap sensitivity (both directions indicators of market signal)
    pricing_state_neg_gap = {
        "E1": {"supply_risk": 0.25},
        "E2": {"elasticity": 0.0},
        "E3": {"inventory_pressure": 0.1, "urgency_score": 0.1},
        "E4": {"market_pressure": 0.5, "competitive_gap": -2.0}
    }
    weights_neg_gap = generate_heuristic_weights(pricing_state_neg_gap, business_context)
    assert np.isclose(weights[3], weights_neg_gap[3])

def test_normalization_invariants_and_bounds():
    # Test extreme bounds to check if weights are always positive and sum to exactly 1.0
    # Also verify that floor of 0.05 is enforced
    pricing_state = {
        "E1": {"supply_risk": 1.0},
        "E2": {"elasticity": -10.0},
        "E3": {"inventory_pressure": -1.0, "urgency_score": 1.0},
        "E4": {"market_pressure": 1.0, "competitive_gap": 10.0}
    }
    business_context = {
        "retailer_type": "premium",
        "business_strategy": "margin_first"
    }
    weights = generate_heuristic_weights(pricing_state, business_context)
    
    assert len(weights) == 4
    assert np.all(weights >= 0.05)
    assert np.isclose(np.sum(weights), 1.0)
