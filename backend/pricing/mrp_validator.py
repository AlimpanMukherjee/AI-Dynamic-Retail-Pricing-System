def apply_mrp_limit(
    calculated_price: float,
    mrp: float,
    strict: bool = True
) -> dict:
    """
    Enforces the Maximum Retail Price (MRP) constraint on calculated selling price.
    
    Args:
        calculated_price (float): Calculated price from pricing logic.
        mrp (float): Maximum retail price of the product.
        strict (bool): Whether to raise a ValueError on missing/invalid MRPs.
        
    Returns:
        dict: A status summary containing calculated_price, mrp, final_price, and mrp_limit_applied.
    """
    if mrp is None or mrp <= 0:
        if strict:
            raise ValueError(f"Invalid or missing product MRP: {mrp}")
        else:
            import logging
            logging.getLogger("pricing_system.mrp_validator").warning(
                f"MRP validation skipped. Invalid/missing MRP: {mrp}"
            )
            return {
                "calculated_price": float(calculated_price),
                "mrp": None if mrp is None else float(mrp),
                "final_price": float(calculated_price),
                "mrp_limit_applied": False
            }

    calc_price_val = float(calculated_price)
    mrp_val = float(mrp)

    if calc_price_val <= mrp_val:
        return {
            "calculated_price": calc_price_val,
            "mrp": mrp_val,
            "final_price": calc_price_val,
            "mrp_limit_applied": False
        }
    else:
        return {
            "calculated_price": calc_price_val,
            "mrp": mrp_val,
            "final_price": mrp_val,
            "mrp_limit_applied": True
        }
