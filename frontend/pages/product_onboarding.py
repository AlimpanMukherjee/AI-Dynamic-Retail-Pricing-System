import streamlit as st
import pandas as pd
from frontend.services.product_onboarding_service import onboard_single_product
from frontend.services.pricing_service import get_available_locations

def show_page():
    st.title("✨ Product Onboarding Portal")
    st.markdown("Onboard new SKUs into the pricing system by cataloging their base attributes, supplier costs, and initial inventory levels.")
    st.markdown("---")

    # Use tabs for a clean, non-overwhelming step-by-step onboarding process
    tab1, tab2, tab3 = st.tabs([
        "📁 1. Product Master Catalog",
        "⚖️ 2. Supplier & Procurement Costs",
        "📦 3. Initial Inventory & Location"
    ])

    # Shared State initialized in session state
    if "onboard_sku" not in st.session_state:
        st.session_state.onboard_sku = ""

    with tab1:
        st.subheader("Product Metadata & Description")
        st.markdown("Enter details about the product to register it in the master catalog.")
        
        col_id, col_name = st.columns(2)
        with col_id:
            sku = st.text_input(
                "Product ID (SKU)*", 
                value=st.session_state.onboard_sku,
                placeholder="e.g., SKU_1110",
                help="A unique identifier for the SKU. Must not already exist."
            ).strip()
            # Update session state
            st.session_state.onboard_sku = sku
        with col_name:
            product_name = st.text_input(
                "Product Name*",
                placeholder="e.g., Sprite 300ml Can",
                help="Descriptive name of the product."
            ).strip()

        col_brand, col_cat = st.columns(2)
        with col_brand:
            brand = st.text_input(
                "Brand*",
                placeholder="e.g., Coca Cola",
                help="Brand of the item."
            ).strip()
        with col_cat:
            category = st.selectbox(
                "Product Category*",
                options=["Beverages", "Snacks", "Packaged Foods", "Dairy", "Personal Care", "Staples"],
                help="Primary market category, used for target margin calculations."
            )

        col_sub, col_price = st.columns(2)
        with col_sub:
            subcategory = st.text_input(
                "Subcategory*",
                placeholder="e.g., Carbonated Soft Drink",
                help="Subcategory identifier."
            ).strip()
        with col_price:
            base_price = st.number_input(
                "Base Market Price (₹)*",
                min_value=0.01,
                value=35.0,
                step=1.0,
                format="%.2f",
                help="Recommended default market selling price."
            )

        col_life, col_pack = st.columns(2)
        with col_life:
            shelf_life = st.number_input(
                "Shelf Life (Days)",
                min_value=1,
                value=180,
                step=1,
                help="Expected shelf life in days."
            )
        with col_pack:
            pack_size = st.number_input(
                "Pack Size (g/ml/Units)",
                min_value=1,
                value=300,
                step=1,
                help="Size of the pack packaging."
            )

    with tab2:
        st.subheader("Procurement & Landed Cost Breakdown")
        st.markdown("Define the supplier cost profile so the pricing system can guarantee margin boundaries.")

        col_sup, col_loc = st.columns(2)
        with col_sup:
            supplier_id = st.text_input(
                "Supplier ID*",
                placeholder="e.g., SUP_912",
                help="The primary supplier identifier."
            ).strip()
        with col_loc:
            supplier_loc = st.text_input(
                "Supplier Location*",
                placeholder="e.g., Pune",
                help="City where supplier DC is located."
            ).strip()

        col_cost, col_freight = st.columns(2)
        with col_cost:
            supplier_price = st.number_input(
                "Supplier Cost Price (₹)*",
                min_value=0.01,
                value=22.50,
                step=1.0,
                format="%.2f",
                help="Base cost price charged by the supplier."
            )
        with col_freight:
            freight_cost = st.number_input(
                "Freight Cost (₹)",
                min_value=0.0,
                value=1.50,
                step=0.5,
                format="%.2f",
                help="Transport/delivery cost per unit."
            )

        col_wh, col_tax = st.columns(2)
        with col_wh:
            warehouse_cost = st.number_input(
                "Warehouse Cost (₹)",
                min_value=0.0,
                value=0.80,
                step=0.10,
                format="%.2f",
                help="Storage and warehouse handling cost per unit."
            )
        with col_tax:
            gst_tax = st.number_input(
                "GST/Taxes (₹)",
                min_value=0.0,
                value=2.02,
                step=0.10,
                format="%.2f",
                help="Taxes applied to the procurement."
            )

        col_rel, col_lead = st.columns(2)
        with col_rel:
            reliability = st.number_input(
                "Supplier Reliability (0.0 to 1.0)",
                min_value=0.0,
                max_value=1.0,
                value=0.92,
                step=0.01,
                format="%.2f",
                help="Supplier reliability score. Used to calculate Supply Risk metrics."
            )
        with col_lead:
            lead_time = st.number_input(
                "Supplier Lead Time (Days)",
                min_value=1,
                value=6,
                step=1,
                help="Average days required for supply delivery."
            )

        col_moq = st.columns(1)[0]
        moq = col_moq.number_input(
            "Minimum Order Quantity (MOQ)",
            min_value=1,
            value=100,
            step=10,
            help="Minimum purchase quantity order threshold."
        )

    with tab3:
        st.subheader("Operational Inventory Setup")
        st.markdown("Set up initial store stock levels and safety inventory targets.")

        col_store, col_stock = st.columns(2)
        with col_store:
            # Load locations dynamically from pricing service
            available_locs = get_available_locations()
            store_location = st.selectbox(
                "Store Location*",
                options=available_locs,
                help="Retail store where inventory will be deployed."
            )
        with col_stock:
            current_stock = st.number_input(
                "Initial Stock Level*",
                min_value=0,
                value=500,
                step=10,
                help="Initial physical stock count in the store."
            )

        col_res, col_safe = st.columns(2)
        with col_res:
            reserved_stock = st.number_input(
                "Reserved Stock Level",
                min_value=0,
                value=0,
                step=1,
                help="Stock quantities reserved for online or pending orders."
            )
        with col_safe:
            safety_stock = st.number_input(
                "Safety Stock Level",
                min_value=0,
                value=50,
                step=5,
                help="Safety cushion threshold. Below this triggers low-stock alerts."
            )

        col_wh_loc = st.columns(1)[0]
        warehouse_location = col_wh_loc.text_input(
            "Warehouse Location (DC)",
            value=f"{store_location} DC",
            help="Warehouse or distribution center matching the store region."
        ).strip()

    st.markdown("---")

    # Onboard execution
    if st.button("🚀 Onboard & Initialize Product", type="primary", use_container_width=True):
        # 1. Basic validation
        if not sku or not product_name or not brand or not subcategory or not supplier_id or not supplier_loc:
            st.error("❌ **Validation Error**: Please fill in all mandatory fields (*) across the tabs.")
            return

        # 2. Build structured data objects
        product_data = {
            "product_id": sku,
            "product_name": product_name,
            "brand": brand,
            "category": category,
            "base_market_price": float(base_price),
            "shelf_life_days": int(shelf_life),
            "subcategory": subcategory,
            "pack_size_ml": int(pack_size)
        }

        procurement_data = {
            "product_id": sku,
            "product_name": product_name,
            "brand": brand,
            "supplier_id": supplier_id,
            "supplier_location": supplier_loc,
            "supplier_price": float(supplier_price),
            "freight_cost": float(freight_cost),
            "warehouse_cost": float(warehouse_cost),
            "gst_tax": float(gst_tax),
            "lead_time_days": int(lead_time),
            "supplier_reliability": float(reliability),
            "minimum_order_quantity": int(moq)
        }

        inventory_data = {
            "product_id": sku,
            "product_name": product_name,
            "brand": brand,
            "category": category,
            "retailer_company": "Spencer's", # Aligned with user retailer company preference
            "store_location": store_location,
            "warehouse_location": warehouse_location,
            "current_stock": int(current_stock),
            "reserved_stock": int(reserved_stock),
            "reorder_point": int(safety_stock * 1.5), # heuristic
            "safety_stock": int(safety_stock),
            "sales_velocity_per_day": 0.0,
            "lead_time_days": int(lead_time),
            "stock_age_days": 1,
            "inventory_holding_cost": float(warehouse_cost * current_stock),
            "stockout_risk_score": 0.0,
            "warehouse": warehouse_location
        }

        try:
            with st.spinner("Writing master entries and initializing stock..."):
                res = onboard_single_product(
                    product_data=product_data,
                    procurement_data=procurement_data,
                    inventory_data=inventory_data
                )
            
            # Clear caches to ensure dashboard and run pricing drop-downs update
            st.cache_data.clear()

            st.success(f"🎉 **Onboarding Successful!** Product `{res['product_id']} - {res['product_name']}` is now cataloged.")
            st.info(
                "💡 **Next Steps**:\n\n"
                "1. Go to the **Run Pricing** page in the sidebar.\n"
                "2. Your new product should be selectable in the **SKU selector** dropdown.\n"
                "3. Run pricing optimization to generate its cost floor and coordinate margins."
            )
        except Exception as e:
            st.error(f"❌ **Onboarding Ingestion Failed**: {str(e)}")
