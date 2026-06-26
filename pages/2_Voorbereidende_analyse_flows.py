"""Streamlit sub-page: voorbereidende analyse flows & prijzen."""

import idea_consult_altair_theme  # noqa: F401 — Idea Consult-thema + NL getalnotatie

from ui.auth import check_password
from showcase.analyse_2 import render as render_analyse_2

check_password()
render_analyse_2()
