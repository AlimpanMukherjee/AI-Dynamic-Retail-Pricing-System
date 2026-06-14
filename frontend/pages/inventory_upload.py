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
        help="The system will run UPSERT on current stocks and append copy to history logs."
    )

    if uploaded_file is not None:
        if st.button("Validate & Process Snapshot", type="primary"):
            try:
                with st.spinner("Performing backup, validation, and database updates..."):
                    summary = process_inventory_upload(uploaded_file)
                
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
                    
                st.info("💡 **Technical Note**: The operational inventory levels was refreshed using UPSERT logic. Unaltered properties were safely preserved.")
            except Exception as e:
                st.error(f"❌ **Validation/Ingestion Error**:\n\n{str(e)}")
