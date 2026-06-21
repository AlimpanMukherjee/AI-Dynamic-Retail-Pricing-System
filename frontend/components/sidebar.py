import streamlit as st

def render_sidebar():
    """
    Renders the navigation sidebar in Streamlit and manages navigation state.
    """
    st.sidebar.title("🎯 AI Retail Pricing")
    st.sidebar.caption("System Management & Forecasting Console")
    st.sidebar.markdown("---")

    # Defined navigation options
    options = [
        "📊 Dashboard",
        "📈 Sales Upload",
        "📦 Inventory Upload",
        "📦 Competitor Upload",
        "🔍 Product Search",
        "💸 Run Pricing",
        "🕰️ Pricing History",
        "🧠 Model Management",
        "🚨 Alerts"
    ]

    # Resolve index of current page if set in session state
    current_page_idx = 0
    if "page" in st.session_state:
        for idx, opt in enumerate(options):
            if opt.endswith(st.session_state.page):
                current_page_idx = idx
                break

    # Render selector
    choice = st.sidebar.radio("Console Navigation", options, index=current_page_idx)

    # Extract clean page name by removing emoji prefixes
    page_name = choice.split(" ", 1)[1]
    st.session_state.page = page_name

    st.sidebar.markdown("---")
    st.sidebar.info(
        "💡 **Operation Tip**:\n\n"
        "Use the uploader sections to submit transaction files. The pricing engines automatically leverage new uploads during execution."
    )
