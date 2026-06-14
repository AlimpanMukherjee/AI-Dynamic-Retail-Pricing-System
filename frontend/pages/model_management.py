import streamlit as st
import pandas as pd
from frontend.services.retraining_service import (
    load_model_registry,
    get_active_model_details,
    execute_model_retraining
)
from backend.retraining.retrain_model import activate_model
from frontend.components.metrics import render_metric_card

def show_page():
    st.title("🧠 ML Model Management & Retraining Console")
    st.markdown("Monitor performance of the XGBoost Demand Forecaster (Engine 2), retrain on new sales, and audit model versions.")
    st.markdown("---")

    active_model = get_active_model_details()
    
    # Render Active Model Details
    if active_model:
        st.subheader("🎯 Active Forecasting Model")
        
        # Grid layout for model properties
        col_ver, col_date, col_rows = st.columns(3)
        with col_ver:
            render_metric_card("Active Version", active_model["model_version"], border_color="#1cc88a")
        with col_date:
            render_metric_card("Training Date", str(active_model["training_date"]), border_color="#4e73df")
        with col_rows:
            render_metric_card("Training Samples", f"{active_model['training_rows']:,}", border_color="#36b9cc")

        col_tr, col_val, col_te = st.columns(3)
        with col_tr:
            render_metric_card("Train R²", f"{active_model['train_r2']:.4f}", border_color="#858796")
        with col_val:
            render_metric_card("Validation R² (Gate Value)", f"{active_model['val_r2']:.4f}", border_color="#f6c23e")
        with col_te:
            render_metric_card("Test R²", f"{active_model['test_r2']:.4f}", border_color="#e74a3b")
    else:
        st.warning("⚠️ No models registered or active in the system. Retrain a model below to initialize.")

    st.markdown("---")

    # Retraining Control Panel
    st.subheader("🚀 Trigger Engine 2 Retraining")
    st.markdown(
        "Training runs chronological time-series cross-validation splits using the combined "
        "`sales_history.csv` dataset, fitting regularized XGBoost parameters."
    )

    # Safety Gate Options
    override_gate = st.checkbox(
        "⚠️ Override Validation Safety Gate (Force-activate new model even if validation R² is lower)",
        value=False
    )

    if st.button("🔥 Execute Model Retraining", type="primary", use_container_width=True):
        try:
            with st.spinner("Loading sales databases, pre-processing features, and fitting XGBoost estimators..."):
                res = execute_model_retraining(force_override_gate=override_gate)
                
            if res["status"] == "activated":
                st.success(
                    f"🏆 **Model Retrained and Activated Successfully!**\n\n"
                    f"• **Version Created**: `{res['version']}`\n"
                    f"• **Training Rows**: {res['training_rows']:,}\n"
                    f"• **New Validation R²**: {res['new_val_r2']:.4f}\n"
                    f"• **Previous R²**: {res['old_val_r2']}\n"
                    f"• **Test R²**: {res['test_r2']:.4f}"
                )
            else:
                st.warning(
                    f"🛡️ **Retraining Completed, but Safety Gate Triggered!**\n\n"
                    f"The newly trained model version `{res['version']}` has a validation R² score of "
                    f"`{res['new_val_r2']:.4f}`, which does not exceed the current active model's R² "
                    f"(`{res['old_val_r2']:.4f}`).\n\n"
                    f"**Action**: The model version has been logged in the registry, but the older, more performant "
                    f"model remains active for pricing calculations. Check the override checkbox above to force activation."
                )
            st.rerun()
        except Exception as e:
            st.error(f"❌ Retraining operation failed: {str(e)}")

    st.markdown("---")

    # Model Version Registry Audit Table
    st.subheader("📜 Model Version Registry")
    df_reg = load_model_registry()

    if df_reg.empty:
        st.info("No historical model runs logged in registry.")
    else:
        # Prettify table
        df_display = df_reg.copy()
        df_display["active"] = df_display["active"].apply(lambda x: "🟢 ACTIVE" if x else "⚪ Inactive")
        df_display["training_rows"] = df_display["training_rows"].map('{:,}'.format)
        
        # Display table
        from frontend.components.tables import render_styled_table
        render_styled_table(df_display)

        # Allow manual activation form
        st.markdown("#### ⚙️ Manual Active Version Override")
        with st.form("activation_form"):
            target_v = st.selectbox(
                "Select version to manually activate",
                sorted(list(df_reg["model_version"].unique()))
            )
            sub = st.form_submit_button("Activate Model Version")
            if sub:
                if activate_model(target_v):
                    st.cache_data.clear()
                    st.success(f"Successfully activated model version {target_v}!")
                    st.rerun()
                else:
                    st.error("Failed to activate selected version.")
