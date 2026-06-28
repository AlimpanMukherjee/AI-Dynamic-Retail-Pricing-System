def show_page():
    import streamlit as st
    import pandas as pd
    from frontend.services.competitor_service import (
        load_competitor_data,
        update_competitor_data,
    )

    st.title("📦 Competitor Price Upload")
    st.markdown(
        "Upload a CSV or Excel spreadsheet to refresh competitor pricing. Only rows matching **product_id + competitor_name** are updated; all other records stay unchanged."
    )

    uploaded_file = st.file_uploader("Upload Competitor Pricing CSV or Excel", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".xlsx"):
                upload_df = pd.read_excel(uploaded_file, engine='openpyxl')
            else:
                upload_df = pd.read_csv(uploaded_file)
            st.subheader("Uploaded Data Preview")
            st.dataframe(upload_df)

            if st.button("Update Competitor Data"):
                result = update_competitor_data(upload_df)
                if not result.get("valid", False):
                    st.error("Validation failed")
                    st.json(result["errors"])  # Show detailed error report
                else:
                    st.success("Competitor data updated successfully")
                    st.write({
                        "Rows Uploaded": len(upload_df),
                        "Existing SKUs Updated": result["updated"],
                        "New SKUs Added": result["inserted"],
                    })
                    # Show a preview of the merged dataset (first 20 rows)
                    merged = load_competitor_data()
                    st.subheader("Current Competitor Data (first 20 rows)")
                    st.dataframe(merged.head(20))
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
