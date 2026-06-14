import streamlit as st
from frontend.services.sales_service import append_sales_upload

def show_page():
    st.title("📈 Daily Sales Ingestion")
    st.markdown("Upload daily transaction spreadsheets to append new sales records to the master log.")
    st.markdown("---")

    st.subheader("File Upload Panel")
    st.info("Supported file types: **CSV** or **Excel (.xlsx)**. Required columns: `date`, `product_id`, `units_sold`, `selling_price`.")

    uploaded_file = st.file_uploader(
        "Choose a sales spreadsheet to upload", 
        type=["csv", "xlsx"], 
        help="Make sure column headers match the requirements exactly."
    )

    if uploaded_file is not None:
        if st.button("Validate & Import Sales Data", type="primary"):
            try:
                with st.spinner("Analyzing spreadsheet columns and rows..."):
                    summary = append_sales_upload(uploaded_file)
                
                st.success("🎉 Sales Upload Successful!")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Rows Processed", f"{summary['rows_processed']:,}")
                with col2:
                    st.metric("Unique Products Affected", f"{summary['products_affected']}")
                with col3:
                    st.metric("Deduplicated Rows Added", f"{summary['rows_inserted']}")
                    
                st.info(f"📅 **Ingested Date Range**: {summary['start_date']} ➔ {summary['end_date']}")
            except Exception as e:
                st.error(f"❌ **Validation/Upload Error**:\n\n{str(e)}")
