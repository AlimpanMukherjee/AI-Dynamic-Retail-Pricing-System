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
            effective_uplift_pct = float(e5_data.get("effective_uplift_pct", 0.0))
            elasticity = float(pricing_state.get("E2", {}).get("elasticity", 0.0))
            elasticity_factor = max(0.5, min(1.5, 2.0 - abs(elasticity)))
            event_uplift_pct_val = effective_uplift_pct * elasticity_factor * 100.0
            narrative += (
                f"A special {e5_data.get('event_type')} event nearby (expected attendance: {e5_data.get('attendance'):,}, "
                f"distance: {e5_data.get('distance_km'):.1f}km, duration: {e5_data.get('duration_hours'):.1f} hours) "
                f"triggered an '{impact_level}' event intelligence surge (E5 opportunity score: {e5_data.get('event_opportunity_score'):.1f}%), "
                f"resulting in a post-optimization business uplift of {event_uplift_pct_val:.1f}% applied to the base recommended price. "
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

        # E2 confidence and learning explanation
        e2_conf = pricing_state.get("engine2_confidence", 1.0)
        if e2_conf < 0.5:
            narrative += (
                "Demand forecasting is operating with limited historical sales data. "
                "The pricing recommendation therefore relies more heavily on procurement costs, "
                "inventory conditions, competitor pricing, and event intelligence. "
            )
        else:
            narrative += (
                "Demand forecasting is based on substantial historical sales data and has "
                "significant influence on the pricing recommendation. "
            )


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
        Calculates post-optimization price journey parameters including base minimum safe price,
        Layer 3 optimized price, and post-optimization event uplift.
        """
        minimum_safe_price = float(pricing_state.get("E1", {}).get("minimum_safe_price", 0.0))
        layer3_price = float(final_selected_price)
        
        event_active = bool(pricing_state.get("event_active", False))
        e5_data = pricing_state.get("E5", {})
        effective_uplift_pct = float(e5_data.get("effective_uplift_pct", 0.0)) if event_active else 0.0
        elasticity = float(pricing_state.get("E2", {}).get("elasticity", 0.0))
        
        elasticity_factor = max(0.5, min(1.5, 2.0 - abs(elasticity)))
        event_uplift_amount = layer3_price * effective_uplift_pct * elasticity_factor if event_active else 0.0
        final_price = layer3_price + event_uplift_amount
        
        return {
            "minimum_safe_price": round(minimum_safe_price, 2),
            "layer3_price": round(layer3_price, 2),
            "event_uplift_amount": round(event_uplift_amount, 2),
            "event_uplift_pct": round(effective_uplift_pct * 100.0, 2),
            "final_price": round(final_price, 2)
        }

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
