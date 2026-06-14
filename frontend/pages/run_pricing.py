import streamlit as st
from frontend.services.pricing_service import (
    get_available_products,
    get_available_retailers,
    get_available_locations,
    run_pricing
)

def show_page():
    st.title("💸 Dynamic Price Optimization Engine")
    st.markdown("Run the Dynamic Retail Pricing pipeline to compute dynamic engine weights and optimized price recommendations.")
    st.markdown("---")

    # Load available selections
    products = get_available_products()
    retailers = get_available_retailers()
    locations = get_available_locations()

    if not products:
        st.warning("⚠️ No products cataloged in the system. Please upload inventory snapshots first.")
        return

    # Simulation Parameter Columns
    col_sku, col_ret, col_loc = st.columns(3)
    
    with col_sku:
        selected_prod = st.selectbox(
            "Select Target SKU", 
            products, 
            format_func=lambda x: x["label"]
        )
    with col_ret:
        selected_retailer = st.selectbox("Select Target Retailer", retailers)
    with col_loc:
        selected_location = st.selectbox("Select Store Location", locations)

    st.markdown("---")

    # Run pricing button
    if st.button("🚀 Run Pricing Optimization", type="primary", use_container_width=True):
        try:
            with st.spinner("Executing E1-E4 Specialist Engines & Layer 3 Optimization..."):
                result = run_pricing(
                    product_id=selected_prod["id"],
                    retailer=selected_retailer,
                    location=selected_location
                )
            
            st.success("✅ Pricing Calculation Completed!")

            # 1. Main Optimized Price banner (Large green card)
            final_price = result["final_price"]
            confidence = result["confidence"]
            winning_candidate = result["winning_candidate"]
            explanation = result["explanation"]

            banner_html = f"""
            <div style="
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 8px;
                padding: 2rem;
                text-align: center;
                margin-bottom: 2rem;
                box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 120, 0.05);
            ">
                <h3 style="color: #155724; margin: 0; font-size: 1.1rem; font-weight: 600; text-transform: uppercase;">
                    Final Optimized Price
                </h3>
                <h1 style="color: #155724; margin: 0.5rem 0; font-size: 3.2rem; font-weight: 800;">
                    ₹{final_price:.2f}
                </h1>
                <p style="color: #155724; margin: 0; font-size: 1rem; font-weight: bold;">
                    Confidence: {confidence:.2%} &nbsp;|&nbsp; Winning Candidate: ₹{winning_candidate:.2f}
                </p>
            </div>
            """
            st.markdown(banner_html, unsafe_allow_html=True)

            # 2. Specialist Engines breakdown rows
            pricing_state = result["pricing_state"]
            
            # Row 1: E1 & E2
            col_e1, col_e2 = st.columns(2)
            
            with col_e1:
                st.subheader("🛡️ E1: Procurement Risk")
                e1 = pricing_state["E1"]
                st.markdown(
                    f"""
                    <div style="padding: 1rem; border-radius: 6px; border-left: 4px solid #4e73df; background-color: #f8f9fc; margin-bottom: 1rem;">
                        <b>Supply Risk (0-1):</b> {e1['supply_risk']:.3f}<br>
                        <b>Cost Volatility (0-1):</b> {e1.get('cost_volatility', 0.0):.3f}<br>
                        <b>Minimum Safe Price:</b> ₹{e1['minimum_safe_price']:.2f}<br>
                        <b>Procurement cost:</b> ₹{e1['true_landed_cost']:.2f}<br>
                        <b>Primary Supplier:</b> {e1['supplier_id']}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

            with col_e2:
                st.subheader("📈 E2: Demand Forecasting")
                e2 = pricing_state["E2"]
                st.markdown(
                    f"""
                    <div style="padding: 1rem; border-radius: 6px; border-left: 4px solid #1cc88a; background-color: #f8f9fc; margin-bottom: 1rem;">
                        <b>Prediction Mode:</b> {e2['prediction_source'].replace('_', ' ').title()}<br>
                        <b>Optimal Price Point:</b> ₹{e2['optimal_price']:.2f}<br>
                        <b>Expected Daily Demand:</b> {e2['expected_demand']:.2f} units<br>
                        <b>Price Elasticity Score:</b> {e2['elasticity']:.3f}<br>
                        <b>Similarity SKU count:</b> {len(e2.get('similar_products_used', []))}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

            # Row 2: E3 & E4
            col_e3, col_e4 = st.columns(2)
            
            with col_e3:
                st.subheader("📦 E3: Inventory Dynamics")
                e3 = pricing_state["E3"]
                st.markdown(
                    f"""
                    <div style="padding: 1rem; border-radius: 6px; border-left: 4px solid #f6c23e; background-color: #f8f9fc; margin-bottom: 1rem;">
                        <b>Inventory Pressure:</b> {e3['inventory_pressure']:.3f}<br>
                        <b>Stockout Risk (Calc):</b> {e3['stockout_risk']:.3f}<br>
                        <b>Urgency Level (0-1):</b> {e3.get('urgency_score', 0.0):.3f}<br>
                        <b>Multiplier Recommendation:</b> {e3['recommended_multiplier']:.3f}<br>
                        <b>Current Warehouse:</b> {e3.get('store_location', 'N/A')}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

            with col_e4:
                st.subheader("⚖️ E4: Competitor Market Intelligence")
                e4 = pricing_state["E4"]
                st.markdown(
                    f"""
                    <div style="padding: 1rem; border-radius: 6px; border-left: 4px solid #36b9cc; background-color: #f8f9fc; margin-bottom: 1rem;">
                        <b>Market Pressure Index:</b> {e4['market_pressure']:.3f}<br>
                        <b>Competitive Gap vs Median:</b> ₹{e4['competitive_gap']:.2f}<br>
                        <b>Competitor Price Band:</b> ₹{e4['competitor_band'][0]:.2f} ➔ ₹{e4['competitor_band'][1]:.2f}<br>
                        <b>Multiplier Recommendation:</b> {e4['recommended_multiplier']:.3f}<br>
                        <b>Target Market Region:</b> {e4['market_region']}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

            st.markdown("---")

            # 3. Dynamic weights allocation
            st.subheader("⚖️ DynCo: Coordinated Engine Weights")
            w_col1, w_col2, w_col3, w_col4 = st.columns(4)
            weights = result["coordinated_weights"]
            
            with w_col1:
                st.metric("E1 Weight", f"{weights['E1_weight']:.2%}")
            with w_col2:
                st.metric("E2 Weight", f"{weights['E2_weight']:.2%}")
            with w_col3:
                st.metric("E3 Weight", f"{weights['E3_weight']:.2%}")
            with w_col4:
                st.metric("E4 Weight", f"{weights['E4_weight']:.2%}")

            st.markdown("---")

            # 4. Stakeholder Explanation
            st.subheader("📝 Stakeholder Decision Explanation")
            st.info(explanation)

        except Exception as e:
            st.error(f"❌ **Pricing Optimization Failed**:\n\n{str(e)}")
