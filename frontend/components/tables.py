import streamlit as st
import pandas as pd

def render_styled_table(df: pd.DataFrame, use_container_width: bool = True):
    """
    Renders a formatted DataFrame. Highlights status indicators and pads numerical values.
    """
    # Create copy to prevent index or inplace alterations
    display_df = df.copy()

    # Apply style formatters dynamically if columns are present
    style_obj = display_df.style

    formatters = {}
    if "current_stock" in display_df.columns:
        formatters["current_stock"] = "{:,}"
    if "stock" in display_df.columns:
        formatters["stock"] = "{:,}"
    if "reserved_stock" in display_df.columns:
        formatters["reserved_stock"] = "{:,}"
    if "net_stock" in display_df.columns:
        formatters["net_stock"] = "{:,}"
    if "units_sold" in display_df.columns:
        formatters["units_sold"] = "{:,}"
        
    price_cols = [
        "price", "selling_price", "recommended_price", "competitor_price",
        "base_price", "e2_contribution", "e3_contribution", "e4_contribution", "e5_contribution",
        "e2_contribution_raw", "e3_contribution_raw", "e4_contribution_raw", "e5_contribution_raw",
        "total_uplift", "final_price", "base_market_price", "supplier_price", 
        "freight_cost", "warehouse_cost", "gst_tax", "true_landed_cost",
        "price_before_event", "event_uplift_amount"
    ]
    for col in price_cols:
        if col in display_df.columns:
            formatters[col] = "₹{:.2f}"
            
    if "confidence_score" in display_df.columns:
        formatters["confidence_score"] = "{:.1f}%"

    if formatters:
        style_obj = style_obj.format(formatters)

    # Highlight cells based on stock rules if columns are found
    if "stock_status" in display_df.columns:
        def highlight_status(val):
            if val == "Critical":
                return "background-color: #fce4d6; color: #c00000; font-weight: bold;"
            elif val == "Watchlist":
                return "background-color: #fff2cc; color: #7f6000; font-weight: bold;"
            elif val == "Healthy":
                return "background-color: #e2efda; color: #375623; font-weight: bold;"
            return ""
        if hasattr(style_obj, "map"):
            style_obj = style_obj.map(highlight_status, subset=["stock_status"])
        else:
            style_obj = style_obj.applymap(highlight_status, subset=["stock_status"])

    st.dataframe(style_obj, use_container_width=use_container_width, hide_index=True)
