import streamlit as st
import pandas as pd
import plotly.express as px
from frontend.services.pricing_history_service import load_pricing_history
from frontend.services.pricing_service import get_available_products, get_available_retailers

def show_page():
    st.title("📊 Pricing Recommendation Audit History")
    st.markdown("Track and analyze historical price optimizations, confidence intervals, and engine risks over time.")
    st.markdown("---")

    df_hist = load_pricing_history()

    if df_hist.empty:
        st.info("ℹ️ No historical pricing decisions recorded yet. Run the pricing pipeline to populate history.")
        return

    # Extract catalog names mapping
    products = get_available_products()
    prod_map = {p["id"]: p["label"] for p in products}

    # Sidebar Filter Controls
    st.subheader("🔍 Filter Recommendation Records")
    col_sku, col_ret, col_date = st.columns(3)

    with col_sku:
        sku_options = ["All"] + sorted(list(df_hist["product_id"].unique()))
        selected_sku = st.selectbox(
            "Filter by SKU", 
            sku_options,
            format_func=lambda x: prod_map.get(x, x) if x != "All" else "All Products"
        )
    with col_ret:
        retailer_options = ["All"] + sorted(list(df_hist["retailer"].unique()))
        selected_retailer = st.selectbox("Filter by Retailer", retailer_options)
    with col_date:
        min_date = df_hist["run_timestamp"].min().date()
        max_date = df_hist["run_timestamp"].max().date()
        selected_dates = st.date_input(
            "Filter by Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

    # Filter dataset
    df_filtered = df_hist.copy()
    if selected_sku != "All":
        df_filtered = df_filtered[df_filtered["product_id"] == selected_sku]
    if selected_retailer != "All":
        df_filtered = df_filtered[df_filtered["retailer"] == selected_retailer]
    
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_d, end_d = selected_dates
        df_filtered = df_filtered[
            (df_filtered["run_timestamp"].dt.date >= start_d) &
            (df_filtered["run_timestamp"].dt.date <= end_d)
        ]

    if df_filtered.empty:
        st.warning("⚠️ No decisions found matching the current filter settings.")
        return

    # Sort chronology for charts
    df_filtered = df_filtered.sort_values("run_timestamp")

    # Render visual chart if single SKU selected
    if selected_sku != "All":
        sku_label = prod_map.get(selected_sku, selected_sku)
        st.subheader(f"📈 Price Trend: {sku_label}")
        
        # Plotly chart
        fig_price = px.line(
            df_filtered, 
            x="run_timestamp", 
            y=["final_price", "engine1_price", "engine2_price"],
            labels={"value": "Price (₹)", "run_timestamp": "Timestamp", "variable": "Metric"},
            title="Optimized Price vs Specialist Cost Bounds",
            color_discrete_sequence=["#1cc88a", "#e74a3b", "#4e73df"]
        )
        fig_price.update_layout(
            legend_orientation="h",
            legend_y=-0.2,
            margin=dict(l=20, r=20, t=40, b=20),
            plot_bgcolor="rgba(240, 242, 246, 0.5)"
        )
        st.plotly_chart(fig_price, use_container_width=True)

        # Plotly risks overlay
        st.subheader("🛡️ Confidence & Pressure Trends")
        fig_risks = px.area(
            df_filtered,
            x="run_timestamp",
            y=["confidence", "supply_risk", "inventory_pressure", "market_pressure"],
            labels={"value": "Index (0-1)", "run_timestamp": "Timestamp", "variable": "Risk Metric"},
            title="Engine Pressure Indices & Recommendation Confidence Score",
            color_discrete_sequence=["#36b9cc", "#f6c23e", "#e74a3b", "#858796"]
        )
        fig_risks.update_layout(
            legend_orientation="h",
            legend_y=-0.2,
            margin=dict(l=20, r=20, t=40, b=20),
            plot_bgcolor="rgba(240, 242, 246, 0.5)"
        )
        st.plotly_chart(fig_risks, use_container_width=True)

    else:
        st.info("💡 **Tip**: Select a specific SKU filter to view comparative time-series line charts and risk trends.")

    # Show raw historical data records
    st.subheader("📋 Log of Decisions")
    
    # Prettify labels for rendering
    df_grid = df_filtered.copy()
    df_grid["product_name"] = df_grid["product_id"].map(prod_map)
    df_grid["run_timestamp"] = df_grid["run_timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    
    cols_to_show = [
        "run_timestamp", "product_id", "product_name", "retailer", "location", 
        "final_price", "confidence", "supply_risk", "inventory_pressure", "market_pressure"
    ]
    
    from frontend.components.tables import render_styled_table
    render_styled_table(df_grid[cols_to_show])
