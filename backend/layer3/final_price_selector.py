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
                "market_score": float(winner["market_score"])
            },
            "decision_summary": decision_summary,
            "explanation": explanation
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
            "E4_weight": "Competitor & Market Alignment (E4)"
        }
        
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        top_weight_key, top_weight_val = sorted_weights[0]
        top_engine_name = engine_display_names.get(top_weight_key, top_weight_key)

        e1_data = pricing_state.get("E1", {})
        min_safe_price = float(e1_data.get("minimum_safe_price", 0.0))
        
        # Build narrative
        narrative = (
            f"The pricing optimization engine selected ${winner['price']:.2f} as the final price (confidence: {winner['final_score']:.2%}). "
            f"This decision was primarily guided by {top_engine_name} with an assigned weight of {top_weight_val:.1%}. "
        )

        # Describe constraint resolution
        e2_optimal = float(pricing_state.get("E2", {}).get("optimal_price", 0.0))
        competitor_band = pricing_state.get("E4", {}).get("competitor_band", [])

        if e2_optimal > 0 and e2_optimal < min_safe_price:
            narrative += (
                f"An engine conflict was detected and resolved: "
                f"while the demand optimal price was lower at ${e2_optimal:.2f}, "
                f"it was rejected to respect the procurement safety floor of ${min_safe_price:.2f}. "
            )
        else:
            narrative += f"The selected price fully satisfies the procurement safety floor of ${min_safe_price:.2f}. "

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
