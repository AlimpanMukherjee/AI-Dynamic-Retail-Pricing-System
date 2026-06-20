import logging
from typing import Dict, Any, List

from backend.layer3.constraints import PricingConstraints
from backend.layer3.candidate_generator import CandidateGenerator
from backend.layer3.scoring_engine import PricingScorer
from backend.layer3.final_price_selector import FinalPriceSelector

# Configure logging
logger = logging.getLogger("pricing_system.layer3.optimizer")

class PriceOptimizer:
    """
    Orchestrator for Layer 3 (Arbitration & Optimization Layer).
    Resolves engine conflicts by filtering candidates through constraints,
    scoring them, and selecting the highest-scoring candidate.
    """
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initializes the PriceOptimizer orchestrator.
        
        Parameters:
            config (dict): Global configurations for Layer 3 components:
                - candidate_step_size (float): Pricing candidate grid size (default: 1.0).
                - steps_around_anchors (int): Number of steps to generate around anchors (default: 5).
                - constraints_config (dict): Configuration for PricingConstraints.
                - scoring_config (dict): Configuration for PricingScorer.
        """
        self.config = config or {}
        
        # Instantiate sub-components
        self.constraints = PricingConstraints(self.config.get("constraints_config"))
        self.generator = CandidateGenerator(
            step_size=self.config.get("candidate_step_size", 1.0),
            steps_around_anchors=self.config.get("steps_around_anchors", 5)
        )
        self.scorer = PricingScorer(self.config.get("scoring_config"))
        self.selector = FinalPriceSelector()

    def optimize_price(
        self,
        pricing_state: Dict[str, Any],
        coordinated_weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Orchestrates the end-to-end pricing arbitration process.
        
        Parameters:
            pricing_state (dict): Output from Layer 1 specialist engines.
            coordinated_weights (dict): Output weights from Layer 2 model.
            
        Returns:
            dict: Structured final AI price recommendation containing:
                - final_price
                - confidence
                - selected_price_score
                - winning_candidate
                - price_breakdown
                - decision_summary
                - explanation
        """
        # 1. Error Handling and Validation for inputs
        self._validate_inputs(pricing_state, coordinated_weights)

        # Ensure E1 is available, as it defines the absolute safety floor
        e1_data = pricing_state.get("E1", {})
        min_safe_price = e1_data.get("minimum_safe_price", None)
        if min_safe_price is None:
            raise ValueError("[Layer3] Critical input missing: 'minimum_safe_price' from E1 is required.")
        
        # 2. Generate raw price candidates
        raw_candidates = self.generator.generate_candidates(pricing_state)

        # 3. Filter candidates through constraints
        valid_candidates = self.constraints.filter_candidates(raw_candidates, pricing_state)

        # Handle Edge Case: All candidates filtered out by constraints
        if not valid_candidates:
            logger.warning("[Layer3] All generated candidates failed constraints. Falling back to procurement floor.")
            print("[Layer3] WARNING: All candidates failed constraints. Using procurement floor as fallback.")
            valid_candidates = [float(min_safe_price)]

        # 4. Score all valid candidate prices
        scored_candidates = []
        for price in valid_candidates:
            scored_info = self.scorer.score_candidate(price, pricing_state, coordinated_weights)
            scored_candidates.append(scored_info)

        # 5. Select the winner with the highest score
        decision_report = self.selector.select_best_price(
            scored_candidates=scored_candidates,
            pricing_state=pricing_state,
            weights=coordinated_weights
        )

        return decision_report

    def _validate_inputs(self, pricing_state: Dict[str, Any], weights: Dict[str, float]):
        """
        Validates the structure and correctness of Layer 1 and Layer 2 inputs.
        Prevents crashes due to missing keys or non-normalized weights.
        """
        if not pricing_state or not isinstance(pricing_state, dict):
            raise ValueError("[Layer3] Invalid input: pricing_state must be a non-empty dictionary.")
        
        if not weights or not isinstance(weights, dict):
            raise ValueError("[Layer3] Invalid input: coordinated_weights must be a non-empty dictionary.")

        # Verify Layer 1 structures
        required_engines = ["E1", "E2", "E3", "E4"]
        for eng in required_engines:
            if eng not in pricing_state or not isinstance(pricing_state[eng], dict):
                logger.warning(f"[Layer3] Pricing state is missing engine dictionary for {eng}. Injecting empty dict.")
                pricing_state[eng] = {}

        # Validate weights completeness
        expected_keys = {"E1_weight", "E2_weight", "E3_weight", "E4_weight", "E5_weight"}
        present_keys = set(weights.keys())
        missing_keys = expected_keys - present_keys
        
        if missing_keys:
            logger.warning(f"[Layer3] Missing weights {missing_keys}. Initializing to defaults.")
            for key in missing_keys:
                if key == "E5_weight":
                    weights[key] = 0.0
                else:
                    weights[key] = 0.25
        
        # Ensure weights are positive floats and normalize if they deviate from 1.0
        for k in expected_keys:
            try:
                weights[k] = max(0.0, float(weights[k]))
            except (ValueError, TypeError):
                weights[k] = 0.0 if k == "E5_weight" else 0.25

        weight_values = [weights[k] for k in expected_keys]
        total_weight = sum(weight_values)
        
        # If total weight is zero or extremely small, reset to equal weights
        if total_weight < 1e-5:
            logger.warning("[Layer3] Total weight is zero. Resetting to equal weights.")
            for k in expected_keys:
                weights[k] = 0.0 if k == "E5_weight" else 0.25
            total_weight = 1.0

        if not (0.99 <= total_weight <= 1.01):
            logger.info(f"[Layer3] Weights sum to {total_weight}. Normalizing weights to 1.0.")
            for k in expected_keys:
                weights[k] = float(round(weights[k] / total_weight, 4))
