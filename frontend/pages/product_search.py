import streamlit as st
from frontend.services.inventory_service import get_inventory_summary
from frontend.components.tables import render_styled_table

def show_page():
    st.title("🔍 Catalog & Product Search")
    st.markdown("Query the inventory database, inspect reserve stocks, and analyze Days of Supply profiles.")
    st.markdown("---")

    # Load inventory summaries
    summary = get_inventory_summary()
    df = summary["products_list"]

    if df.empty:
        st.info("No active catalog records. Navigate to the Inventory Upload panel to populate stock states.")
        return

    # Clean warehouse columns
    if "warehouse" not in df.columns:
        if "warehouse_location" in df.columns:
            df["warehouse"] = df["warehouse_location"]
        else:
            df["warehouse"] = "N/A"

    # Filter Layout Row 1
    col1, col2 = st.columns(2)
    with col1:
        search_query = st.text_input("Search by Product ID or Name", "", placeholder="Enter keyword (e.g. Maggi, SKU_1056)")
    with col2:
        status_filter = st.multiselect("Filter Stock Status", ["Healthy", "Watchlist", "Critical"], default=[])

    # Filter Layout Row 2
    col3, col4 = st.columns(2)
    categories = sorted(df["category"].dropna().astype(str).unique())
    brands = sorted(df["brand"].dropna().astype(str).unique())
    with col3:
        cat_filter = st.multiselect("Filter Category", categories, default=[])
    with col4:
        brand_filter = st.multiselect("Filter Brand", brands, default=[])

    # Execute filtering logic
    df_filtered = df.copy()

    if search_query:
        q = search_query.strip().lower()
        df_filtered = df_filtered[
            df_filtered["product_id"].astype(str).str.lower().str.contains(q) |
            df_filtered["product_name"].astype(str).str.lower().str.contains(q)
        ]

    if status_filter:
        df_filtered = df_filtered[df_filtered["stock_status"].isin(status_filter)]

    if cat_filter:
        df_filtered = df_filtered[df_filtered["category"].isin(cat_filter)]

    if brand_filter:
        df_filtered = df_filtered[df_filtered["brand"].isin(brand_filter)]

    st.subheader(f"Results ({len(df_filtered)} matching products)")

    # Columns to render
    cols_to_show = [
        "product_id",
        "product_name",
        "category",
        "brand",
        "base_market_price",
        "supplier_price",
        "freight_cost",
        "warehouse_cost",
        "gst_tax",
        "true_landed_cost",
        "current_stock",
        "reserved_stock",
        "net_stock",
        "stock_status",
        "warehouse"
    ]
    
    # Render using the styled tables component
    render_styled_table(df_filtered[cols_to_show])
