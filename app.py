"""Main Streamlit application for the simulation dashboard."""

import os
import sys
import unittest

# Optional startup tests (disabled by default for faster UI reruns)
if os.getenv("RUN_STARTUP_TESTS", "false").strip().lower() == "true":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(
        "tests.test_measure_selection_manager.TestMeasureSelectionManagerConnection"
    )
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)

import streamlit as st

import idea_consult_altair_theme  # noqa: F401 — Idea Consult-thema + NL getalnotatie

from ui.auth import check_password
from ui.navigation import run_app_navigation

check_password()

st.set_page_config(layout="wide", page_title="Balanced approach — simulator")

run_app_navigation()
