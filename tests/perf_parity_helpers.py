"""Helpers for performance-parity golden fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from config import (
    BEGINJAAR,
    EINDJAAR,
    FLOW_RULES_FILE,
    FLOW_SIZE_FILE,
    LDEN_ZONES_FILE,
    MEASURE_COSTS_FILE,
    MEASURES_FILE,
    STOCK_PRICES_FILE,
    STOCKS_FILE,
)
from models.measure_selection_manager import MeasureSelectionManager
from models.stock_manager import StockManager
from simulation.engine import SimulationEngine

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "perf_parity"

ACTIVE_MEASURES = (
    "woongebiedverbod",
    "woningverbod",
    "verkavelingsverbod",
)

FLOW_SORT_COLS = [
    "db_ondergrens",
    "jaar",
    "naam_flow",
    "inflow_stock_name",
    "outflow_stock_name",
]


def build_engine() -> tuple[SimulationEngine, MeasureSelectionManager, StockManager]:
    measure_ids = tuple(
        pd.read_csv(MEASURES_FILE, usecols=["measure_id"])["measure_id"].astype(str)
    )
    stock_manager = StockManager.from_lden_analysis(
        stocks_file=STOCKS_FILE,
        flow_size_file=FLOW_SIZE_FILE,
        stock_prices_file=STOCK_PRICES_FILE,
        zones_file=LDEN_ZONES_FILE,
        beginjaar=BEGINJAAR,
        measure_ids=measure_ids,
    )
    selection = MeasureSelectionManager(
        zones_file=LDEN_ZONES_FILE,
        measures_file=MEASURES_FILE,
        flow_rules_file=FLOW_RULES_FILE,
        measure_costs_file=MEASURE_COSTS_FILE,
    )
    zones = stock_manager.get_zones()
    engine = SimulationEngine(
        stock_manager,
        selection,
        zones,
        zones_file=LDEN_ZONES_FILE,
        measures_file=MEASURES_FILE,
        flow_rules_file=FLOW_RULES_FILE,
        measure_costs_file=MEASURE_COSTS_FILE,
        ernstig_gehinderden_methode="A",
    )
    return engine, selection, stock_manager


def apply_active_measures(
    selection: MeasureSelectionManager,
    measure_ids: Iterable[str],
    zones: Iterable[str],
) -> None:
    zone_tuple = tuple(str(z) for z in zones)
    for measure_id in measure_ids:
        selection.set_selected_zones(str(measure_id), zone_tuple)


def run_scenario(scenario: str) -> dict:
    """Run full load→sim→persist pipeline; return serialisable snapshot."""
    engine, selection, stock_manager = build_engine()
    zones = stock_manager.get_zones()
    if scenario == "active":
        apply_active_measures(selection, ACTIVE_MEASURES, zones)
    elif scenario != "baseline":
        raise ValueError(f"Unknown scenario: {scenario}")

    selected_zones = [
        (name, selection.get_selected_zones(str(name)))
        for name in selection.get_measure_descriptions().index
    ]
    selected_overlays = [
        (name, selection.get_selected_overlay(str(name)))
        for name in selection.get_measure_descriptions().index
    ]
    state = engine.load_inputs(
        BEGINJAAR, EINDJAAR, selected_zones, selected_overlays=selected_overlays
    )
    state = engine.run_simulation_state(state)
    outputs = engine.build_outputs(state)
    engine.persist_outputs(outputs)

    flow = pd.DataFrame(engine._flow_log_rows)
    if not flow.empty:
        flow = flow.sort_values(by=FLOW_SORT_COLS).reset_index(drop=True)

    stock = stock_manager.get_dataframe().reset_index().sort_values(
        by=["naam", "jaar", "zone"]
    ).reset_index(drop=True)

    kost_ov, kost_pr = engine.get_total_costs()
    return {
        "scenario": scenario,
        "sim_state": np.asarray(outputs.sim_state, dtype=np.float64),
        "bands": tuple(outputs.bands) if outputs.bands else (),
        "stock_names": tuple(outputs.stock_names),
        "kost_overheid": float(kost_ov),
        "kost_prive": float(kost_pr),
        "flow": flow,
        "stock": stock,
    }


def fixture_paths(scenario: str) -> dict[str, Path]:
    base = FIXTURE_DIR / scenario
    return {
        "meta": base.with_suffix(".meta.npz"),
        "flow": base.with_name(f"{scenario}_flow.parquet"),
        "stock": base.with_name(f"{scenario}_stock.parquet"),
    }


def write_fixture(snapshot: dict) -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    paths = fixture_paths(snapshot["scenario"])
    np.savez_compressed(
        paths["meta"],
        sim_state=snapshot["sim_state"],
        bands=np.asarray(snapshot["bands"], dtype=np.int64),
        stock_names=np.asarray(snapshot["stock_names"], dtype=object),
        kost_overheid=np.asarray([snapshot["kost_overheid"]], dtype=np.float64),
        kost_prive=np.asarray([snapshot["kost_prive"]], dtype=np.float64),
    )
    snapshot["flow"].to_parquet(paths["flow"], index=False)
    snapshot["stock"].to_parquet(paths["stock"], index=False)


def load_fixture(scenario: str) -> dict:
    paths = fixture_paths(scenario)
    meta = np.load(paths["meta"], allow_pickle=True)
    return {
        "scenario": scenario,
        "sim_state": meta["sim_state"],
        "bands": tuple(int(x) for x in meta["bands"].tolist()),
        "stock_names": tuple(str(x) for x in meta["stock_names"].tolist()),
        "kost_overheid": float(meta["kost_overheid"][0]),
        "kost_prive": float(meta["kost_prive"][0]),
        "flow": pd.read_parquet(paths["flow"]),
        "stock": pd.read_parquet(paths["stock"]),
    }


def assert_snapshots_equal(actual: dict, expected: dict, *, rtol: float = 1e-9) -> None:
    np.testing.assert_allclose(
        actual["sim_state"], expected["sim_state"], rtol=rtol, atol=1e-9
    )
    assert actual["bands"] == expected["bands"]
    assert actual["stock_names"] == expected["stock_names"]
    assert abs(actual["kost_overheid"] - expected["kost_overheid"]) <= 1e-6
    assert abs(actual["kost_prive"] - expected["kost_prive"]) <= 1e-6

    flow_a = actual["flow"].reset_index(drop=True)
    flow_e = expected["flow"].reset_index(drop=True)
    assert list(flow_a.columns) == list(flow_e.columns)
    assert len(flow_a) == len(flow_e)
    for col in flow_a.columns:
        if pd.api.types.is_numeric_dtype(flow_a[col]):
            np.testing.assert_allclose(
                flow_a[col].to_numpy(dtype=float),
                flow_e[col].to_numpy(dtype=float),
                rtol=rtol,
                atol=1e-9,
                err_msg=f"flow mismatch in {col}",
            )
        else:
            assert flow_a[col].astype(str).tolist() == flow_e[col].astype(str).tolist()

    stock_a = actual["stock"].reset_index(drop=True)
    stock_e = expected["stock"].reset_index(drop=True)
    assert list(stock_a.columns) == list(stock_e.columns)
    assert len(stock_a) == len(stock_e)
    for col in ("naam", "jaar", "zone"):
        assert stock_a[col].astype(str).tolist() == stock_e[col].astype(str).tolist()
    np.testing.assert_allclose(
        stock_a["aantal"].to_numpy(dtype=float),
        stock_e["aantal"].to_numpy(dtype=float),
        rtol=rtol,
        atol=1e-9,
        err_msg="stock.aantal mismatch",
    )
