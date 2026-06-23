from backend.engines.event_config import CATEGORY_ALIASES, CATEGORY_EVENT_MULTIPLIERS

def normalize_category(product_category: str) -> str:
    """
    Normalizes a catalog category name to a standardized category used in event mapping.
    Uses CATEGORY_ALIASES. Falls back to title-casing the category if no match is found.
    """
    if not product_category:
        return "Other"
    
    # Strip whitespace and normalize capitalization
    category_stripped = str(product_category).strip()
    
    # 1. Direct match in CATEGORY_ALIASES
    for alias_key, standard_name in CATEGORY_ALIASES.items():
        if alias_key.lower() == category_stripped.lower():
            return standard_name
            
    # 2. Direct match in CATEGORY_EVENT_MULTIPLIERS
    for standard_name in CATEGORY_EVENT_MULTIPLIERS.keys():
        if standard_name.lower() == category_stripped.lower():
            return standard_name
            
    # 3. Substring match fallback
    for standard_name in CATEGORY_EVENT_MULTIPLIERS.keys():
        if standard_name.lower() in category_stripped.lower() or category_stripped.lower() in standard_name.lower():
            return standard_name
            
    return category_stripped.title()

def get_category_relevance_multiplier(product_category: str, event_type: str) -> float:
    """
    Looks up category-event relevance multiplier based on catalog product category and event type.
    Defaults to 1.0 if not found.
    """
    normalized = normalize_category(product_category)
    category_map = CATEGORY_EVENT_MULTIPLIERS.get(normalized)
    
    if not category_map:
        return 1.0
        
    # Match event type case-insensitively
    for key, val in category_map.items():
        if key.lower() == str(event_type).strip().lower():
            return val
            
    return 1.0
