"""Build validated simulation inputs/state from CSV files."""

from typing import Dict, Iterable, Tuple
import pandas as pd
import numpy as np

from models.stock_manager import StockManager
from simulation.state import FlowRule, SimulationState


def _selected_map_from_iterable(
    selected_zones: Iterable[tuple[str, Tuple[str, ...]]] | None,
) -> Dict[str, set[str]]:
    if selected_zones is None:
        return {}
    return {name: set(zones) for name, zones in selected_zones}


def resolve_regional_flow_targets(
    stock_name: str, stock_to_idx: Dict[str, int]
) -> list[str]:
    """
    Map een flow-regel stock (basisnaam) naar regionale sim-stocks.

    flow_rules.csv blijft ongewijzigd; elke regel wordt op vlaanderen én brussel toegepast.
    """
    regional = [f"{stock_name}_{regio}" for regio in StockManager.REGIONS]
    if all(name in stock_to_idx for name in regional):
        return regional
    if stock_name in stock_to_idx:
        return [stock_name]
    return []


def _load_rule_templates(
    flow_rules_file: str, measure_costs_file: str
) -> pd.DataFrame:
    flow_rules_df = pd.read_csv(flow_rules_file)
    costs_df = pd.read_csv(measure_costs_file)

    required_rules = {
        "rule_id",
        "measure_id",
        "inflow_stock",
        "outflow_stock",
        "flow_rate_baseline",
        "flow_rate_active",
        "flow_mode",
    }
    missing_rules = sorted(required_rules - set(flow_rules_df.columns))
    if missing_rules:
        raise ValueError(f"flow_rules.csv mist kolommen: {', '.join(missing_rules)}")

    required_costs = {"measure_id", "rel_cost_overheid", "rel_cost_prive", "kost_stock"}
    missing_costs = sorted(required_costs - set(costs_df.columns))
    if missing_costs:
        raise ValueError(f"measure_costs.csv mist kolommen: {', '.join(missing_costs)}")

    merged = flow_rules_df.merge(costs_df, on="measure_id", how="left")
    merged["priority"] = (
        pd.to_numeric(merged.get("priority", 100), errors="coerce")
        .fillna(100)
        .astype(int)
    )
    for col in ("rel_cost_overheid", "rel_cost_prive"):
        merged[col] = pd.to_numeric(merged[col], errors="raise")
    merged["flow_mode"] = merged["flow_mode"].astype(str).str.strip().str.lower()
    valid_flow_modes = {"transfer", "growth"}
    unknown_modes = sorted(set(merged["flow_mode"]) - valid_flow_modes)
    if unknown_modes:
        raise ValueError(
            "flow_rules.csv bevat ongeldige flow_mode waarden: " + ", ".join(unknown_modes)
        )
    return merged.sort_values("priority")


def _flow_rule_from_row(
    row: pd.Series,
    *,
    zone: str,
    db_ondergrens: int | None,
    flow_rate_baseline: float,
    flow_rate_active: float,
    active: bool,
) -> FlowRule:
    return FlowRule(
        rule_id=str(row["rule_id"]),
        measure_id=str(row["measure_id"]),
        zone=zone,
        inflow_stock=str(row["inflow_stock"]),
        outflow_stock=str(row["outflow_stock"]),
        flow_rate_baseline=float(flow_rate_baseline),
        flow_rate_active=float(flow_rate_active),
        flow_mode=str(row["flow_mode"]),
        active=active,
        cost_stock=str(row.get("kost_stock", "")).strip(),
        rel_cost_overheid=float(row["rel_cost_overheid"]),
        rel_cost_prive=float(row["rel_cost_prive"]),
        priority=int(row["priority"]),
        db_ondergrens=db_ondergrens,
    )


def _load_band_rules(
    *,
    stock_manager: StockManager,
    merged: pd.DataFrame,
    selected_map: Dict[str, set[str]],
) -> Dict[int, list[FlowRule]]:
    by_band: Dict[int, list[FlowRule]] = {}
    for db in stock_manager.get_bands():
        zone = stock_manager.band_to_zone[db]
        band_rates = stock_manager.get_flow_rates_for_band(db)
        rules: list[FlowRule] = []
        for _, row in merged.iterrows():
            measure_id = str(row["measure_id"])
            active = zone in selected_map.get(measure_id, set())
            baseline, active_rate = band_rates.get(
                measure_id,
                (float(row["flow_rate_baseline"]), float(row["flow_rate_active"])),
            )
            rules.append(
                _flow_rule_from_row(
                    row,
                    zone=zone,
                    db_ondergrens=db,
                    flow_rate_baseline=baseline,
                    flow_rate_active=active_rate,
                    active=active,
                )
            )
        by_band[db] = rules
    return by_band


def _load_zone_rules(
    *,
    zones: Tuple[str, ...],
    merged: pd.DataFrame,
    selected_map: Dict[str, set[str]],
) -> Dict[str, list[FlowRule]]:
    by_zone: Dict[str, list[FlowRule]] = {zone: [] for zone in zones}
    for zone in zones:
        for _, row in merged.iterrows():
            measure_id = str(row["measure_id"])
            active = zone in selected_map.get(measure_id, set())
            by_zone[zone].append(
                _flow_rule_from_row(
                    row,
                    zone=zone,
                    db_ondergrens=None,
                    flow_rate_baseline=float(row["flow_rate_baseline"]),
                    flow_rate_active=float(row["flow_rate_active"]),
                    active=active,
                )
            )
    return by_zone


def load_simulation_inputs(
    *,
    stock_manager: StockManager,
    beginjaar: int,
    eindjaar: int,
    zones: Tuple[str, ...],
    flow_rules_file: str,
    measure_costs_file: str,
    selected_zones: Iterable[tuple[str, Tuple[str, ...]]] | None = None,
) -> SimulationState:
    """Load and validate all simulation inputs into a SimulationState."""
    selected_map = _selected_map_from_iterable(selected_zones)
    merged = _load_rule_templates(flow_rules_file, measure_costs_file)

    stock_names = stock_manager.get_simulation_stock_names()
    stock_to_idx = {stock: idx for idx, stock in enumerate(stock_names)}
    year_to_idx = {year: idx for idx, year in enumerate(range(beginjaar, eindjaar + 1))}

    if stock_manager._lden_band_mode:
        bands = stock_manager.get_bands()
        band_to_idx = {band: idx for idx, band in enumerate(bands)}
        sim_state = np.zeros((len(year_to_idx), len(bands), len(stock_names)), dtype=float)
        for stock_idx, stock_name in enumerate(stock_names):
            for band_idx, band in enumerate(bands):
                sim_state[0, band_idx, stock_idx] = stock_manager.get_aantal_for_band(
                    stock_name, beginjaar, band
                )
        flow_rules_by_band = _load_band_rules(
            stock_manager=stock_manager,
            merged=merged,
            selected_map=selected_map,
        )
        return SimulationState(
            beginjaar=beginjaar,
            eindjaar=eindjaar,
            zones=zones,
            stock_names=stock_names,
            sim_state=sim_state,
            stock_to_idx=stock_to_idx,
            year_to_idx=year_to_idx,
            bands=bands,
            band_to_idx=band_to_idx,
            band_to_zone=dict(stock_manager.band_to_zone),
            flow_rules_by_band=flow_rules_by_band,
        )

    zone_to_idx = {zone: idx for idx, zone in enumerate(zones)}
    sim_state = np.zeros((len(year_to_idx), len(zones), len(stock_names)), dtype=float)
    for stock_idx, stock_name in enumerate(stock_names):
        for zone_idx, zone in enumerate(zones):
            sim_state[0, zone_idx, stock_idx] = stock_manager.get_aantal(
                stock_name, beginjaar, zone
            )
    flow_rules_by_zone = _load_zone_rules(
        zones=zones,
        merged=merged,
        selected_map=selected_map,
    )
    return SimulationState(
        beginjaar=beginjaar,
        eindjaar=eindjaar,
        zones=zones,
        stock_names=stock_names,
        sim_state=sim_state,
        zone_to_idx=zone_to_idx,
        stock_to_idx=stock_to_idx,
        year_to_idx=year_to_idx,
        flow_rules_by_band={},
        flow_rules_by_zone=flow_rules_by_zone,
    )
