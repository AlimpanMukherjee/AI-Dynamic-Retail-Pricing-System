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
    st.subheader("🎪 Event Intelligence")
    event_active = st.checkbox("Special Event Nearby", value=False)
    event_type = "Other"
    attendance = 0
    distance_km = 2.0
    duration_hours = 4.0
    
    if event_active:
        col_evt1, col_evt2 = st.columns(2)
        with col_evt1:
            event_type = st.selectbox(
                "Event Type",
                ["Festival", "Sports Match", "Concert", "Political Rally", "Local Fair", "Other"]
            )
            attendance = st.number_input(
                "Expected Attendance",
                min_value=0,
                value=5000,
                step=1000
            )
        with col_evt2:
            distance_km = st.number_input(
                "Distance From Store (km)",
                min_value=0.1,
                value=2.0,
                step=0.5
            )
            duration_hours = st.number_input(
                "Event Duration (hours)",
                min_value=1.0,
                value=4.0,
                step=1.0
            )

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
                    duration_hours=float(duration_hours)
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
                
                price_points = np.linspace(opt_price * 0.5, opt_price * 1.5, 45)
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
                st.subheader("🎪 E5: Event Intelligence")
                e5 = pricing_state.get("E5", {})
                
                # Fetch target category
                try:
                    import backend.config as cfg
                    import pandas as pd
                    df_p = pd.read_csv(cfg.CUSTOMER_PRODUCTS_PATH)
                    row_p = df_p[df_p["product_id"].astype(str).str.strip() == str(pricing_state["product_id"]).strip()]
                    cat_name = str(row_p.iloc[0].get("category", "Other")).strip() if not row_p.empty else "Other"
                except Exception:
                    cat_name = "Other"
                
                applied_uplift_pct = result.get("event_uplift_pct", 0.0)
                
                col_e5_1, col_e5_2 = st.columns(2)
                
                with col_e5_1:
                    st.markdown(
                        f"""
                        <div style="padding: 1.2rem; border-radius: 8px; border-left: 4px solid #6f42c1; background-color: #f8f9fc; height: 100%;">
                            <h4 style="margin-top: 0; color: #6f42c1;">Business Opportunity Detail</h4>
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr><td style="padding: 4px 0;"><b>Event Type:</b></td><td style="text-align: right;">{e5.get('event_type')}</td></tr>
                                <tr><td style="padding: 4px 0;"><b>Attendance:</b></td><td style="text-align: right;">{e5.get('attendance', 0):,} people</td></tr>
                                <tr><td style="padding: 4px 0;"><b>Category:</b></td><td style="text-align: right;">{cat_name}</td></tr>
                                <tr><td style="padding: 4px 0;"><b>Impact Level:</b></td><td style="text-align: right; font-weight: bold; color: {'#e74a3b' if e5.get('impact_level') == 'EXTREME' else '#f6c23e' if e5.get('impact_level') == 'HIGH' else '#36b9cc' if e5.get('impact_level') == 'MEDIUM' else '#858796'};">{e5.get('impact_level')}</td></tr>
                                <tr><td style="padding: 4px 0;"><b>Opportunity Score:</b></td><td style="text-align: right; font-weight: bold;">{e5.get('event_opportunity_score', 0.0):.1f}%</td></tr>
                                <tr><td style="padding: 4px 0;"><b>Applied Uplift:</b></td><td style="text-align: right; font-weight: bold; color: #1cc88a;">+{applied_uplift_pct:.1f}%</td></tr>
                            </table>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                with col_e5_2:
                    st.markdown(
                        """
                        <div style="padding: 1.2rem; border-radius: 8px; border-left: 4px solid #4e73df; background-color: #f8f9fc; height: 100%;">
                            <h4 style="margin-top: 0; color: #4e73df;">Why Event Uplift?</h4>
                            <ul style="margin-bottom: 0; padding-left: 1.2rem;">
                        """,
                        unsafe_allow_html=True
                    )
                    
                    reasoning_list = e5.get("reasoning", [])
                    if not reasoning_list:
                        st.markdown("<li>Nearby event detected</li>", unsafe_allow_html=True)
                    else:
                        for reason in reasoning_list:
                            if reason == "Sports Match":
                                desc = "Large sports match event nearby."
                            elif reason == "Festival":
                                desc = "Festival event scheduled nearby."
                            elif reason == "Concert":
                                desc = "Concert event scheduled nearby."
                            elif reason == "Political Rally":
                                desc = "Political rally event scheduled nearby."
                            elif reason == "Local Fair":
                                desc = "Local fair event scheduled nearby."
                            elif reason == "Large Attendance":
                                desc = "High attendance expected, driving strong local demand."
                            elif reason == "Moderate Attendance":
                                desc = "Moderate attendance expected, driving regular demand surge."
                            elif reason == "Small Attendance":
                                desc = "Minor attendance expected, low demand influence."
                            elif "Category" in reason:
                                desc = f"Product category ({reason}) strongly associated with event demand."
                            elif reason == "Very Close To Venue":
                                desc = "Store is located extremely close to venue (within 1km)."
                            elif reason == "Close To Venue":
                                desc = "Store is located close to venue (within 3km)."
                            elif reason == "Moderate Proximity To Venue":
                                desc = "Store is located in moderate proximity to venue."
                            else:
                                desc = f"Event condition: {reason}."
                            st.markdown(f"<li>{desc}</li>", unsafe_allow_html=True)
                            
                    st.markdown(
                        """
                            </ul>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

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
