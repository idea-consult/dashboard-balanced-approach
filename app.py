"""Main Streamlit application for the simulation dashboard."""

import sys
import unittest
import os
from time import perf_counter

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

from config import (
    MEASURES_FILE,
    FLOW_RULES_FILE,
    MEASURE_COSTS_FILE,
    LDEN_CONTOUR_FILE,
    LNIGHT_CONTOUR_FILE,
    LDEN_ZONES_FILE,
    LNIGHT_ZONES_FILE,
    OUTPUT_STOCK_FILE,
    OUTPUT_FLOW_LOG_ZONE_FILE,
    BEGINJAAR,
    EINDJAAR,
)
from models.stock_manager import StockManager
from models.measure_selection_manager import MeasureSelectionManager
from models.validation import get_conflict_message
from simulation.engine import SimulationEngine
from ui.auth import check_password
from ui.components import (
    render_sidebar_controls,
    render_metrics,
    render_charts,
    render_leefbaarheidspunten_weight_controls,
    render_flow_log_zone_table,
)


def maybe_print_total_duration(total_seconds: float) -> None:
    """Print total app duration when debug mode is enabled."""
    if os.getenv("PRINT_TIMINGS", "false").strip().lower() != "true":
        return
    print(f"\n[PERF] app.total: {total_seconds * 1000:.2f} ms")


# Authentication
check_password()

# Page configuration
st.set_page_config(layout="wide")
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
stock_manager = StockManager(selected_contour_file, selected_zones_file, BEGINJAAR)
measure_selection_manager = MeasureSelectionManager(
    zones_file=selected_zones_file,
    measures_file=MEASURES_FILE,
    flow_rules_file=FLOW_RULES_FILE,
    measure_costs_file=MEASURE_COSTS_FILE,
)
zones = stock_manager.get_zones()

# Render sidebar controls en toon eventuele conflicten centraal
conflicts = render_sidebar_controls(measure_selection_manager, zones)
if conflicts:
    st.error("**Incompatibele maatregelcombinaties:**")
    for zone, measure1, measure2 in conflicts:
        st.error(get_conflict_message(zone, measure1, measure2, measure_selection_manager))
    st.stop()

# Run simulation
simulation_engine = SimulationEngine(
    stock_manager,
    measure_selection_manager,
    zones,
    zones_file=selected_zones_file,
    measures_file=MEASURES_FILE,
    flow_rules_file=FLOW_RULES_FILE,
    measure_costs_file=MEASURE_COSTS_FILE,
)
selected_zones = [
    (name, measure_selection_manager.get_selected_zones(str(name)))
    for name in measure_selection_manager.get_measure_descriptions().index
]
sim_state = simulation_engine.load_inputs(BEGINJAAR, EINDJAAR, selected_zones)
sim_state = simulation_engine.run_simulation_state(sim_state)
sim_outputs = simulation_engine.build_outputs(sim_state)
simulation_engine.persist_outputs(sim_outputs)
kost_overheid, kost_prive = simulation_engine.get_total_costs()

# Leefbaarheidspunten (gewichten → berekening vóór KPI's)
with st.expander("Instelling leefbaarheidspunten per zone", expanded=False):
    leefbaarheidspunten_weights = render_leefbaarheidspunten_weight_controls(
        stock_manager, contour_type
    )
simulation_engine.calculate_leefbaarheidspunten(BEGINJAAR, EINDJAAR, leefbaarheidspunten_weights)

# Render UI
render_metrics(stock_manager, kost_overheid, kost_prive)
render_charts(stock_manager)

# Save results (inclusief leefbaarheidspunten na UI-instellingen)
stock_manager.save(OUTPUT_STOCK_FILE)
render_flow_log_zone_table(OUTPUT_FLOW_LOG_ZONE_FILE)

app_total_duration = perf_counter() - app_total_start
maybe_print_total_duration(app_total_duration)
