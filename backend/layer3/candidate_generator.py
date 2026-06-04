import numpy as np
import logging
from typing import Dict, List, Any

# Configure logging
logger = logging.getLogger("pricing_system.layer3.candidate_generator")

class CandidateGenerator:
    """
    Generates realistic, discrete business candidate prices centered around domain anchors
    such as the procurement cost floor, demand elastic optimal price, competitor prices,
    and inventory-adjusted price targets.
    """
    def __init__(self, step_size: float = 1.0, steps_around_anchors: int = 5):
        """
        Initializes the CandidateGenerator.
        
        Parameters:
            step_size (float): The pricing increment step (e.g. 1.00 for $1 steps, 0.50, or 5.00).
            steps_around_anchors (int): The number of steps to generate above and below each anchor.
        """
        self.step_size = max(0.01, step_size)
        self.steps_around_anchors = steps_around_anchors

    def generate_candidates(self, pricing_state: Dict[str, Any]) -> List[float]:
        """
        Generates a sorted, unique list of candidate prices using Layer 1 outputs.
        
        Parameters:
            pricing_state (dict): The outputs from Layer 1 specialist engines.
            
        Returns:
            list: A list of float candidate prices, guaranteed to contain realistic options.
        """
        anchors = set()

        # 1. Procurement Safety Floor (E1)
        e1_data = pricing_state.get("E1", {})
        min_safe_price = e1_data.get("minimum_safe_price", None)
        if min_safe_price is not None:
            anchors.add(float(min_safe_price))

        # 2. Elasticity Optimal Price (E2)
        e2_data = pricing_state.get("E2", {})
        optimal_price = e2_data.get("optimal_price", None)
        if optimal_price is not None:
            anchors.add(float(optimal_price))

        # 3. Competitor Band Anchors (E4)
        e4_data = pricing_state.get("E4", {})
        competitor_band = e4_data.get("competitor_band", None)
        if competitor_band and isinstance(competitor_band, list) and len(competitor_band) == 2:
            min_comp = float(competitor_band[0])
            max_comp = float(competitor_band[1])
            anchors.add(min_comp)
            anchors.add(max_comp)
            anchors.add(round((min_comp + max_comp) / 2, 2))
        
        # 4. Inventory-Adjusted Price (E3 Recommended Adjustment Multiplier applied to optimal price)
        e3_data = pricing_state.get("E3", {})
        inventory_multiplier = e3_data.get("recommended_multiplier", None)
        if inventory_multiplier is not None and optimal_price is not None:
            anchors.add(float(optimal_price * inventory_multiplier))

        # 5. Market-Adjusted Price (E4 Recommended Adjustment Multiplier applied to optimal price)
        market_multiplier = e4_data.get("recommended_multiplier", None)
        if market_multiplier is not None and optimal_price is not None:
            anchors.add(float(optimal_price * market_multiplier))

        # Fallback if no anchors are found
        if not anchors:
            logger.warning("[Layer3] No anchors could be extracted from Layer 1. Defaulting to a baseline anchor.")
            anchors.add(50.0)  # Safe default baseline if everything is missing

        # Generate candidates around each anchor using grid steps
        candidates = set()
        for anchor in anchors:
            for i in range(-self.steps_around_anchors, self.steps_around_anchors + 1):
                candidate_price = anchor + (i * self.step_size)
                # Align to nearest step_size multiple to make prices neat and business-realistic
                aligned_price = round(round(candidate_price / self.step_size) * self.step_size, 2)
                if aligned_price > 0:
                    candidates.add(aligned_price)

        # In addition to anchors, generate a uniform grid between min and max anchors to avoid gaps
        min_anchor = min(anchors)
        max_anchor = max(anchors)
        
        # Generate grid between min_anchor and max_anchor * 1.2 to allow some upside pricing room
        grid_start = min_anchor
        grid_end = max_anchor * 1.2
        
        # Guard against zero range
        if grid_start < grid_end:
            grid_prices = np.arange(grid_start, grid_end + self.step_size, self.step_size)
            for price in grid_prices:
                aligned_price = round(round(price / self.step_size) * self.step_size, 2)
                if aligned_price > 0:
                    candidates.add(aligned_price)

        # Sort the final list of unique candidates
        sorted_candidates = sorted(list(candidates))
        
        logger.info(f"[Layer3] Generated {len(sorted_candidates)} candidates between {min(sorted_candidates)} and {max(sorted_candidates)}")
        print(f"[Layer3] Generated {len(sorted_candidates)} candidates between {min(sorted_candidates)} and {max(sorted_candidates)}")
        
        return sorted_candidates
