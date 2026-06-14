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
    if "price" in display_df.columns:
        formatters["price"] = "₹{:.2f}"
    if "selling_price" in display_df.columns:
        formatters["selling_price"] = "₹{:.2f}"
    if "recommended_price" in display_df.columns:
        formatters["recommended_price"] = "₹{:.2f}"
    if "competitor_price" in display_df.columns:
        formatters["competitor_price"] = "₹{:.2f}"

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
        style_obj = style_obj.applymap(highlight_status, subset=["stock_status"])

    st.dataframe(style_obj, use_container_width=use_container_width, hide_index=True)
