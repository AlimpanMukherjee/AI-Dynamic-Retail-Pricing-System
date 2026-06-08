import numpy as np

def calculate_pack_size_similarity(size1: float, size2: float) -> float:
    """
    Computes a similarity score between two pack sizes (in ml or grams) on a [0, 1] scale.
    
    Uses a custom-fitted quadratic mapping to align precisely with domain expectations:
      - Exact match (e.g., 200ml vs 200ml) -> 1.0
      - Close match (e.g., 200ml vs 250ml) -> ~0.9
      - High difference (e.g., 200ml vs 2L) -> ~0.1
      
    Mathematical formulation:
      Let r = min(size1, size2) / max(size1, size2)
      f(r) = -0.714 * r^2 + 1.785 * r - 0.071 (clipped to [0, 1])
    """
    if size1 <= 0 or size2 <= 0:
        return 0.0
        
    ratio = min(size1, size2) / max(size1, size2)
    
    # Quadratic curve fitting the three milestones:
    # f(1.0) = 1.0
    # f(0.8) = 0.90
    # f(0.1) = 0.10
    similarity = -0.714 * (ratio ** 2) + 1.785 * ratio - 0.071
    
    return float(np.clip(similarity, 0.0, 1.0))
