"""Main Streamlit application for the simulation dashboard."""

import sys
import unittest

# Run critical tests at startup
loader = unittest.TestLoader()
suite = loader.loadTestsFromName("tests.test_flow_manager.TestFlowManagerIsolatievoorschriften")
result = unittest.TextTestRunner(verbosity=0).run(suite)
if not result.wasSuccessful():
    sys.exit(1)

import streamlit as st

from config import (
    STOCK_FILE,
    FLOW_FILE,
    BESCHRIJVING_MAATREGELEN_FILE,
    OUTPUT_STOCK_FILE,
    ZONES,
    BEGINJAAR,
    EINDJAAR,
)
from models.stock_manager import StockManager
from models.flow_manager import FlowManager
from models.validation import get_conflict_message
from simulation.engine import SimulationEngine
from ui.auth import check_password
from ui.components import (
    render_sidebar_controls,
    render_metrics,
    render_total_cost,
    render_charts,
)

# Authentication
check_password()

# Page configuration
st.set_page_config(layout="wide")

# Initialize managers
stock_manager = StockManager(STOCK_FILE)
flow_manager = FlowManager(FLOW_FILE, BESCHRIJVING_MAATREGELEN_FILE)

# Render sidebar controls en toon eventuele conflicten centraal
conflicts = render_sidebar_controls(flow_manager)
if conflicts:
    st.error("**Incompatibele maatregelcombinaties:**")
    for zone, measure1, measure2 in conflicts:
        st.error(get_conflict_message(zone, measure1, measure2, flow_manager))
    st.stop()

# Run simulation
simulation_engine = SimulationEngine(stock_manager, flow_manager, ZONES)
simulation_engine.run_simulation(BEGINJAAR, EINDJAAR)

# Save results
stock_manager.save(OUTPUT_STOCK_FILE)

# Render UI
render_metrics(stock_manager)
render_total_cost(flow_manager)
render_charts(stock_manager)
