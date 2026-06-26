"""Standalone showcase for contour_analyse_1 (stocks & intersecties)."""

import streamlit as st

import idea_consult_altair_theme  # noqa: F401 — Idea Consult-thema + NL getalnotatie

from showcase.analyse_1 import render

# uv run streamlit run contour_analyse_1_showcase.py
st.set_page_config(
    page_title="Voorbereidende analyse — stocks",
    layout="wide",
)
render()
