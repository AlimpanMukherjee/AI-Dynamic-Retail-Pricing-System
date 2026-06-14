import os
import shutil
import streamlit as st
import backend.config as cfg
from backend.inventory.inventory_ingestion import initialize_inventory_datasets

def initialize_application():
    """
    Performs startup verification, directory creation, and legacy dataset auto-migrations.
    """
    if "initialized" in st.session_state and st.session_state.initialized:
        return

    # 1. Trigger legacy inventory database auto-migration (inventory.csv -> inventory_current & inventory_history)
    initialize_inventory_datasets()

    # 2. Check and migrate legacy sales dataset (sales.csv -> sales_history.csv)
    sales_history_path = cfg.CUSTOMER_SALES_PATH
    data_dir = os.path.dirname(sales_history_path)
    legacy_sales_path = os.path.join(data_dir, "sales.csv")

    if not os.path.exists(sales_history_path) and os.path.exists(legacy_sales_path):
        try:
            os.makedirs(data_dir, exist_ok=True)
            shutil.copyfile(legacy_sales_path, sales_history_path)
            logger_msg = f"Application Startup: Auto-migrated sales.csv to {sales_history_path}"
            print(logger_msg)
        except Exception as e:
            print(f"Error during legacy sales migration: {str(e)}")

    # 3. Create raw upload recovery directories if missing
    os.makedirs(cfg.BACKUP_INVENTORY_DIR, exist_ok=True)

    # 4. Initialize model registry and training directories
    try:
        from backend.retraining.retrain_model import _initialize_registry
        _initialize_registry()
    except Exception as e:
        print(f"Error initializing model registry: {str(e)}")

    st.session_state.initialized = True


# Initialize application datasets & configurations
initialize_application()

# Set up page configurations
st.set_page_config(
    page_title="AI Dynamic Retail Pricing System",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize navigation route if missing
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

# Load sidebar navigation layout
from frontend.components.sidebar import render_sidebar
render_sidebar()

# Page Route Dispatcher
page = st.session_state.page

if page == "Dashboard":
    from frontend.pages.dashboard import show_page
    show_page()
elif page == "Sales Upload":
    from frontend.pages.sales_upload import show_page
    show_page()
elif page == "Inventory Upload":
    from frontend.pages.inventory_upload import show_page
    show_page()
elif page == "Product Search":
    from frontend.pages.product_search import show_page
    show_page()
elif page == "Run Pricing":
    from frontend.pages.run_pricing import show_page
    show_page()
elif page == "Pricing History":
    from frontend.pages.pricing_history import show_page
    show_page()
elif page == "Model Management":
    from frontend.pages.model_management import show_page
    show_page()
elif page == "Alerts":
    from frontend.pages.alerts import show_page
    show_page()
