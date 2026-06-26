"""Dashboard page content (simulator)."""

import os
from time import perf_counter

import pandas as pd
import streamlit as st

from config import (
    BEGINJAAR,
    EINDJAAR,
    FLOW_RULES_FILE,
    FLOW_SIZE_FILE,
    LDEN_ZONES_FILE,
    MEASURE_COSTS_FILE,
    MEASURES_FILE,
    OUTPUT_FLOW_LOG_ZONE_FILE,
    OUTPUT_STOCK_FILE,
    STOCK_PRICES_FILE,
    STOCKS_FILE,
)
from models.measure_selection_manager import MeasureSelectionManager
from models.stock_manager import StockManager
from models.validation import get_conflict_message
from simulation.engine import SimulationEngine
from ui.components import (
    render_charts,
    render_flow_log_zone_table,
    render_leefbaarheidspunten_panel,
    render_metrics,
    render_sidebar_controls,
)
from ui.showcase_links import render_showcase_footer
from ui.throttle import spinner_step


def maybe_print_total_duration(total_seconds: float) -> None:
    """Print total app duration when debug mode is enabled."""
    if os.getenv("PRINT_TIMINGS", "false").strip().lower() != "true":
        return
    print(f"\n[PERF] app.total: {total_seconds * 1000:.2f} ms")


def render_dashboard() -> None:
    """Run simulation dashboard (maatregelen, KPI's, grafieken)."""
    app_total_start = perf_counter()

    st.sidebar.caption("Contour: Lden (1 dB, echte data)")
    st.sidebar.info("Lnight-data is nog niet beschikbaar en wordt verborgen.")

    selected_zones_file = LDEN_ZONES_FILE

    with spinner_step("init"):
        measure_ids = tuple(
            pd.read_csv(MEASURES_FILE, usecols=["measure_id"])["measure_id"].astype(str)
        )
        stock_manager = StockManager.from_lden_analysis(
            stocks_file=STOCKS_FILE,
            flow_size_file=FLOW_SIZE_FILE,
            stock_prices_file=STOCK_PRICES_FILE,
            zones_file=selected_zones_file,
            beginjaar=BEGINJAAR,
            measure_ids=measure_ids,
        )
        measure_selection_manager = MeasureSelectionManager(
            zones_file=selected_zones_file,
            measures_file=MEASURES_FILE,
            flow_rules_file=FLOW_RULES_FILE,
            measure_costs_file=MEASURE_COSTS_FILE,
        )
        zones = stock_manager.get_zones()

    conflicts = render_sidebar_controls(measure_selection_manager, zones, stock_manager)
    if conflicts:
        st.error("**Incompatibele maatregelcombinaties:**")
        for zone, measure1, measure2 in conflicts:
            st.error(
                get_conflict_message(zone, measure1, measure2, measure_selection_manager)
            )
        st.stop()

    with spinner_step("simulation"):
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

    with spinner_step("render"):
        render_metrics(stock_manager, kost_overheid, kost_prive)

    with spinner_step("leefbaarheidspunten"):
        render_leefbaarheidspunten_panel(stock_manager, "Lden", simulation_engine)

    with spinner_step("charts"):
        render_charts(stock_manager)

    with spinner_step("save"):
        stock_manager.save(OUTPUT_STOCK_FILE)
        render_flow_log_zone_table(OUTPUT_FLOW_LOG_ZONE_FILE)

    render_showcase_footer()

    maybe_print_total_duration(perf_counter() - app_total_start)
