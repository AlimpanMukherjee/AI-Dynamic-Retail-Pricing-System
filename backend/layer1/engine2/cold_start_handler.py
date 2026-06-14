import logging
from backend.layer1.engine2.config import MODE_THRESHOLDS

logger = logging.getLogger("pricing_system.layer1.engine2.cold_start_handler")

def determine_prediction_mode(sales_records_count: int) -> str:
    """
    Determines whether Engine 2 should operate in:
    - cold_start (0-30 sales records)
    - hybrid (31-100 sales records)
    - normal (>100 sales records)
    """
    thresholds = MODE_THRESHOLDS
    if sales_records_count <= thresholds["cold_start_max"]:
        return "cold_start"
    elif sales_records_count <= thresholds["hybrid_max"]:
        return "hybrid"
    else:
        return "normal"

def hybrid_prediction(hist_metrics: dict, sim_metrics: dict, sales_records_count: int) -> dict:
    """
    Blends target SKU sales history with similarity-borrowed signals.
    """
    n = sales_records_count
    if n <= 30:
        w_hist = 0.0
    elif n <= 31:
        w_hist = 0.10
    elif n <= 50:
        w_hist = 0.10 + (n - 31) / (50 - 31) * (0.30 - 0.10)
    elif n <= 100:
        w_hist = 0.30 + (n - 50) / (100 - 50) * (1.00 - 0.30)
    else:
        w_hist = 1.0

    w_sim = 1.0 - w_hist

    blended_optimal_price = w_hist * hist_metrics["optimal_price"] + w_sim * sim_metrics["optimal_price"]
    blended_expected_demand = w_hist * hist_metrics["expected_demand"] + w_sim * sim_metrics["expected_demand"]
    blended_elasticity = w_hist * hist_metrics["elasticity"] + w_sim * sim_metrics["elasticity"]

    log_msg = f"[Hybrid] Blending {w_hist * 100:.1f}% historical and {w_sim * 100:.1f}% similarity signals"
    logger.info(log_msg)

    return {
        "optimal_price": float(round(blended_optimal_price, 2)),
        "expected_demand": float(round(blended_expected_demand, 2)),
        "elasticity": float(round(blended_elasticity, 3)),
        "similar_products_used": sim_metrics.get("similar_products_used", [])
    }
