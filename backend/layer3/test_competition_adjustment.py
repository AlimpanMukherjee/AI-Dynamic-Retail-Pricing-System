import pytest
import backend.config as cfg
from backend.layer3.scoring_engine import PricingScorer

def test_competition_adjustment_scenarios(monkeypatch):
    # Setup test configuration values
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", True)
    monkeypatch.setattr(cfg, "COMPETITIVE_PRICING_ADJUSTMENT_WEIGHT", 0.35)
    monkeypatch.setattr(cfg, "COMPETITIVE_PRICING_GAP_TOLERANCE", 0.02)
    monkeypatch.setattr(cfg, "MAX_COMPETITIVE_PRICING_ADJUSTMENT", 0.15)
    monkeypatch.setattr(cfg, "MIN_COMPETITOR_SAMPLE_SIZE", 3)
    monkeypatch.setattr(cfg, "COMPETITIVE_GAP_LEVELS", {"low": 0.05, "medium": 0.10, "high": 0.20})
    monkeypatch.setattr(cfg, "COMPETITIVE_GAP_MULTIPLIERS", {"low": 1.0, "medium": 1.35, "high": 1.75})

    scorer = PricingScorer()

    # Base pricing state structure
    base_state = {
        "E1": {"minimum_safe_price": 10.0, "true_landed_cost": 8.0, "supply_risk": 0.0, "cost_volatility": 0.0},
        "E2": {"optimal_price": 12.0, "expected_demand": 50.0, "elasticity": -1.0},
        "E3": {"inventory_pressure": 0.0, "urgency_score": 0.0, "recommended_multiplier": 1.0},
        "E5": {"event_score": 0.0}
    }
    
    # Base weights
    weights = {
        "E1_weight": 0.25,
        "E2_weight": 0.25,
        "E3_weight": 0.25,
        "E4_weight": 0.25,
        "E5_weight": 0.0
    }

    # Scenario 1: Candidate price is below competitor median -> Adjustment should be 0.0
    state_s1 = base_state.copy()
    state_s1["E4"] = {
        "median_competitor_price": 15.0,
        "market_pressure": 0.8,
        "recommended_multiplier": 1.0,
        "competitor_count": 5
    }
    # Candidate price = 14.0 (below median 15.0)
    res_s1 = scorer.score_candidate(14.0, state_s1, weights)
    # If gap is 0, final_score = base blended score (which is ~0.8-0.9 depending on other engines)
    # Let's verify by disabling it and comparing
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", False)
    res_disabled = scorer.score_candidate(14.0, state_s1, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", True)
    assert res_s1["final_score"] == res_disabled["final_score"]

    # Scenario 2: Gap is below tolerance (2%) -> Adjustment should be 0.0
    # Median = 100.0, Candidate = 101.5 (gap = 1.5% < 2%)
    state_s2 = base_state.copy()
    state_s2["E4"] = {
        "median_competitor_price": 100.0,
        "market_pressure": 0.8,
        "recommended_multiplier": 1.0,
        "competitor_count": 4
    }
    res_s2 = scorer.score_candidate(101.5, state_s2, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", False)
    res_disabled = scorer.score_candidate(101.5, state_s2, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", True)
    assert res_s2["final_score"] == res_disabled["final_score"]

    # Scenario 3: Gap levels low, medium, high multipliers
    # Base weight = 0.35, market_pressure = 0.80, recommended_multiplier = 1.0 (market_factor = 0.8 * 1.0 = 0.8)
    state_s3 = base_state.copy()
    state_s3["E4"] = {
        "median_competitor_price": 100.0,
        "market_pressure": 0.8,
        "recommended_multiplier": 1.0,
        "competitor_count": 3
    }
    
    # 3a) Low Gap (e.g. 4% -> severity = 1.0)
    # gap = 0.04. adjustment = 0.04 * 0.8 * 1.0 * 0.35 = 0.0112
    res_s3_low = scorer.score_candidate(104.0, state_s3, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", False)
    res_disabled_low = scorer.score_candidate(104.0, state_s3, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", True)
    assert abs((res_disabled_low["final_score"] - res_s3_low["final_score"]) - 0.0112) < 1e-4

    # 3b) Medium Gap (e.g. 8% -> severity = 1.35)
    # gap = 0.08. adjustment = 0.08 * 0.8 * 1.35 * 0.35 = 0.03024
    res_s3_med = scorer.score_candidate(108.0, state_s3, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", False)
    res_disabled_med = scorer.score_candidate(108.0, state_s3, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", True)
    assert abs((res_disabled_med["final_score"] - res_s3_med["final_score"]) - 0.03024) < 1e-4

    # 3c) High Gap (e.g. 15% -> severity = 1.75)
    # gap = 0.15. adjustment = 0.15 * 0.8 * 1.75 * 0.35 = 0.0735
    res_s3_high = scorer.score_candidate(115.0, state_s3, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", False)
    res_disabled_high = scorer.score_candidate(115.0, state_s3, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", True)
    assert abs((res_disabled_high["final_score"] - res_s3_high["final_score"]) - 0.0735) < 1e-4

    # Scenario 4: Capping at MAX_COMPETITIVE_PRICING_ADJUSTMENT (0.15)
    # Large gap: 40% (0.40) -> severity = 1.75
    # raw adjustment = 0.40 * 0.8 * 1.75 * 0.35 = 0.196
    # capped at 0.15
    res_s4 = scorer.score_candidate(140.0, state_s3, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", False)
    res_disabled_s4 = scorer.score_candidate(140.0, state_s3, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", True)
    assert abs((res_disabled_s4["final_score"] - res_s4["final_score"]) - 0.15) < 1e-4

    # Scenario 5: Disabled adjustment configuration behavior
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", False)
    res_s5 = scorer.score_candidate(115.0, state_s3, weights)
    assert res_s5["final_score"] == res_disabled_high["final_score"]
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", True)

    # Scenario 6: Missing or invalid competitor data (median_competitor_price <= 0 or market_pressure <= 0)
    state_s6_invalid_price = base_state.copy()
    state_s6_invalid_price["E4"] = {
        "median_competitor_price": 0.0,
        "market_pressure": 0.8,
        "recommended_multiplier": 1.0,
        "competitor_count": 5
    }
    res_s6_price = scorer.score_candidate(115.0, state_s6_invalid_price, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", False)
    res_disabled_s6 = scorer.score_candidate(115.0, state_s6_invalid_price, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", True)
    assert res_s6_price["final_score"] == res_disabled_s6["final_score"]

    state_s6_invalid_pressure = base_state.copy()
    state_s6_invalid_pressure["E4"] = {
        "median_competitor_price": 100.0,
        "market_pressure": 0.0,
        "recommended_multiplier": 1.0,
        "competitor_count": 5
    }
    res_s6_pressure = scorer.score_candidate(115.0, state_s6_invalid_pressure, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", False)
    res_disabled_s6_pressure = scorer.score_candidate(115.0, state_s6_invalid_pressure, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", True)
    assert res_s6_pressure["final_score"] == res_disabled_s6_pressure["final_score"]

    # Scenario 7: Insufficient competitor sample size (competitor_count < MIN_COMPETITOR_SAMPLE_SIZE)
    state_s7 = base_state.copy()
    state_s7["E4"] = {
        "median_competitor_price": 100.0,
        "market_pressure": 0.8,
        "recommended_multiplier": 1.0,
        "competitor_count": 2 # less than MIN_COMPETITOR_SAMPLE_SIZE=3
    }
    res_s7 = scorer.score_candidate(115.0, state_s7, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", False)
    res_disabled_s7 = scorer.score_candidate(115.0, state_s7, weights)
    monkeypatch.setattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", True)
    assert res_s7["final_score"] == res_disabled_s7["final_score"]
