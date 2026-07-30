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
    render_metrics,
    render_sidebar_controls,
)
from ui.report_download import render_pdf_report_download
from ui.showcase_links import render_showcase_footer


def maybe_print_total_duration(total_seconds: float) -> None:
    """Print total app duration when debug mode is enabled."""
    if os.getenv("PRINT_TIMINGS", "false").strip().lower() != "true":
        return
    print(f"\n[PERF] app.total: {total_seconds * 1000:.2f} ms")


def render_dashboard() -> None:
    """Run simulation dashboard (maatregelen, KPI's, grafieken)."""
    app_total_start = perf_counter()

    st.sidebar.caption("Contour: Lden (1 dB, echte data)")
    st.sidebar.info(
        "Lnight als apart dashboard is nog niet beschikbaar. "
        "Wel beschikbaar: overlays Lnight45 en NA70 op het Lden-dashboard."
    )

    selected_zones_file = LDEN_ZONES_FILE

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

    conflicts, ernstig_methode = render_sidebar_controls(
        measure_selection_manager, zones, stock_manager
    )
    if conflicts:
        st.error("**Incompatibele maatregelcombinaties:**")
        for zone, measure1, measure2 in conflicts:
            st.error(
                get_conflict_message(zone, measure1, measure2, measure_selection_manager)
            )
        st.stop()

    simulation_engine = SimulationEngine(
        stock_manager,
        measure_selection_manager,
        zones,
        zones_file=selected_zones_file,
        measures_file=MEASURES_FILE,
        flow_rules_file=FLOW_RULES_FILE,
        measure_costs_file=MEASURE_COSTS_FILE,
        ernstig_gehinderden_methode=ernstig_methode,
    )
    selected_zones = [
        (name, measure_selection_manager.get_selected_zones(str(name)))
        for name in measure_selection_manager.get_measure_descriptions().index
    ]
    selected_overlays = [
        (name, measure_selection_manager.get_selected_overlay(str(name)))
        for name in measure_selection_manager.get_measure_descriptions().index
    ]
    sim_state = simulation_engine.load_inputs(
        BEGINJAAR, EINDJAAR, selected_zones, selected_overlays=selected_overlays
    )
    sim_state = simulation_engine.run_simulation_state(sim_state)
    sim_outputs = simulation_engine.build_outputs(sim_state)
    simulation_engine.persist_outputs(sim_outputs)
    kost_overheid, kost_prive = simulation_engine.get_total_costs()

    with st.skeleton():
        render_metrics(stock_manager, kost_overheid, kost_prive)

    with st.skeleton():
        render_charts(stock_manager)

    with st.skeleton():
        stock_manager.save(OUTPUT_STOCK_FILE)
        render_flow_log_zone_table(OUTPUT_FLOW_LOG_ZONE_FILE)

    render_pdf_report_download(
        stock_manager=stock_manager,
        measure_selection_manager=measure_selection_manager,
        kost_overheid=kost_overheid,
        kost_prive=kost_prive,
        ernstig_gehinderden_methode=ernstig_methode,
    )

    render_showcase_footer()

    maybe_print_total_duration(perf_counter() - app_total_start)
