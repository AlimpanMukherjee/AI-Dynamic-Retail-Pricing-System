import pandas as pd
import backend.config as cfg
import logging

logger = logging.getLogger("pricing_system.competitor_service")

# ---------------------------------------------------------------------
# Internal helper: schema validation
# ---------------------------------------------------------------------
def _validate_schema(df: pd.DataFrame):
    """Validate uploaded competitor DataFrame.
    Returns (is_valid: bool, error_report: dict).
    Checks:
        - Required columns exist
        - No duplicate (product_id, competitor_name)
        - product_id non‑empty
        - competitor_price > 0
        - promotion_active convertible to bool
        - rating within 0‑5
    """
    required = [
        "product_id",
        "product_name",
        "competitor_name",
        "competitor_price",
        "market_region",
        "promotion_active",
        "rating",
    ]
    errors = {}
    # 1. column presence
    missing = [c for c in required if c not in df.columns]
    if missing:
        errors["missing_columns"] = missing
        return False, errors

    # Run unified backend competitor validation
    from backend.onboarding.validators import validate_competitors, ValidationError
    try:
        validate_competitors(df)
    except ValidationError as e:
        errors["validation_error"] = str(e)

    # 2. duplicate detection
    dup_mask = df.duplicated(subset=["product_id", "competitor_name"], keep=False)
    if dup_mask.any():
        dup_rows = df[dup_mask].index.tolist()
        errors["duplicate_rows"] = dup_rows

    # 3. row‑level checks
    row_errors = []
    for idx, row in df.iterrows():
        row_err = {}
        # product_id
        if pd.isna(row["product_id"]) or str(row["product_id"]).strip() == "":
            row_err["product_id"] = "empty"
        # competitor_price
        try:
            price = float(row["competitor_price"])
            if price <= 0:
                row_err["competitor_price"] = "must be > 0"
        except Exception:
            row_err["competitor_price"] = "not numeric"
        # promotion_active
        val = row["promotion_active"]
        if isinstance(val, str):
            val_l = val.lower()
            if val_l not in ["true", "false"]:
                row_err["promotion_active"] = f"invalid string '{val}'"
        elif not isinstance(val, (bool, int, float)):
            row_err["promotion_active"] = f"invalid type {type(val)}"
        # rating
        try:
            rating = float(row["rating"])
            if not (0 <= rating <= 5):
                row_err["rating"] = "out of range 0‑5"
        except Exception:
            row_err["rating"] = "not numeric"
        if row_err:
            row_errors.append({"row": idx, "errors": row_err})
    if row_errors:
        errors["row_errors"] = row_errors

    is_valid = len(errors) == 0
    return is_valid, errors

# ---------------------------------------------------------------------
# Internal helper: merging logic
# ---------------------------------------------------------------------
def _merge_data(current_df: pd.DataFrame, upload_df: pd.DataFrame):
    """Merge upload into current data using (product_id, competitor_name) as key.
    Returns merged DataFrame and a summary dict {"updated": X, "inserted": Y}.
    """
    # Identify keys present in upload
    upload_keys = set(
        zip(upload_df["product_id"].astype(str), upload_df["competitor_name"].astype(str))
    )
    # Drop matching rows from current
    mask_keep = ~current_df.apply(
        lambda r: (str(r["product_id"]), str(r["competitor_name"])) in upload_keys,
        axis=1,
    )
    kept = current_df[mask_keep]
    merged = pd.concat([kept, upload_df], ignore_index=True, sort=False)
    # Count updates vs inserts
    current_keys = set(
        zip(current_df["product_id"].astype(str), current_df["competitor_name"].astype(str))
    )
    updated = len([k for k in upload_keys if k in current_keys])
    inserted = len(upload_keys) - updated
    summary = {"updated": updated, "inserted": inserted}
    return merged, summary

# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------
def load_competitor_data() -> pd.DataFrame:
    """Load the current competitor CSV defined by cfg.CUSTOMER_COMPETITOR_PATH."""
    path = cfg.CUSTOMER_COMPETITOR_PATH
    return pd.read_csv(path)

def update_competitor_data(upload_df: pd.DataFrame):
    """Validate, merge and persist uploaded competitor data.
    Returns a summary dict with counts and any validation errors.
    """
    # 1. Validation
    valid, errors = _validate_schema(upload_df)
    if not valid:
        logger.error("Competitor upload validation failed")
        return {"valid": False, "errors": errors}

    # 2. Load current data
    current_df = load_competitor_data()

    # 3. Merge
    merged_df, merge_summary = _merge_data(current_df, upload_df)

    # 4. Persist
    merged_df.to_csv(cfg.CUSTOMER_COMPETITOR_PATH, index=False)
    logger.info(
        f"Competitor data merged – updated: {merge_summary['updated']}, inserted: {merge_summary['inserted']}"
    )
    return {"valid": True, **merge_summary}
