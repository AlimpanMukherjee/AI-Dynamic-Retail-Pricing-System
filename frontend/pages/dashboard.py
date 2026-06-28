import streamlit as st
import pandas as pd
from frontend.services.inventory_service import get_inventory_summary
from frontend.services.sales_service import get_sales_summary, get_sales_history_df
from frontend.components.metrics import render_metric_card

def show_page():
    st.title("📊 Pricing & Ingestion Dashboard")
    st.markdown("Monitor real-time stock levels, check dataset metrics, and analyze health statuses.")
    st.markdown("---")

    # Load data summaries
    inv_summary = get_inventory_summary()
    sales_summary = get_sales_summary()

    # Log dashboard inventory source path
    import logging
    from backend.inventory.inventory_repository import get_current_inventory_path
    logger = logging.getLogger("pricing_system.frontend.dashboard")
    logger.info(f"Dashboard metrics loaded. Inventory Source Path: {get_current_inventory_path()}")

    # Load alerts and model details
    from frontend.services.alert_service import get_alerts_summary
    from frontend.services.retraining_service import get_active_model_details

    alerts_sum = get_alerts_summary()
    open_alerts = alerts_sum["open_count"]
    high_sev_alerts = alerts_sum["high_severity_count"]

    active_model = get_active_model_details()
    active_ver = active_model.get("model_version", "N/A")
    last_retrain = active_model.get("training_date", "N/A")

    # Metric Row 1
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Total Products Cataloged", f"{inv_summary['total_products']:,}", border_color="#4e73df")
    with col2:
        render_metric_card("Total Inventory Units", f"{inv_summary['total_stock']:,}", border_color="#1cc88a")
    with col3:
        render_metric_card("Low Stock (Watchlist)", f"{inv_summary['low_stock_count']:,}", border_color="#f6c23e")
    with col4:
        render_metric_card("Critical Stock items", f"{inv_summary['critical_stock_count']:,}", border_color="#e74a3b")

    # Metric Row 2: Operational Status
    col5, col6, col7 = st.columns(3)
    with col5:
        render_metric_card("Latest Sales Transaction Date", sales_summary["latest_sale_date"], border_color="#4e73df")
    with col6:
        render_metric_card("Latest Inventory Ingest Time", inv_summary["latest_update"], border_color="#f8f9fc")
    with col7:
        render_metric_card("Model Last Retrained", last_retrain, border_color="#858796")

    st.markdown("---")

    # If no data is available
    if inv_summary["products_list"].empty:
        st.info("No current inventory records found. Please navigate to the Upload panels to ingest CSV updates.")
        return

    df = inv_summary["products_list"]

    # Charts Row
    st.subheader("Inventory Metrics & Visual Analytics")
    c_col1, c_col2, c_col3 = st.columns(3)

    with c_col1:
        st.markdown("**Stock Health Status**")
        health_data = pd.DataFrame(
            [{"Status": k, "Count": v} for k, v in inv_summary["health_counts"].items()]
        )
        st.bar_chart(health_data, x="Status", y="Count")

    with c_col2:
        st.markdown("**Top 10 SKUs by On-Hand Stock**")
        df_top10 = df.sort_values(by="current_stock", ascending=False).head(10)
        df_top10["label"] = df_top10["product_id"] + " - " + df_top10.get("product_name", "Product")
        st.bar_chart(df_top10, x="product_id", y="current_stock")

    with c_col3:
        st.markdown("**Stock Distribution by Category**")
        df_cat = df.groupby("category")["current_stock"].sum().reset_index()
        st.bar_chart(df_cat, x="category", y="current_stock")

    st.markdown("---")

    # Sales Analytics Trends
    st.subheader("📈 Sales Analytics Trends")
    df_sales_raw = get_sales_history_df()
    
    if not df_sales_raw.empty:
        # Group sales by day
        df_sales_raw["parsed_date"] = pd.to_datetime(df_sales_raw["date"], format='mixed').dt.date
        price_col = "selling_price" if "selling_price" in df_sales_raw.columns else "price"
        df_sales_raw["sales_value"] = df_sales_raw[price_col] * df_sales_raw["units_sold"]
        
        df_daily = df_sales_raw.groupby("parsed_date").agg({
            "units_sold": "sum",
            "sales_value": "sum"
        }).reset_index().sort_values("parsed_date")
        
        # User selection toggle
        chart_option = st.radio(
            "Select Sales Metric for Trend Line Chart",
            options=["Sales Quantity (Units Sold)", "Total Sales Value (Revenue)"],
            horizontal=True
        )
        
        if chart_option == "Sales Quantity (Units Sold)":
            st.markdown("**Daily Sales Quantity (Units)**")
            st.line_chart(df_daily, x="parsed_date", y="units_sold")
        else:
            st.markdown("**Daily Sales Value (Revenue in ₹)**")
            st.line_chart(df_daily, x="parsed_date", y="sales_value")
    else:
        st.info("No historical sales transactions found to plot trends.")

    st.markdown("---")

    # Low & Critical Stock watchlist tables
    st.subheader("⚠️ Stock Level Alerts")
    critical_df = df[df["stock_status"] == "Critical"][["product_id", "product_name", "category", "current_stock", "reserved_stock", "net_stock", "warehouse"]]
    watchlist_df = df[df["stock_status"] == "Watchlist"][["product_id", "product_name", "category", "current_stock", "reserved_stock", "net_stock", "warehouse"]]

    tab1, tab2 = st.tabs(["🔴 Critical Stock Warnings", "🟡 Low Stock Watchlist"])
    
    with tab1:
        if not critical_df.empty:
            st.warning(f"{len(critical_df)} products are currently in Critical condition. Stockout risk is high.")
            st.dataframe(critical_df, use_container_width=True, hide_index=True)
        else:
            st.success("All products have safe stock counts above safety levels.")

    with tab2:
        if not watchlist_df.empty:
            st.info(f"{len(watchlist_df)} products are below reorder thresholds. Consider reordering.")
            st.dataframe(watchlist_df, use_container_width=True, hide_index=True)
        else:
            st.success("No products are in the low-stock warning zone.")
