"""Standalone showcase for contour_analyse_2 (flows & prijzen)."""

import streamlit as st

import idea_consult_altair_theme  # noqa: F401 — Idea Consult-thema + NL getalnotatie

from showcase.analyse_2 import render

# uv run streamlit run contour_analyse_2_showcase.py
st.set_page_config(
    page_title="Voorbereidende analyse — flows",
    layout="wide",
)
render()
