"""Main Streamlit application for the simulation dashboard."""

import sys
import unittest
import os
from time import perf_counter

# Optional startup tests (disabled by default for faster UI reruns)
if os.getenv("RUN_STARTUP_TESTS", "false").strip().lower() == "true":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName("tests.test_flow_manager.TestFlowManagerMeasureConnection")
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)

import streamlit as st

from config import (
    FLOW_FILE,
    LDEN_CONTOUR_FILE,
    LNIGHT_CONTOUR_FILE,
    LDEN_ZONES_FILE,
    LNIGHT_ZONES_FILE,
    BESCHRIJVING_MAATREGELEN_FILE,
    OUTPUT_STOCK_FILE,
    OUTPUT_FLOW_LOG_ZONE_FILE,
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
    render_charts,
    render_flow_log_zone_table,
)


def maybe_print_timings(timings: dict[str, float]) -> None:
    """Print timing stats to terminal when debug mode is enabled."""
    if os.getenv("PRINT_TIMINGS", "false").strip().lower() != "true":
        return
    print("\n[PERF] Timing per rerun (ms):")
    for step, seconds in sorted(timings.items(), key=lambda item: item[1], reverse=True):
        print(f"[PERF] {step}: {seconds * 1000:.2f}")


# Authentication
check_password()

# Page configuration
st.set_page_config(layout="wide")
timings: dict[str, float] = {}
app_total_start = perf_counter()

# Contour selection (day/night) in sidebar
with st.sidebar:
    contour_type = st.segmented_control(
        label="Contourtype",
        options=["Lden", "Lnight"],
        default="Lden",
        selection_mode="single",
        key="contour_type",
        width="stretch",
    )

if contour_type == "Lnight":
    selected_contour_file = LNIGHT_CONTOUR_FILE
    selected_zones_file = LNIGHT_ZONES_FILE
else:
    selected_contour_file = LDEN_CONTOUR_FILE
    selected_zones_file = LDEN_ZONES_FILE

# Initialize managers
init_start = perf_counter()
stock_manager = StockManager(selected_contour_file, selected_zones_file, BEGINJAAR)
flow_manager = FlowManager(FLOW_FILE, BESCHRIJVING_MAATREGELEN_FILE)
zones = stock_manager.get_zones()
timings["app.init_managers"] = perf_counter() - init_start

# Render sidebar controls en toon eventuele conflicten centraal
sidebar_start = perf_counter()
conflicts = render_sidebar_controls(flow_manager, zones)
timings["app.sidebar_controls"] = perf_counter() - sidebar_start
if conflicts:
    st.error("**Incompatibele maatregelcombinaties:**")
    for zone, measure1, measure2 in conflicts:
        st.error(get_conflict_message(zone, measure1, measure2, flow_manager))
    st.stop()

# Run simulation
sim_start = perf_counter()
simulation_engine = SimulationEngine(
    stock_manager,
    flow_manager,
    zones,
    zones_file=selected_zones_file,
)
simulation_engine.run_simulation(BEGINJAAR, EINDJAAR)
kost_overheid, kost_prive = simulation_engine.get_total_costs()
timings["app.run_simulation"] = perf_counter() - sim_start
timings.update(simulation_engine.get_timing_stats())

# Save results
save_start = perf_counter()
stock_manager.save(OUTPUT_STOCK_FILE)
timings["app.save_stock"] = perf_counter() - save_start

# Render UI
render_start = perf_counter()
render_metrics(stock_manager, kost_overheid, kost_prive)
render_charts(stock_manager)
render_flow_log_zone_table(OUTPUT_FLOW_LOG_ZONE_FILE)
timings["app.render_ui"] = perf_counter() - render_start
timings["app.total"] = perf_counter() - app_total_start

maybe_print_timings(timings)
