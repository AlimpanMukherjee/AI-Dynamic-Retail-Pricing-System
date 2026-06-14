import streamlit as st

def render_metric_card(label: str, value: str, delta: str = None, border_color: str = "#4e73df"):
    """
    Renders a premium visual card container with custom CSS styled border indicators.
    """
    card_html = f"""
    <div style="
        padding: 1.25rem;
        border-radius: 8px;
        border-left: 5px solid {border_color};
        background-color: #ffffff;
        box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 120, 0.1);
        margin-bottom: 1rem;
    ">
        <div style="font-size: 0.8rem; text-transform: uppercase; font-weight: 700; color: #858796; letter-spacing: 0.05rem;">
            {label}
        </div>
        <div style="font-size: 1.6rem; font-weight: 700; color: #2e303d; margin-top: 0.25rem;">
            {value}
        </div>
    """
    
    if delta:
        color = "#1cc88a" if delta.startswith("+") else "#e74a3b" if delta.startswith("-") else "#858796"
        card_html += f"""
        <div style="font-size: 0.85rem; font-weight: 600; color: {color}; margin-top: 0.25rem;">
            {delta}
        </div>
        """
        
    card_html += "</div>"
    st.markdown(card_html, unsafe_allow_html=True)
