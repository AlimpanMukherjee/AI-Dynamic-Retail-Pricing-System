import numpy as np
import logging
from typing import Dict, Any
import backend.config as cfg

# Configure logging
logger = logging.getLogger("pricing_system.layer3.scoring_engine")

class PricingScorer:
    """
    Computes domain-specific scores (Procurement, Elasticity, Inventory, Market)
    for price candidates and blends them using Layer 2 dynamic weights.
    """
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initializes the PricingScorer with configurable parameters.
        
        Parameters:
            config (dict): Score sensitivity and boundary configurations:
                - target_margin (float): Target profit margin for procurement scoring (default: 0.25).
                - revenue_volume_split (float): Weight of revenue vs sales volume in elasticity score (default: 0.8 for revenue).
                - inventory_penalty_factor (float): Penalty scale for deviating from inventory target price (default: 5.0).
                - market_competitiveness_factor (float): Penalty scale for pricing above competitor band (default: 8.0).
                - underprice_penalty_factor (float): Penalty scale for pricing below competitor band (default: 2.0).
        """
        self.config = config or {}
        self.target_margin = self.config.get("target_margin", 0.25)
        self.revenue_volume_split = self.config.get("revenue_volume_split", 0.8)
        self.inventory_penalty_factor = self.config.get("inventory_penalty_factor", 5.0)
        self.market_competitiveness_factor = self.config.get("market_competitiveness_factor", 8.0)
        self.underprice_penalty_factor = self.config.get("underprice_penalty_factor", 2.0)

    def calculate_procurement_score(self, price: float, pricing_state: Dict[str, Any]) -> float:
        """
        Calculates the Procurement Score (0 to 1).
        - Discards margins below the minimum safe price.
        - Rewards prices that achieve target profit margins.
        - Penalizes low-margin candidates if supply risk or cost volatility is high.
        """
        e1_data = pricing_state.get("E1", {})
        min_safe_price = float(e1_data.get("minimum_safe_price", 0.0))
        true_landed_cost = float(e1_data.get("true_landed_cost", 0.0))
        supply_risk = float(e1_data.get("supply_risk", 0.0))
        cost_volatility = float(e1_data.get("cost_volatility", 0.0))

        # Absolute check
        if price < min_safe_price:
            return 0.0

        # Estimate the target price needed to achieve the target margin
        # price = landed_cost / (1 - margin)
        if self.target_margin < 1.0:
            target_price = true_landed_cost / (1.0 - self.target_margin)
        else:
            target_price = min_safe_price * 1.5

        # If target price is less than minimum safe price, push it higher
        if target_price <= min_safe_price:
            target_price = min_safe_price * 1.3

        # Base margin score: linear interpolation between min_safe_price (0.5) and target_price (1.0)
        if price >= target_price:
            base_score = 1.0
        else:
            base_score = 0.5 + 0.5 * ((price - min_safe_price) / (target_price - min_safe_price))

        # Supply risk and cost volatility adjust the score
        # High risk requires a higher risk buffer (meaning we penalize prices closer to the safety floor)
        risk_index = (0.7 * supply_risk) + (0.3 * cost_volatility)
        
        # Penalize up to 20% of the score depending on risk and closeness to minimum safe price
        closeness_to_floor = max(0.0, 1.0 - ((price - min_safe_price) / (target_price - min_safe_price + 1e-5)))
        penalty = 0.2 * risk_index * closeness_to_floor
        
        procurement_score = float(np.clip(base_score - penalty, 0.0, 1.0))
        return procurement_score

    def calculate_elasticity_score(self, price: float, pricing_state: Dict[str, Any]) -> float:
        """
        Calculates the Demand Elasticity Score (0 to 1).
        - Estimates expected demand using point elasticity: Q = Q_opt * (P / P_opt)^elasticity.
        - Calculates revenue potential: R = P * Q.
        - Normalizes revenue and volume to produce a blended score.
        """
        e2_data = pricing_state.get("E2", {})
        optimal_price = float(e2_data.get("optimal_price", 0.0))
        expected_demand_opt = float(e2_data.get("expected_demand", 0.0))
        elasticity = float(e2_data.get("elasticity", 0.0))

        if optimal_price <= 0 or expected_demand_opt <= 0:
            # Fallback if E2 outputs are invalid
            return 1.0

        # Treat positive elasticity or near-zero noise as 0 (inelastic/flat demand)
        # Point elasticity calculation is valid for negative values
        epsilon = min(0.0, elasticity)

        # Estimate demand at the candidate price
        # Q(P) = Q_opt * (P / P_opt) ^ epsilon
        # To avoid division by zero or extreme numbers, clip the price ratio
        price_ratio = price / optimal_price
        
        # Point elasticity formula
        estimated_demand = expected_demand_opt * (price_ratio ** epsilon)
        
        # Revenue calculation
        estimated_revenue = price * estimated_demand
        max_revenue = optimal_price * expected_demand_opt

        # Normalize revenue score (0 to 1)
        revenue_score = float(np.clip(estimated_revenue / (max_revenue + 1e-5), 0.0, 1.0))

        # Normalize volume score (0 to 1) relative to the optimal price demand
        volume_score = float(np.clip(estimated_demand / (expected_demand_opt + 1e-5), 0.0, 1.0))

        # Blend revenue score and volume score
        w_rev = self.revenue_volume_split
        w_vol = 1.0 - w_rev
        elasticity_score = (w_rev * revenue_score) + (w_vol * volume_score)
        
        return float(np.clip(elasticity_score, 0.0, 1.0))

    def calculate_inventory_score(self, price: float, pricing_state: Dict[str, Any]) -> float:
        """
        Calculates the Inventory Score (0 to 1) using an asymmetric penalty.
        - If overstocked: penalizes prices ABOVE the inventory-adjusted price.
        - If understocked (stockout risk): penalizes prices BELOW the inventory-adjusted price.
        - Returns 1.0 if stock is balanced.
        """
        e2_data = pricing_state.get("E2", {})
        optimal_price = float(e2_data.get("optimal_price", 0.0))
        
        e3_data = pricing_state.get("E3", {})
        inventory_pressure = float(e3_data.get("inventory_pressure", 0.0))
        urgency_score = float(e3_data.get("urgency_score", 0.0))
        recommended_multiplier = float(e3_data.get("recommended_multiplier", 1.0))

        if optimal_price <= 0:
            return 1.0

        # Calculate target inventory price anchor
        target_inv_price = optimal_price * recommended_multiplier

        # Case 1: Overstock (inventory_pressure > 0)
        # We need to clear stock, so lower prices are favored. Prices above target_inv_price are penalized.
        if inventory_pressure > 0:
            if price <= target_inv_price:
                inventory_score = 1.0
            else:
                deviation = (price - target_inv_price) / target_inv_price
                penalty = np.exp(-self.inventory_penalty_factor * urgency_score * (deviation ** 2))
                inventory_score = penalty

        # Case 2: Understock / Stockout Risk (inventory_pressure < 0)
        # We want to conserve stock and increase price. Prices below target_inv_price are penalized.
        elif inventory_pressure < 0:
            if price >= target_inv_price:
                inventory_score = 1.0
            else:
                deviation = (target_inv_price - price) / target_inv_price
                penalty = np.exp(-self.inventory_penalty_factor * urgency_score * (deviation ** 2))
                inventory_score = penalty

        # Case 3: Balanced Inventory (inventory_pressure == 0)
        else:
            inventory_score = 1.0

        return float(np.clip(inventory_score, 0.0, 1.0))

    def calculate_market_score(self, price: float, pricing_state: Dict[str, Any]) -> float:
        """
        Calculates the Market Competitiveness Score (0 to 1).
        - High score within competitor band.
        - Severe exponential penalty if pricing above competitor max (scaled by market pressure).
        - Mild penalty if pricing below competitor min (underpricing safety).
        """
        e4_data = pricing_state.get("E4", {})
        competitor_band = e4_data.get("competitor_band", None)
        market_pressure = float(e4_data.get("market_pressure", 0.0))

        if not competitor_band or not isinstance(competitor_band, list) or len(competitor_band) != 2:
            # Fallback if competitor band is missing
            return 1.0

        min_comp = float(competitor_band[0])
        max_comp = float(competitor_band[1])

        # If competitor prices are extremely low or zero, guard against issues
        if min_comp <= 0:
            return 1.0

        # Case 1: Above competitor band (price > max_comp)
        # High uncompetitiveness, heavily penalized if competitor pressure is high
        if price > max_comp:
            deviation = (price - max_comp) / max_comp
            # Penalty increases with market pressure and deviation
            penalty = np.exp(-self.market_competitiveness_factor * market_pressure * (deviation ** 2))
            market_score = penalty

        # Case 2: Below competitor band (price < min_comp)
        # Underpriced - very competitive, but we might be leaving money on the table.
        # Apply a mild penalty to discourage excessive undercutting.
        elif price < min_comp:
            deviation = (min_comp - price) / min_comp
            penalty = np.exp(-self.underprice_penalty_factor * (deviation ** 2))
            market_score = penalty

        # Case 3: Inside competitor band (min_comp <= price <= max_comp)
        # Score is high. If competitor pressure is high, we prefer being closer to min_comp.
        # If competitor pressure is low, we can price closer to max_comp without penalty.
        else:
            if max_comp > min_comp:
                position_ratio = (price - min_comp) / (max_comp - min_comp)
            else:
                position_ratio = 0.0
            
            # If market_pressure is 1.0, we penalize higher prices in the band.
            # If market_pressure is 0.0, there is no penalty inside the band.
            market_score = 1.0 - 0.3 * market_pressure * position_ratio

        return float(np.clip(market_score, 0.0, 1.0))

    def score_candidate(self, price: float, pricing_state: Dict[str, Any], weights: Dict[str, float]) -> Dict[str, Any]:
        """
        Scores a single candidate price across all dimensions and calculates
        the final weighted score incorporating E5 Event component.
        
        Parameters:
            price (float): The price candidate.
            pricing_state (dict): The outputs from Layer 1 specialist engines.
            weights (dict): Layer 2 engine weights mapping.
            
        Returns:
            dict: The candidate price, sub-scores, and the final blended score.
        """
        procurement_score = self.calculate_procurement_score(price, pricing_state)
        elasticity_score = self.calculate_elasticity_score(price, pricing_state)
        inventory_score = self.calculate_inventory_score(price, pricing_state)
        market_score = self.calculate_market_score(price, pricing_state)

        # Retrieve weights
        w1 = weights.get("E1_weight", 0.25)
        w2 = weights.get("E2_weight", 0.25)
        w3 = weights.get("E3_weight", 0.25)
        w4 = weights.get("E4_weight", 0.25)
        w5 = weights.get("E5_weight", 0.0)

        # Retrieve event properties
        event_active = pricing_state.get("event_active", False)
        current_price = pricing_state.get("current_price", 0.0)
        
        if event_active and current_price > 0:
            e5_data = pricing_state.get("E5", {})
            event_score = float(e5_data.get("event_score", 0.0))
            price_increase_ratio = (price - current_price) / current_price
            # Upward-only pricing reward: max(0.0, price_increase_ratio)
            event_component = w5 * event_score * max(0.0, price_increase_ratio)
        else:
            event_score = 0.0
            event_component = 0.0

        # Blended weighted score
        final_score = (
            (w1 * procurement_score) + 
            (w2 * elasticity_score) + 
            (w3 * inventory_score) + 
            (w4 * market_score) + 
            event_component
        )

        # Compute Competitive Score Adjustment if enabled
        enable_adjustment = getattr(cfg, "ENABLE_COMPETITIVE_PRICING_ADJUSTMENT", True)
        competitive_score_adjustment = 0.0
        
        if enable_adjustment:
            e4_data = pricing_state.get("E4", {})
            competitor_median_price = float(e4_data.get("median_competitor_price", 0.0))
            market_pressure = float(e4_data.get("market_pressure", 0.0))
            recommended_multiplier = float(e4_data.get("recommended_multiplier", 1.0))
            competitor_count = int(e4_data.get("competitor_count", 0))
            min_sample_size = getattr(cfg, "MIN_COMPETITOR_SAMPLE_SIZE", 3)
            
            # Verify that competitor data exists and is reliable
            if competitor_median_price > 0 and market_pressure > 0 and competitor_count >= min_sample_size:
                competitive_gap_pct = max(0.0, (price - competitor_median_price) / competitor_median_price)
                
                # Ignore very small pricing differences below tolerance
                gap_tolerance = getattr(cfg, "COMPETITIVE_PRICING_GAP_TOLERANCE", 0.02)
                if competitive_gap_pct >= gap_tolerance:
                    # Determine severity level multiplier
                    levels = getattr(cfg, "COMPETITIVE_GAP_LEVELS", {"low": 0.05, "medium": 0.10, "high": 0.20})
                    multipliers = getattr(cfg, "COMPETITIVE_GAP_MULTIPLIERS", {"low": 1.0, "medium": 1.35, "high": 1.75})
                    
                    if competitive_gap_pct <= levels.get("low", 0.05):
                        severity = multipliers.get("low", 1.0)
                    elif competitive_gap_pct <= levels.get("medium", 0.10):
                        severity = multipliers.get("medium", 1.35)
                    else:
                        severity = multipliers.get("high", 1.75)
                    
                    # Scale penalty directionally: stronger when E4 recommends lowering price (recommended_multiplier < 1.0)
                    market_factor = market_pressure * max(0.5, 2.0 - recommended_multiplier)
                    
                    # Competitive adjustment is intentionally a soft penalty.
                    # It nudges Layer 3 toward market-competitive prices without
                    # overriding procurement safety, demand elasticity or inventory logic.
                    base_weight = getattr(cfg, "COMPETITIVE_PRICING_ADJUSTMENT_WEIGHT", 0.35)
                    max_adj = getattr(cfg, "MAX_COMPETITIVE_PRICING_ADJUSTMENT", 0.15)
                    competitive_score_adjustment = min(
                        competitive_gap_pct * market_factor * severity * base_weight,
                        max_adj
                    )

        # Apply internal Competitive Score Adjustment (ranking only)
        final_score = max(0.0, final_score - competitive_score_adjustment)

        return {
            "price": price,
            "procurement_score": float(round(procurement_score, 4)),
            "elasticity_score": float(round(elasticity_score, 4)),
            "inventory_score": float(round(inventory_score, 4)),
            "market_score": float(round(market_score, 4)),
            "event_score": float(round(event_score, 4)),
            "event_component": float(round(event_component, 4)),
            "final_score": float(round(final_score, 4))
        }
