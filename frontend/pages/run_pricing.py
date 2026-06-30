import streamlit as st
from frontend.services.pricing_service import (
    get_available_products,
    get_resolved_retailer,
    get_available_locations,
    run_pricing
)

def show_page():
    st.title("💸 Dynamic Price Optimization Engine")
    st.markdown("Run the Dynamic Retail Pricing pipeline to compute dynamic engine weights and optimized price recommendations.")
    st.markdown("---")

    # Load available selections
    products = get_available_products()
    selected_retailer = get_resolved_retailer()
    locations = get_available_locations()

    if not products:
        st.warning("⚠️ No products cataloged in the system. Please upload inventory snapshots first.")
        return

    # Simulation Parameter Columns
    col_sku, col_loc = st.columns(2)
    
    with col_sku:
        selected_prod = st.selectbox(
            "Select Target SKU", 
            products, 
            format_func=lambda x: x["label"]
        )
    with col_loc:
        selected_location = st.selectbox("Select Store Location", locations)

    st.markdown(f"🏢 **Active Retailer**: `{selected_retailer}`")

    # Event Intelligence section
    st.subheader("🎪 Event Pricing")
    event_active = st.checkbox("Enable Event Pricing", value=False)
    projected_event_demand = 0.0
    event_type = "Other"
    attendance = 0
    distance_km = 2.0
    duration_hours = 4.0
    event_time_of_day = "Evening"
    
    if event_active:
        projected_event_demand = st.number_input(
            "Projected Demand During Event (Units)",
            min_value=0.0,
            value=450.0,
            step=50.0,
            help="Expected total demand for this product during the event period."
        )
        attendance = int(projected_event_demand)

    st.markdown("---")

    # Run pricing button
    if st.button("🚀 Run Pricing Optimization", type="primary", use_container_width=True):
        try:
            with st.spinner("Executing E1-E5 Specialist Engines & Layer 3 Optimization..."):
                result = run_pricing(
                    product_id=selected_prod["id"],
                    retailer=selected_retailer,
                    location=selected_location,
                    event_active=event_active,
                    event_type=event_type,
                    attendance=int(attendance),
                    distance_km=float(distance_km),
                    duration_hours=float(duration_hours),
                    event_time_of_day=event_time_of_day,
                    projected_event_demand=float(projected_event_demand)
                )
            
            st.success("✅ Pricing Calculation Completed!")

            # 1. Main Optimized Price banner (Large green card)
            final_price = result["final_price"]
            confidence = result["confidence"]
            winning_candidate = result["winning_candidate"]
            explanation = result["explanation"]
            
            price_conf = result.get("price_confidence", {})
            conf_score = price_conf.get("confidence_score", round(confidence * 100, 1))
            conf_level = price_conf.get("confidence_level", "High" if conf_score >= 80 else "Medium" if conf_score >= 50 else "Low")

            mrp_limit_applied = result.get("mrp_limit_applied", False)
            price_before_mrp = result.get("price_before_mrp", final_price)
            mrp = result.get("mrp")

            if mrp_limit_applied:
                banner_html = f"""
                <div style="
                    background-color: #fff3cd;
                    border: 1px solid #ffeeba;
                    border-radius: 8px;
                    padding: 1.5rem;
                    text-align: center;
                    margin-bottom: 2rem;
                    box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 120, 0.05);
                ">
                    <h3 style="color: #856404; margin: 0; font-size: 1rem; font-weight: 600; text-transform: uppercase;">
                        Calculated Price: ₹{price_before_mrp:.2f}
                    </h3>
                    <h1 style="color: #856404; margin: 0.5rem 0; font-size: 3.2rem; font-weight: 800;">
                        ₹{final_price:.2f}
                    </h1>
                    <p style="color: #721c24; margin: 0; font-size: 1.1rem; font-weight: bold;">
                        ⚠️ Selling price capped at product MRP.
                    </p>
                    <p style="color: #856404; margin: 0.5rem 0 0 0; font-size: 0.9rem;">
                        Confidence Score: {conf_score}% ({conf_level} Level) &nbsp;|&nbsp; Winning Candidate: ₹{winning_candidate:.2f}
                    </p>
                </div>
                """
            else:
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
                        Confidence Score: {conf_score}% ({conf_level} Level) &nbsp;|&nbsp; Winning Candidate: ₹{winning_candidate:.2f}
                    </p>
                </div>
                """
            st.markdown(banner_html, unsafe_allow_html=True)

            # Price Composition Waterfall Section
            price_journey = result.get("price_journey", {})
            if price_journey:
                st.subheader("📊 Price Composition & Journey")
                
                minimum_safe_price = price_journey.get("minimum_safe_price", 0.0)
                layer3_price = price_journey.get("layer3_price", 0.0)
                event_uplift_amount = price_journey.get("event_uplift_amount", 0.0)
                final_recommended_price = price_journey.get("final_price", final_price)
                
                optimization_uplift = layer3_price - minimum_safe_price
                
                # Plotly Waterfall Chart
                import plotly.graph_objects as go
                import pandas as pd
                
                measure = ["relative", "relative", "relative", "total"]
                x_labels = ["Minimum Safe Price", "Layer 3 Optimization Uplift", "Event Uplift", "Final Recommended Price"]
                
                text_labels = [
                    f"₹{minimum_safe_price:.2f}",
                    f"{'+' if optimization_uplift >= 0 else ''}₹{optimization_uplift:.2f}",
                    f"{'+' if event_uplift_amount >= 0 else ''}₹{event_uplift_amount:.2f}",
                    f"₹{final_recommended_price:.2f}"
                ]
                
                fig = go.Figure(go.Waterfall(
                    name="Price Journey",
                    orientation="v",
                    measure=measure,
                    x=x_labels,
                    y=[minimum_safe_price, optimization_uplift, event_uplift_amount, 0],
                    text=text_labels,
                    textposition="outside",
                    connector={"line": {"color": "rgb(63, 63, 63)"}},
                    decreasing={"marker": {"color": "#e74a3b"}},
                    increasing={"marker": {"color": "#4e73df"}},
                    totals={"marker": {"color": "#1cc88a"}}
                ))
                
                fig.update_layout(
                    title="Price Build Up Waterfall",
                    showlegend=False,
                    margin=dict(l=20, r=20, t=40, b=20),
                    plot_bgcolor="rgba(240, 242, 246, 0.5)",
                    yaxis_title="Price (₹)"
                )
                
                st.plotly_chart(fig, use_container_width=True)

                # Show text summary table
                st.markdown("### 📋 Price Breakdown Summary")
                breakdown_data = {
                    "Metric": [
                        "Minimum Safe Price (Procurement Floor)",
                        "Layer 3 Price (Optimized)",
                        "Event Uplift",
                        "Final Price"
                    ],
                    "Amount": [
                        f"₹{minimum_safe_price:.2f}",
                        f"₹{layer3_price:.2f}",
                        f"+₹{event_uplift_amount:.2f} ({price_journey.get('event_uplift_pct', 0.0):+.1f}%)",
                        f"₹{final_recommended_price:.2f}"
                    ]
                }
                st.dataframe(pd.DataFrame(breakdown_data), use_container_width=True, hide_index=True)



            st.markdown("---")

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
                sales_count = e2.get("sales_history_count", 0)
                
                st.markdown(
                    f"""
                    <div style="padding: 1rem; border-radius: 6px; border-left: 4px solid #1cc88a; background-color: #f8f9fc; margin-bottom: 1rem;">
                        <b>Optimal Price Point:</b> ₹{e2['optimal_price']:.2f}<br>
                        <b>Expected Daily Demand:</b> {e2['expected_demand']:.2f} units<br>
                        <b>Price Elasticity Score:</b> {e2['elasticity']:.3f}<br>
                        <b>Sales Records Used:</b> {sales_count}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                if confidence < 0.5:
                    st.info(
                        "ℹ️ **Demand forecasting is operating with limited historical sales data.**\n\n"
                        "The pricing recommendation therefore relies more heavily on procurement costs, "
                        "inventory conditions, competitor pricing, and event intelligence."
                    )
                else:
                    st.success(
                        "✨ **Demand forecasting is based on substantial historical sales data and has "
                        "significant influence on the pricing recommendation.**"
                    )
                
            # Centered and larger Demand Elasticity Curve
            opt_price = float(e2.get("optimal_price", 0.0))
            exp_demand = float(e2.get("expected_demand", 0.0))
            elasticity = float(e2.get("elasticity", 0.0))
            
            if opt_price > 0 and exp_demand > 0:
                import numpy as np
                import pandas as pd
                import plotly.express as px
                import os
                import backend.config as cfg
                
                products_path = cfg.CUSTOMER_PRODUCTS_PATH
                if not os.path.exists(products_path):
                    products_path = cfg.DEV_PRODUCTS_PATH
                    
                product_mrp = 9999.0
                try:
                    df_prod = pd.read_csv(products_path)
                    p_row = df_prod[df_prod["product_id"].astype(str).str.strip() == str(selected_prod["id"]).strip()]
                    if not p_row.empty:
                        base_market_price = float(p_row.iloc[0].get("base_market_price", 0.0))
                        product_mrp = float(p_row.iloc[0].get("mrp", base_market_price * 1.25))
                except Exception:
                    pass

                minimum_safe_price = float(pricing_state.get("E1", {}).get("minimum_safe_price", opt_price * 0.5))
                
                min_graph_price = minimum_safe_price
                max_graph_price = product_mrp
                if min_graph_price >= max_graph_price:
                    min_graph_price = max_graph_price * 0.5
                
                price_points = np.linspace(min_graph_price, max_graph_price, 45)
                eps = min(0.0, elasticity)
                demand_points = [float(exp_demand * ((p / opt_price) ** eps)) for p in price_points]
                
                df_curve = pd.DataFrame({
                    "Price (₹)": price_points,
                    "Expected Demand (units)": demand_points
                })
                
                fig_curve = px.line(
                    df_curve,
                    x="Price (₹)",
                    y="Expected Demand (units)",
                    title="Demand Elasticity Curve"
                )
                fig_curve.update_traces(line_color="#1cc88a", line_width=3)
                
                fig_curve.update_layout(
                    title_x=0.5,
                    margin=dict(l=40, r=40, t=50, b=40),
                    height=320,
                    showlegend=False,
                    plot_bgcolor="rgba(240, 242, 246, 0.5)",
                    xaxis_title="Price (₹)",
                    yaxis_title="Demand (Units)"
                )
                st.plotly_chart(fig_curve, use_container_width=True, config={'displayModeBar': False})

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

            # Row 3: E5 (only if event is active)
            if pricing_state.get("event_active"):
                st.markdown("---")
                st.subheader("🎪 E5: Event Pricing")
                e5 = pricing_state.get("E5", {})

                projected_demand_val = e5.get("projected_demand", 0.0)
                available_inventory_val = e5.get("available_inventory", 0.0)
                inventory_shortage_val = e5.get("inventory_shortage", 0.0)
                inventory_coverage_val = e5.get("inventory_coverage", 1.0)
                scarcity_score_val = e5.get("scarcity_score", 0.0)
                elasticity_val = e5.get("elasticity", -1.5)
                elasticity_factor_val = e5.get("elasticity_factor", 1.0)
                recommended_price_increase_pct_val = e5.get("recommended_price_increase_pct", 0.0)
                estimated_demand_after_increase_val = e5.get("estimated_demand_after_increase", 0.0)
                projected_inventory_coverage_val = e5.get("projected_inventory_coverage", 1.0)
                stock_sufficient_val = e5.get("stock_sufficient", True)
                warnings_list = e5.get("warnings", [])
                reasoning_list = e5.get("reasoning", [])
                
                event_uplift_amount_val = e5.get("event_price_increase", 0.0)
                final_price_val = e5.get("final_price", 0.0)
                confidence_val = e5.get("confidence", "High")
                pricing_reason = e5.get("reason", "")

                # Render Warnings if any
                if warnings_list:
                    for warning in warnings_list:
                        st.warning(warning)

                col_e5_1, col_e5_2 = st.columns(2)

                with col_e5_1:
                    st.markdown(
                        f"""
                        <div style="padding: 1rem; border-radius: 8px; border-left: 4px solid #6f42c1; background-color: #f8f9fc; height: 100%;">
                            <h4 style="margin-top: 0; color: #6f42c1; font-weight: bold;">Demand Surge Analysis</h4>
                            <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
                                <tr><td style="padding: 4px 0;"><b>Expected Demand:</b></td><td style="text-align: right;">{projected_demand_val:,.0f} Units</td></tr>
                                <tr><td style="padding: 4px 0;"><b>Available Inventory:</b></td><td style="text-align: right;">{available_inventory_val:,.0f} Units</td></tr>
                                <tr><td style="padding: 4px 0; font-weight: bold;"><b>Inventory Coverage:</b></td><td style="text-align: right; font-weight: bold; color: {'#1cc88a' if stock_sufficient_val else '#f6c23e'};">{inventory_coverage_val * 100:.0f}%</td></tr>
                                <tr><td style="padding: 4px 0; color: {'#e74a3b' if not stock_sufficient_val else '#1cc88a'};"><b>Inventory Shortage:</b></td><td style="text-align: right; font-weight: bold; color: {'#e74a3b' if not stock_sufficient_val else '#1cc88a'};">{inventory_shortage_val:,.0f} Units</td></tr>
                            </table>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with col_e5_2:
                    st.markdown(
                        f"""
                        <div style="padding: 1rem; border-radius: 8px; border-left: 4px solid #1cc88a; background-color: #f8f9fc; height: 100%;">
                            <h4 style="margin-top: 0; color: #1cc88a; font-weight: bold;">Pricing Recommendation</h4>
                            <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
                                <tr><td style="padding: 4px 0;"><b>Elasticity:</b></td><td style="text-align: right;">-{abs(elasticity_val):.2f}</td></tr>
                                <tr><td style="padding: 4px 0;"><b>Elasticity Factor:</b></td><td style="text-align: right;">{elasticity_factor_val:.2f}</td></tr>
                                <tr><td style="padding: 4px 0; color: #6f42c1;"><b>Recommended Increase:</b></td><td style="text-align: right; font-weight: bold; color: #6f42c1;">{recommended_price_increase_pct_val * 100:.1f}%</td></tr>
                                <tr><td style="padding: 4px 0; color: #36b9cc;"><b>Projected Demand After Increase:</b></td><td style="text-align: right; font-size: 0.85rem; color: #36b9cc;">~ {estimated_demand_after_increase_val:,.0f} Units (Estimated)</td></tr>
                                <tr><td style="padding: 4px 0; font-weight: bold; color: #4e73df;"><b>Projected Inventory Coverage:</b></td><td style="text-align: right; font-weight: bold; color: #4e73df;">{projected_inventory_coverage_val * 100:.0f}%</td></tr>
                                <tr><td style="padding: 4px 0; font-weight: bold; font-size: 1rem;"><b>Final Price:</b></td><td style="text-align: right; font-weight: bold; font-size: 1rem;">₹{final_price_val:.2f}</td></tr>
                            </table>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # Show reasoning list below
                st.markdown("##### 📋 Reasoning")
                for bullet in reasoning_list:
                    st.markdown(bullet)

            st.markdown("---")

            # 3. Dynamic weights allocation
            st.subheader("⚖️ DynCo: Coordinated Engine Weights")
            weights = result["coordinated_weights"]
            
            w_cols = st.columns(4)
            with w_cols[0]:
                st.metric("E1 Weight", f"{weights['E1_weight']:.2%}")
            with w_cols[1]:
                st.metric("E2 Weight", f"{weights['E2_weight']:.2%}")
            with w_cols[2]:
                st.metric("E3 Weight", f"{weights['E3_weight']:.2%}")
            with w_cols[3]:
                st.metric("E4 Weight", f"{weights['E4_weight']:.2%}")

        except Exception as e:
            st.error(f"❌ **Pricing Optimization Failed**:\n\n{str(e)}")
