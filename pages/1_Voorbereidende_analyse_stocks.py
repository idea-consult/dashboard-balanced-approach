"""Streamlit sub-page: voorbereidende analyse stocks & intersecties."""

import idea_consult_altair_theme  # noqa: F401 — Idea Consult-thema + NL getalnotatie

from ui.auth import check_password
from showcase.analyse_1 import render as render_analyse_1

check_password()
render_analyse_1()
