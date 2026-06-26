"""Streamlit Page objects shared by navigation and footer links."""

import streamlit as st

PAGE_ANALYSE_STOCKS = st.Page(
    "pages/1_Voorbereidende_analyse_stocks.py",
    title="Analyse 1 — Stocks & intersecties",
)
PAGE_ANALYSE_FLOWS = st.Page(
    "pages/2_Voorbereidende_analyse_flows.py",
    title="Analyse 2 — Flow rates & prijzen",
)
