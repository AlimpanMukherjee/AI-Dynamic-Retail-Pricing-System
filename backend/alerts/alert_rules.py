def check_low_stock(days_of_supply: float) -> bool:
    """
    Triggers if days of supply falls below 7 days.
    """
    try:
        return float(days_of_supply) < 7.0
    except (TypeError, ValueError):
        return False

def check_stockout_risk(stockout_risk: float) -> bool:
    """
    Triggers if stockout risk exceeds 80%.
    """
    try:
        return float(stockout_risk) > 0.80
    except (TypeError, ValueError):
        return False

def check_supply_risk(supply_risk: float) -> bool:
    """
    Triggers if procurement supply risk exceeds 90%.
    """
    try:
        return float(supply_risk) > 0.90
    except (TypeError, ValueError):
        return False

def check_price_change(new_price: float, previous_price: float) -> bool:
    """
    Triggers if the absolute relative price change exceeds 10%.
    """
    try:
        p_price = float(previous_price)
        n_price = float(new_price)
        if p_price <= 0:
            return False
        return (abs(n_price - p_price) / p_price) > 0.10
    except (TypeError, ValueError):
        return False
