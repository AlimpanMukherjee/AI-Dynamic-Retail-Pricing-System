import logging
from typing import Dict, List, Any

# Configure logging
logger = logging.getLogger("pricing_system.layer3.final_price_selector")

class FinalPriceSelector:
    """
    Selects the winning candidate price with the highest blended score,
    assembles the structured output, and generates business-readable explanations.
    """
    def __init__(self):
        pass

    def select_best_price(
        self,
        scored_candidates: List[Dict[str, Any]],
        pricing_state: Dict[str, Any],
        weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Evaluates the scored candidates and returns the winning price and structured meta-data.
        
        Parameters:
            scored_candidates (list): List of scored candidate dictionaries.
            pricing_state (dict): The outputs from Layer 1 specialist engines.
            weights (dict): Layer 2 engine weights mapping.
            
        Returns:
            dict: Structured pricing decision dictionary in the requested output format.
        """
        if not scored_candidates:
            raise ValueError("No scored price candidates available for selection.")

        # Find candidate with the maximum final_score
        winner = max(scored_candidates, key=lambda x: x["final_score"])

        # Extract values for qualitative summaries
        e1_data = pricing_state.get("E1", {})
        e3_data = pricing_state.get("E3", {})
        e4_data = pricing_state.get("E4", {})

        min_safe_price = float(e1_data.get("minimum_safe_price", 0.0))
        supply_risk_val = float(e1_data.get("supply_risk", 0.0))
        inventory_pressure_val = float(e3_data.get("inventory_pressure", 0.0))
        market_pressure_val = float(e4_data.get("market_pressure", 0.0))

        # Map numeric signals to qualitative descriptions ("high", "moderate", "low")
        def map_to_level(val: float, high_thresh: float = 0.7, mod_thresh: float = 0.3) -> str:
            abs_val = abs(val)
            if abs_val > high_thresh:
                return "high"
            elif abs_val > mod_thresh:
                return "moderate"
            else:
                return "low"

        decision_summary = {
            "inventory_pressure": map_to_level(inventory_pressure_val, high_thresh=0.5, mod_thresh=0.1),
            "market_pressure": map_to_level(market_pressure_val, high_thresh=0.7, mod_thresh=0.3),
            "supply_risk": map_to_level(supply_risk_val, high_thresh=0.7, mod_thresh=0.3)
        }

        # Build detailed human-readable explanation
        explanation = self._generate_explanation(
            winner=winner,
            pricing_state=pricing_state,
            weights=weights,
            decision_summary=decision_summary
        )

        price_journey = self._generate_price_journey(pricing_state, weights, float(winner["price"]))
        price_confidence = self._calculate_system_confidence(pricing_state)

        logger.info(f"[Layer3] Selected winning price candidate: ${winner['price']} with score {winner['final_score']}")
        print(f"[Layer3] Best candidate selected: ${winner['price']} (Score: {winner['final_score']})")

        return {
            "final_price": float(winner["price"]),
            "confidence": float(winner["final_score"]),
            "selected_price_score": float(winner["final_score"]),
            "winning_candidate": float(winner["price"]),
            "price_breakdown": {
                "procurement_score": float(winner["procurement_score"]),
                "elasticity_score": float(winner["elasticity_score"]),
                "inventory_score": float(winner["inventory_score"]),
                "market_score": float(winner["market_score"]),
                "event_score": float(winner.get("event_score", 0.0)),
                "event_component": float(winner.get("event_component", 0.0))
            },
            "decision_summary": decision_summary,
            "explanation": explanation,
            "price_journey": price_journey,
            "price_confidence": price_confidence
        }

    def _generate_explanation(
        self,
        winner: Dict[str, Any],
        pricing_state: Dict[str, Any],
        weights: Dict[str, float],
        decision_summary: Dict[str, str]
    ) -> str:
        """
        Generates a clear stakeholder-facing explanation of the pricing choice.
        """
        # Determine the primary engine driver
        engine_display_names = {
            "E1_weight": "Procurement & Cost Protection (E1)",
            "E2_weight": "Demand Elasticity & Revenue Optimization (E2)",
            "E3_weight": "Inventory Urgency & Clearing (E3)",
            "E4_weight": "Competitor & Market Alignment (E4)",
            "E5_weight": "Event Intelligence (E5)"
        }
        
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        top_weight_key, top_weight_val = sorted_weights[0]
        top_engine_name = engine_display_names.get(top_weight_key, top_weight_key)

        e1_data = pricing_state.get("E1", {})
        min_safe_price = float(e1_data.get("minimum_safe_price", 0.0))
        
        # Build narrative
        narrative = (
            f"The pricing optimization engine selected ₹{winner['price']:.2f} as the final price (confidence: {winner['final_score']:.2%}). "
            f"This decision was primarily guided by {top_engine_name} with an assigned weight of {top_weight_val:.1%}. "
        )

        # Retrieve event details
        event_active = pricing_state.get("event_active", False)
        if event_active:
            e5_data = pricing_state.get("E5", {})
            impact_level = e5_data.get("impact_level", "LOW")
            narrative += (
                f"A special {e5_data.get('event_type')} event nearby (expected attendance: {e5_data.get('attendance'):,}, "
                f"distance: {e5_data.get('distance_km'):.1f}km, duration: {e5_data.get('duration_hours'):.1f} hours) "
                f"triggered an '{impact_level}' event intelligence surge (E5 score: {e5_data.get('event_score'):.2f}), "
                f"assigning it an engine influence weight of {weights.get('E5_weight', 0.0):.1%} and contributing "
                f"a price enhancement value of {winner.get('event_component', 0.0):.3f} to this price point. "
            )

        # Describe constraint resolution
        e2_optimal = float(pricing_state.get("E2", {}).get("optimal_price", 0.0))

        if e2_optimal > 0 and e2_optimal < min_safe_price:
            narrative += (
                f"An engine conflict was detected and resolved: "
                f"while the demand optimal price was lower at ₹{e2_optimal:.2f}, "
                f"it was rejected to respect the procurement safety floor of ₹{min_safe_price:.2f}. "
            )
        else:
            narrative += f"The selected price fully satisfies the procurement safety floor of ₹{min_safe_price:.2f}. "

        # Add inventory/market context
        inv_desc = decision_summary["inventory_pressure"]
        mkt_desc = decision_summary["market_pressure"]
        
        narrative += f"Current inventory pressure is '{inv_desc}' and competitor market pressure is '{mkt_desc}'. "

        # Summarize scoring performance
        narrative += (
            f"At this price point, the sub-scores are: "
            f"Procurement Margin: {winner['procurement_score']:.2f}, "
            f"Elasticity/Revenue: {winner['elasticity_score']:.2f}, "
            f"Inventory Clearance: {winner['inventory_score']:.2f}, "
            f"Market Competitiveness: {winner['market_score']:.2f}."
        )

        return narrative

    def _generate_price_journey(
        self,
        pricing_state: Dict[str, Any],
        weights: Dict[str, float],
        final_selected_price: float
    ) -> Dict[str, float]:
        """
        Calculates sub-engine pricing contributions using actual outputs,
        and scales them so they sum up exactly to (final_price - base_price).
        """
        e1_data = pricing_state.get("E1", {})
        e2_data = pricing_state.get("E2", {})
        e3_data = pricing_state.get("E3", {})
        e4_data = pricing_state.get("E4", {})
        e5_data = pricing_state.get("E5", {})

        # Base price (E1 minimum safe price)
        base_price = float(e1_data.get("minimum_safe_price", 0.0))
        e2_price = float(e2_data.get("optimal_price", 0.0))
        
        # E3 Price = E2_price * recommended_multiplier
        e3_mult = float(e3_data.get("recommended_multiplier", 1.0))
        e3_price = e2_price * e3_mult

        # E4 Price = E2_price * recommended_multiplier
        e4_mult = float(e4_data.get("recommended_multiplier", 1.0))
        e4_price = e2_price * e4_mult

        # E5 Price = E2_price * (1.0 + event_score) if active else base_price
        event_active = bool(pricing_state.get("event_active", False))
        event_score = float(e5_data.get("event_score", 0.0)) if e5_data else 0.0
        if event_active:
            e5_price = e2_price * (1.0 + event_score)
        else:
            e5_price = base_price

        # Retrieve Layer 2 weights
        w2 = float(weights.get("E2_weight", 0.0))
        w3 = float(weights.get("E3_weight", 0.0))
        w4 = float(weights.get("E4_weight", 0.0))
        w5 = float(weights.get("E5_weight", 0.0))

        # Calculate raw uplifts (contributions) relative to base_price
        e2_uplift_raw = (e2_price - base_price) * w2
        inventory_uplift_raw = base_price * (e3_mult - 1.0) * w3
        competitor_uplift_raw = base_price * (e4_mult - 1.0) * w4
        event_uplift_raw = base_price * event_score * w5 if event_active else 0.0

        # Scale contributions proportionally to equal the actual difference between selected final price and base price
        target_total_uplift = final_selected_price - base_price
        sum_raw_uplifts = e2_uplift_raw + inventory_uplift_raw + competitor_uplift_raw + event_uplift_raw

        scaled_uplifts = {}
        if abs(sum_raw_uplifts) > 1e-4:
            scale_factor = target_total_uplift / sum_raw_uplifts
            scaled_uplifts["demand_effect"] = e2_uplift_raw * scale_factor
            scaled_uplifts["inventory_effect"] = inventory_uplift_raw * scale_factor
            scaled_uplifts["competitor_effect"] = competitor_uplift_raw * scale_factor
            scaled_uplifts["event_effect"] = event_uplift_raw * scale_factor
        else:
            # Fallback if sum of raw uplifts is zero (e.g. no deviation from E1 base)
            # Distribute based on weights
            total_w = w2 + w3 + w4 + w5
            if total_w > 0:
                scaled_uplifts["demand_effect"] = target_total_uplift * (w2 / total_w)
                scaled_uplifts["inventory_effect"] = target_total_uplift * (w3 / total_w)
                scaled_uplifts["competitor_effect"] = target_total_uplift * (w4 / total_w)
                scaled_uplifts["event_effect"] = target_total_uplift * (w5 / total_w)
            else:
                scaled_uplifts["demand_effect"] = target_total_uplift
                scaled_uplifts["inventory_effect"] = 0.0
                scaled_uplifts["competitor_effect"] = 0.0
                scaled_uplifts["event_effect"] = 0.0

        # Round all outputs to 2 decimal places
        journey = {
            "procurement_floor": round(base_price, 2),
            "demand_effect_raw": round(e2_uplift_raw, 2),
            "demand_effect": round(scaled_uplifts["demand_effect"], 2),
            "inventory_effect_raw": round(inventory_uplift_raw, 2),
            "inventory_effect": round(scaled_uplifts["inventory_effect"], 2),
            "competitor_effect_raw": round(competitor_uplift_raw, 2),
            "competitor_effect": round(scaled_uplifts["competitor_effect"], 2),
            "event_effect_raw": round(event_uplift_raw, 2),
            "event_effect": round(scaled_uplifts["event_effect"], 2),
            "total_uplift": round(target_total_uplift, 2),
            "final_price": round(final_selected_price, 2)
        }

        # Handle rounding errors to ensure: procurement_floor + sum(scaled_effects) == final_price
        sum_components = (
            journey["procurement_floor"] + 
            journey["demand_effect"] + 
            journey["inventory_effect"] + 
            journey["competitor_effect"] + 
            journey["event_effect"]
        )
        diff = round(journey["final_price"] - sum_components, 2)
        if diff != 0:
            # Adjust the largest effect to preserve mathematical exactness
            effects_keys = ["demand_effect", "inventory_effect", "competitor_effect", "event_effect"]
            largest_key = max(effects_keys, key=lambda k: abs(journey[k]))
            journey[largest_key] = round(journey[largest_key] + diff, 2)

        # Make sure total_uplift is exactly the sum of scaled effects
        journey["total_uplift"] = round(
            journey["demand_effect"] + 
            journey["inventory_effect"] + 
            journey["competitor_effect"] + 
            journey["event_effect"], 2
        )

        return journey

    def _calculate_system_confidence(self, pricing_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Computes a heuristic confidence score and level based on data completeness and E2 models.
        """
        score = 50.0
        
        # 1. Check E2 prediction source
        e2_data = pricing_state.get("E2", {})
        pred_src = e2_data.get("prediction_source", "")
        if pred_src == "xgboost":
            score += 15.0
        elif pred_src == "similar_sku_fallback":
            score += 5.0
            
        # 2. Check competitor data
        e4_data = pricing_state.get("E4", {})
        comp_band = e4_data.get("competitor_band", [])
        if comp_band and isinstance(comp_band, list) and len(comp_band) == 2:
            score += 15.0
            
        # 3. Check inventory metrics
        e3_data = pricing_state.get("E3", {})
        if "inventory_pressure" in e3_data and e3_data.get("days_of_supply") is not None:
            score += 10.0
            
        # 4. Check E1 Supply risk
        e1_data = pricing_state.get("E1", {})
        supply_risk = float(e1_data.get("supply_risk", 1.0))
        if supply_risk < 0.4:
            score += 10.0
            
        # Bound score between 0.0 and 100.0
        score = min(100.0, max(0.0, float(round(score, 1))))
        
        if score >= 80.0:
            level = "High"
        elif score >= 50.0:
            level = "Medium"
        else:
            level = "Low"
            
        return {
            "confidence_score": score,
            "confidence_level": level
        }
