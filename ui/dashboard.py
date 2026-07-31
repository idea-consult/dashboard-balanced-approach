"""Dashboard page content (simulator)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from time import perf_counter
from typing import Any

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
from models.lden_data_loader import LdenLoadedData, load_lden_data
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

_SIM_CACHE_KEY = "_sim_result_cache"


def maybe_print_total_duration(total_seconds: float) -> None:
    """Print total app duration when debug mode is enabled."""
    if os.getenv("PRINT_TIMINGS", "false").strip().lower() != "true":
        return
    print(f"\n[PERF] app.total: {total_seconds * 1000:.2f} ms")


def _file_mtime(path: str) -> float:
    try:
        return Path(path).stat().st_mtime
    except OSError:
        return -1.0


@st.cache_data(show_spinner=False)
def _cached_lden_data(
    stocks_mtime: float,
    flow_mtime: float,
    prices_mtime: float,
    zones_mtime: float,
    measure_ids: tuple[str, ...],
) -> LdenLoadedData:
    """Cache band-aggregated Lden inputs; bust on input file mtime."""
    del stocks_mtime, flow_mtime, prices_mtime, zones_mtime  # cache keys only
    return load_lden_data(
        stocks_file=STOCKS_FILE,
        flow_size_file=FLOW_SIZE_FILE,
        stock_prices_file=STOCK_PRICES_FILE,
        zones_file=LDEN_ZONES_FILE,
        measure_ids=measure_ids,
    )


def _selection_cache_key(
    selected_zones: list[tuple[Any, tuple[str, ...]]],
    selected_overlays: list[tuple[Any, str | None]],
    ernstig_methode: str,
) -> str:
    payload = repr(
        (
            sorted((str(n), tuple(z)) for n, z in selected_zones),
            sorted((str(n), o) for n, o in selected_overlays),
            str(ernstig_methode),
            BEGINJAAR,
            EINDJAAR,
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    loaded = _cached_lden_data(
        _file_mtime(STOCKS_FILE),
        _file_mtime(FLOW_SIZE_FILE),
        _file_mtime(STOCK_PRICES_FILE),
        _file_mtime(selected_zones_file),
        measure_ids,
    )
    stock_manager = StockManager._from_loaded_lden(
        loaded, selected_zones_file, BEGINJAAR
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

    selected_zones = [
        (name, measure_selection_manager.get_selected_zones(str(name)))
        for name in measure_selection_manager.get_measure_descriptions().index
    ]
    selected_overlays = [
        (name, measure_selection_manager.get_selected_overlay(str(name)))
        for name in measure_selection_manager.get_measure_descriptions().index
    ]
    cache_key = _selection_cache_key(selected_zones, selected_overlays, ernstig_methode)
    cached = st.session_state.get(_SIM_CACHE_KEY)
    used_cache = (
        isinstance(cached, dict)
        and cached.get("key") == cache_key
        and cached.get("stock_manager") is not None
    )
    if used_cache:
        stock_manager = cached["stock_manager"]
        kost_overheid = cached["kost_overheid"]
        kost_prive = cached["kost_prive"]
        measure_selection_manager = cached["measure_selection_manager"]
    else:
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
        sim_state = simulation_engine.load_inputs(
            BEGINJAAR, EINDJAAR, selected_zones, selected_overlays=selected_overlays
        )
        sim_state = simulation_engine.run_simulation_state(sim_state)
        sim_outputs = simulation_engine.build_outputs(sim_state)
        simulation_engine.persist_outputs(sim_outputs)
        kost_overheid, kost_prive = simulation_engine.get_total_costs()
        st.session_state[_SIM_CACHE_KEY] = {
            "key": cache_key,
            "stock_manager": stock_manager,
            "kost_overheid": kost_overheid,
            "kost_prive": kost_prive,
            "measure_selection_manager": measure_selection_manager,
        }

    with st.skeleton():
        render_metrics(stock_manager, kost_overheid, kost_prive)

    with st.skeleton():
        render_charts(stock_manager)

    with st.skeleton():
        if not used_cache:
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
