"""Footer links to showcase sub-pages."""

import streamlit as st

from ui.app_pages import PAGE_ANALYSE_FLOWS, PAGE_ANALYSE_STOCKS


def render_showcase_footer() -> None:
    """Link to showcase pages via st.page_link (requires st.navigation in app.py)."""
    st.divider()
    st.subheader("Voorbereidende data-analyse")
    st.caption("Documentatie en grafieken van de data-opbouw voor dit dashboard.")
    col1, col2 = st.columns(2)
    with col1:
        st.page_link(
            PAGE_ANALYSE_STOCKS,
            label="Analyse 1 — Stocks & intersecties",
            use_container_width=True,
        )
    with col2:
        st.page_link(
            PAGE_ANALYSE_FLOWS,
            label="Analyse 2 — Flow rates & prijzen",
            use_container_width=True,
        )
