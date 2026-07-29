"""Inject IDEA Consult Aptos fonts into the Streamlit UI."""

from __future__ import annotations

import base64
from functools import lru_cache

import streamlit as st

from reports.brand import APTOS_FONT_PATHS


@lru_cache(maxsize=1)
def _aptos_font_face_css() -> str:
    regular_path, bold_path = APTOS_FONT_PATHS
    if not regular_path.exists() or not bold_path.exists():
        return ""

    regular = base64.b64encode(regular_path.read_bytes()).decode("ascii")
    bold = base64.b64encode(bold_path.read_bytes()).decode("ascii")
    return f"""
@font-face {{
  font-family: "Aptos";
  src: url(data:font/ttf;base64,{regular}) format("truetype");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}}
@font-face {{
  font-family: "Aptos";
  src: url(data:font/ttf;base64,{bold}) format("truetype");
  font-weight: 600 700;
  font-style: normal;
  font-display: swap;
}}
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
.stMarkdown, .stText, .stCaption, .stMetric, .stButton, .stSelectbox,
.stMultiSelect, .stRadio, .stCheckbox, .stTextInput, .stNumberInput,
.stSlider, .stExpander, label, button, input, textarea, p, span, div {{
  font-family: "Aptos", "Segoe UI", sans-serif !important;
}}
"""


def apply_aptos_font() -> None:
    """Load Aptos for Streamlit chrome (and Vega charts that request Aptos)."""
    css = _aptos_font_face_css()
    if not css:
        return
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
