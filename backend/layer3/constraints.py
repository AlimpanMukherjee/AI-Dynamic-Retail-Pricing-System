import logging
from typing import Dict, List, Any

# Configure logging
logger = logging.getLogger("pricing_system.layer3.constraints")

class PricingConstraints:
    """
    Defines, manages, and enforces business and risk constraints on candidate prices.
    Ensures final recommended prices protect procurement margins and respect safety boundaries.
    """
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initializes PricingConstraints with a configuration dictionary.
        
        Parameters:
            config (dict): Configuration options for constraints.
                - min_margin (float): Overriding minimum profit margin (e.g. 0.10 for 10%).
                - max_price_multiplier (float): Maximum price as a multiplier of E1 minimum_safe_price (default: 2.0).
                - min_price (float): Hard minimum price (absolute floor override).
                - max_price (float): Hard maximum price (absolute ceiling override).
        """
        self.config = config or {}
        self.min_margin = self.config.get("min_margin", None)
        self.max_price_multiplier = self.config.get("max_price_multiplier", 2.0)
        self.min_price = self.config.get("min_price", None)
        self.max_price = self.config.get("max_price", None)

    def evaluate_candidate(self, price: float, pricing_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates a single price candidate against all active constraints.
        
        Parameters:
            price (float): The price candidate to evaluate.
            pricing_state (dict): The outputs from Layer 1 specialist engines.
            
        Returns:
            dict: Evaluation results containing:
                - satisfied (bool): True if all constraints are met.
                - reason (str): Explanation of failure if not satisfied.
        """
        # Extract E1 outputs
        e1_data = pricing_state.get("E1", {})
        min_safe_price = float(e1_data.get("minimum_safe_price", 0.0))
        true_landed_cost = float(e1_data.get("true_landed_cost", 0.0))

        # 1. Absolute Procurement Floor (minimum_safe_price)
        # Price must never go below minimum_safe_price
        if price < min_safe_price:
            return {
                "satisfied": False,
                "reason": f"Price below procurement safety floor (${price:.2f} < min_safe_price ${min_safe_price:.2f})"
            }

        # 2. Configured Hard Minimum Price Override
        if self.min_price is not None and price < self.min_price:
            return {
                "satisfied": False,
                "reason": f"Price below configured absolute minimum (${price:.2f} < min_price ${self.min_price:.2f})"
            }

        # 3. Configured Minimum Margin Override (if provided and landed cost is available)
        if self.min_margin is not None and true_landed_cost > 0:
            margin = (price - true_landed_cost) / price
            if margin < self.min_margin:
                return {
                    "satisfied": False,
                    "reason": f"Price fails minimum margin constraint (margin {margin:.2%} < target {self.min_margin:.2%})"
                }

        # 4. Maximum Price Ceiling (Multiplier of min_safe_price)
        max_safe_limit = min_safe_price * self.max_price_multiplier
        if price > max_safe_limit:
            return {
                "satisfied": False,
                "reason": f"Price exceeds risk ceiling multiplier (${price:.2f} > max_limit ${max_safe_limit:.2f})"
            }

        # 5. Configured Hard Maximum Price Override
        if self.max_price is not None and price > self.max_price:
            return {
                "satisfied": False,
                "reason": f"Price exceeds configured absolute maximum (${price:.2f} > max_price ${self.max_price:.2f})"
            }

        return {"satisfied": True, "reason": "All constraints satisfied."}

    def filter_candidates(self, candidates: List[float], pricing_state: Dict[str, Any]) -> List[float]:
        """
        Filters a list of candidate prices, returning only those that satisfy constraints.
        Logs and prints detailed diagnostics about constraint violations.
        
        Parameters:
            candidates (list): List of float candidate prices.
            pricing_state (dict): The outputs from Layer 1 specialist engines.
            
        Returns:
            list: List of float candidate prices that passed constraints.
        """
        passed_candidates = []
        discarded_count = 0
        reasons = {}

        for price in candidates:
            eval_res = self.evaluate_candidate(price, pricing_state)
            if eval_res["satisfied"]:
                passed_candidates.append(price)
            else:
                discarded_count += 1
                reason = eval_res["reason"]
                reasons[reason] = reasons.get(reason, 0) + 1

        if discarded_count > 0:
            logger.info(f"[Layer3] Discarded {discarded_count} candidates due to constraint violations. Reasons: {reasons}")
            print(f"[Layer3] Discarded {discarded_count} candidates due to constraint violations.")
            for r, count in reasons.items():
                print(f"  - {count} candidates: {r}")

        return passed_candidates
