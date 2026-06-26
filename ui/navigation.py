"""Multipage navigation (st.navigation) for dashboard + showcase pages."""

import streamlit as st

from ui.app_pages import PAGE_ANALYSE_FLOWS, PAGE_ANALYSE_STOCKS
from ui.dashboard import render_dashboard

PAGE_DASHBOARD = st.Page(render_dashboard, title="Dashboard", default=True)


def run_app_navigation() -> None:
    """Register pages and run the active page."""
    pg = st.navigation(
        {
            "Simulator": [PAGE_DASHBOARD],
            "Voorbereidende analyse": [PAGE_ANALYSE_STOCKS, PAGE_ANALYSE_FLOWS],
        }
    )
    pg.run()
