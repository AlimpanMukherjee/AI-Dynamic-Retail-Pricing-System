import streamlit as st
from frontend.services.inventory_service import process_inventory_upload

def show_page():
    st.title("📦 Inventory snapshot Ingestion")
    st.markdown("Upload inventory updates to refresh current operational levels and append logs to the historical archive.")
    st.markdown("---")

    st.subheader("Upload Snapshot Panel")
    st.info("Supported file types: **CSV** or **Excel (.xlsx)**. Required columns: `product_id` and `current_stock` (or `stock`).")

    uploaded_file = st.file_uploader(
        "Choose an inventory spreadsheet to upload", 
        type=["csv", "xlsx"],
        help="Select a CSV or Excel spreadsheet to process."
    )

    if uploaded_file is not None:
        mode_selection = st.radio(
            "Select Upload Mode",
            options=["Initialize Inventory", "Restock Inventory", "Overwrite Inventory"],
            index=1,
            help="Initialize: Create initial operational state (fails if file already exists). Restock: Add incoming stock to current stock. Overwrite: Overwrite existing stock values directly."
        )

        confirm_overwrite = False
        if mode_selection == "Overwrite Inventory":
            confirm_overwrite = st.checkbox("⚠️ Confirm administrative override (overwrites current stock values)", value=False)

        if st.button("Validate & Process Snapshot", type="primary"):
            if mode_selection == "Overwrite Inventory" and not confirm_overwrite:
                st.warning("⚠️ You must check the confirmation box to run Overwrite Inventory.")
            else:
                mode_map = {
                    "Initialize Inventory": "initialize",
                    "Restock Inventory": "restock",
                    "Overwrite Inventory": "overwrite"
                }
                mode = mode_map[mode_selection]
                try:
                    with st.spinner("Performing backup, validation, and database updates..."):
                        summary = process_inventory_upload(uploaded_file, mode=mode)
                    
                    st.success("🎉 Inventory Ingestion Completed Successfully!")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Processed Count", f"{summary['rows_processed']}")
                    with col2:
                        st.metric("New SKUs Inserted", f"{summary['rows_inserted']}")
                    with col3:
                        st.metric("SKUs Stock Updated", f"{summary['rows_updated']}")
                    with col4:
                        st.metric("History Records Logged", f"{summary['history_rows_added']}")
                        
                    st.info(f"💡 **Technical Note**: The operational inventory levels were updated using '{mode_selection}' mode.")
                except Exception as e:
                    st.error(f"❌ **Validation/Ingestion Error**:\n\n{str(e)}")
