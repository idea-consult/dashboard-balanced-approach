"""Simulation engine for year-by-year stock and flow calculations."""

from typing import Dict, List, Tuple
import csv
import os
import numpy as np
from models.stock_manager import StockManager
from models.measure_selection_manager import MeasureSelectionManager
from models.simulation_input_loader import load_simulation_inputs
from simulation.state import SimulationOutputs, SimulationState
from simulation.helpers import calculate_leefbaarheidspunten_for_contour
from config import (
    OUTPUT_DIR,
    ZONES_FILE,
    MEASURES_FILE,
    FLOW_RULES_FILE,
    MEASURE_COSTS_FILE,
)


class SimulationEngine:
    """Engine for running year-by-year simulations."""

    def __init__(
        self,
        stock_manager: StockManager,
        measure_selection_manager: MeasureSelectionManager,
        zones: Tuple[str, ...],
        zones_file: str = ZONES_FILE,
        measures_file: str = MEASURES_FILE,
        flow_rules_file: str = FLOW_RULES_FILE,
        measure_costs_file: str = MEASURE_COSTS_FILE,
    ):
        """
        Initialize the simulation engine.

        Args:
            stock_manager: StockManager instance
            measure_selection_manager: MeasureSelectionManager instance
            zones: Tuple of zone identifiers
        """
        self.stock_manager = stock_manager
        self.measure_selection_manager = measure_selection_manager
        self.zones = zones
        self.zones_file = zones_file
        self.measures_file = measures_file
        self.flow_rules_file = flow_rules_file
        self.measure_costs_file = measure_costs_file
        self._flow_log_rows = []
        self._totale_kost_overheid = 0.0
        self._totale_kost_prive = 0.0
        self._price_column_by_stock = {
            "onbebouwde_bebouwbare_percelen": "prijs_onbebouwde_bebouwbare_percelen",
            "onbebouwde_onbebouwbare_percelen": "prijs_onbebouwde_onbebouwbare_percelen",
            "bewoonde_niet_geïsoleerde_woning": "prijs_bewoonde_niet_geïsoleerde_woning",
            "bewoonde_geïsoleerde_woning": "prijs_bewoonde_geïsoleerde_woning",
        }

    def run_simulation(self, beginjaar: int, eindjaar: int) -> None:
        selected_zones = [
            (name, self.measure_selection_manager.get_selected_zones(str(name)))
            for name in self.measure_selection_manager.get_measure_descriptions().index
        ]
        state = self.load_inputs(beginjaar, eindjaar, selected_zones)
        state = self.run_simulation_state(state)
        outputs = self.build_outputs(state)
        self.persist_outputs(outputs)

    def load_inputs(
        self,
        beginjaar: int,
        eindjaar: int,
        selected_zones: List[tuple[str, Tuple[str, ...]]] | None = None,
    ) -> SimulationState:
        """Load validated inputs into a single SimulationState."""
        return load_simulation_inputs(
            stock_manager=self.stock_manager,
            beginjaar=beginjaar,
            eindjaar=eindjaar,
            zones=self.zones,
            flow_rules_file=self.flow_rules_file,
            measure_costs_file=self.measure_costs_file,
            selected_zones=selected_zones,
        )

    def run_simulation_state(self, state: SimulationState) -> SimulationState:
        """Mutate simulation state only (no file writes / UI side effects)."""
        for jaar in range(state.beginjaar, state.eindjaar):
            year_idx = state.year_to_idx[jaar]
            next_year_idx = state.year_to_idx[jaar + 1]
            for zone in state.zones:
                zone_idx = state.zone_to_idx[zone]
                state.sim_state[next_year_idx, zone_idx, :] = state.sim_state[
                    year_idx, zone_idx, :
                ]
                for rule in state.flow_rules_by_zone[zone]:
                    if (
                        rule.inflow_stock not in state.stock_to_idx
                        or rule.outflow_stock not in state.stock_to_idx
                    ):
                        continue
                    inflow_idx = state.stock_to_idx[rule.inflow_stock]
                    outflow_idx = state.stock_to_idx[rule.outflow_stock]
                    inflow_stock_value = state.sim_state[next_year_idx, zone_idx, inflow_idx]
                    outflow_stock_value = state.sim_state[next_year_idx, zone_idx, outflow_idx]
                    flow_rate = (
                        rule.flow_rate_active if rule.active else rule.flow_rate_baseline
                    )
                    flow_absolute = inflow_stock_value * flow_rate
                    if rule.flow_mode == "growth":
                        new_inflow = inflow_stock_value + flow_absolute
                        new_outflow = (
                            new_inflow if outflow_idx == inflow_idx else outflow_stock_value
                        )
                        outflow_absolute = flow_absolute
                    else:
                        new_inflow = inflow_stock_value - flow_absolute
                        if new_inflow < 0:
                            raise ValueError(
                                f"Future inflow stock value is negative for {rule.inflow_stock} in {zone} in {jaar}, using {rule.measure_id}."
                            )
                        new_outflow = outflow_stock_value + flow_absolute
                        outflow_absolute = flow_absolute
                    if rule.active:
                        row_cost = self._calculate_row_cost(zone, rule.cost_stock, outflow_absolute)
                        state.totale_kost_overheid += row_cost * rule.rel_cost_overheid
                        state.totale_kost_prive += row_cost * rule.rel_cost_prive
                    state.flow_log_rows.append(
                        {
                            "zone": zone,
                            "jaar": jaar,
                            "naam_flow": rule.measure_id,
                            "maatregel_toegepast": rule.active,
                            "flow_rate": flow_rate,
                            "flow_mode": rule.flow_mode,
                            "inflow_stock_name": rule.inflow_stock,
                            "orig_future_inflow_stock_value": inflow_stock_value,
                            "new_future_inflow_stock_value": new_inflow,
                            "delta_inflow": new_inflow - inflow_stock_value,
                            "outflow_stock_name": rule.outflow_stock,
                            "orig_future_outflow_stock_value": outflow_stock_value,
                            "new_future_outflow_stock_value": new_outflow,
                            "delta_outflow": new_outflow - outflow_stock_value,
                        }
                    )
                    state.sim_state[next_year_idx, zone_idx, inflow_idx] = new_inflow
                    if outflow_idx != inflow_idx:
                        state.sim_state[next_year_idx, zone_idx, outflow_idx] = new_outflow
        return state

    def build_outputs(self, state: SimulationState) -> SimulationOutputs:
        """Build output bundle from simulation state."""
        return SimulationOutputs(
            flow_log_rows=state.flow_log_rows,
            kost_overheid=state.totale_kost_overheid,
            kost_prive=state.totale_kost_prive,
            sim_state=state.sim_state,
            zones=state.zones,
            stock_names=state.stock_names,
            beginjaar=state.beginjaar,
            eindjaar=state.eindjaar,
        )

    def persist_outputs(self, outputs: SimulationOutputs) -> None:
        """Persist output bundle into stock manager and CSV files."""
        self._flush_sim_state_to_stock_manager(
            sim_state=outputs.sim_state,
            stock_names=list(outputs.stock_names),
            beginjaar=outputs.beginjaar,
            eindjaar=outputs.eindjaar,
        )
        self._flow_log_rows = list(outputs.flow_log_rows)
        self._totale_kost_overheid = outputs.kost_overheid
        self._totale_kost_prive = outputs.kost_prive

        self._calculate_derived_metrics(outputs.beginjaar, outputs.eindjaar)
        self._calculate_totals(outputs.beginjaar, outputs.eindjaar)

        log_path = os.path.join(OUTPUT_DIR, "flow_log.csv")
        fieldnames = [
            "zone",
            "jaar",
            "naam_flow",
            "maatregel_toegepast",
            "flow_rate",
            "flow_mode",
            "inflow_stock_name",
            "orig_future_inflow_stock_value",
            "new_future_inflow_stock_value",
            "delta_inflow",
            "outflow_stock_name",
            "orig_future_outflow_stock_value",
            "new_future_outflow_stock_value",
            "delta_outflow",
        ]
        with open(log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(self._flow_log_rows)

        self._write_flow_log_zone(log_path, fieldnames)

    def _flush_sim_state_to_stock_manager(
        self,
        sim_state: np.ndarray,
        stock_names: List[str],
        beginjaar: int,
        eindjaar: int,
    ) -> None:
        """Write simulated per-zone stock totals back into StockManager."""
        for year_offset, jaar in enumerate(range(beginjaar, eindjaar + 1)):
            for zone_idx, zone in enumerate(self.zones):
                for stock_idx, stock_name in enumerate(stock_names):
                    self.stock_manager.set_aantal(
                        stock_name,
                        jaar,
                        zone,
                        float(sim_state[year_offset, zone_idx, stock_idx]),
                    )

    def _load_zone_definitions(self) -> List[Tuple[str, float, float]]:
        """Load 5 dB zone definitions from input/zones.csv."""
        zone_definitions: List[Tuple[str, float, float]] = []
        with open(self.zones_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                zone_definitions.append(
                    (
                        str(row["zone"]),
                        float(row["min dBel"]),
                        float(row["max dBel"]),
                    )
                )
        return zone_definitions

    def _map_to_zone_bucket(
        self, zone_value: str, zone_definitions: List[Tuple[str, float, float]]
    ) -> str:
        """
        Map an input zone value to a 5 dB zone bucket.

        Supports both existing zone labels (e.g. A-F) and numeric dB values.
        """
        value = str(zone_value).strip()
        zone_labels = {zone for zone, _, _ in zone_definitions}
        if value in zone_labels:
            return value

        try:
            db_value = float(value)
        except ValueError:
            return "Onbekend"

        for zone, min_db, max_db in zone_definitions:
            if min_db <= db_value < max_db:
                return zone
        return "Onbekend"

    def _write_flow_log_zone(self, flow_log_path: str, fieldnames: List[str]) -> None:
        """Create a zone-aggregated flow log with 5 dB buckets."""
        zone_definitions = self._load_zone_definitions()
        aggregated: Dict[Tuple[str, ...], Dict[str, object]] = {}
        numeric_fields = {
            "orig_future_inflow_stock_value",
            "new_future_inflow_stock_value",
            "delta_inflow",
            "orig_future_outflow_stock_value",
            "new_future_outflow_stock_value",
            "delta_outflow",
        }

        with open(flow_log_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                zone_bucket = self._map_to_zone_bucket(row["zone"], zone_definitions)
                key = (
                    zone_bucket,
                    row["jaar"],
                    row["naam_flow"],
                    row["inflow_stock_name"],
                    row["outflow_stock_name"],
                )
                if key not in aggregated:
                    aggregated[key] = {
                        "zone": zone_bucket,
                        "jaar": row["jaar"],
                        "naam_flow": row["naam_flow"],
                        "maatregel_toegepast": row["maatregel_toegepast"],
                        "flow_rate": float(row["flow_rate"]),
                        "flow_mode": row["flow_mode"],
                        "inflow_stock_name": row["inflow_stock_name"],
                        "orig_future_inflow_stock_value": 0.0,
                        "new_future_inflow_stock_value": 0.0,
                        "delta_inflow": 0.0,
                        "outflow_stock_name": row["outflow_stock_name"],
                        "orig_future_outflow_stock_value": 0.0,
                        "new_future_outflow_stock_value": 0.0,
                        "delta_outflow": 0.0,
                    }

                agg_row = aggregated[key]
                agg_row["maatregel_toegepast"] = (
                    str(agg_row["maatregel_toegepast"]).lower() == "true"
                    or str(row["maatregel_toegepast"]).lower() == "true"
                )
                for numeric_field in numeric_fields:
                    agg_row[numeric_field] = float(agg_row[numeric_field]) + float(
                        row[numeric_field]
                    )

        output_path = os.path.join(OUTPUT_DIR, "flow_log_zone.csv")
        sorted_rows = sorted(
            aggregated.values(),
            key=lambda r: (str(r["zone"]), int(r["jaar"]), str(r["naam_flow"])),
        )
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(sorted_rows)

    def _calculate_row_cost(self, zone: str, kost_stock: str, outflow_absolute: float) -> float:
        if kost_stock == "-" or not kost_stock:
            return 0.0

        price_col = self._price_column_by_stock.get(kost_stock)
        if not price_col or price_col not in self.stock_manager.df_contour.columns:
            return 0.0

        zone_mask = self.stock_manager.df_contour["zone"] == zone
        woningen_col = (
            "aantal_woningen" if "aantal_woningen" in self.stock_manager.df_contour.columns else "huizen"
        )
        zone_df = self.stock_manager.df_contour.loc[zone_mask, [price_col, woningen_col]].dropna()
        if zone_df.empty:
            return 0.0

        woningen_sum = float(zone_df[woningen_col].sum())
        if woningen_sum <= 0:
            return 0.0

        weighted_price = float((zone_df[price_col] * zone_df[woningen_col]).sum() / woningen_sum)
        return float(outflow_absolute) * weighted_price

    def get_total_costs(self) -> Tuple[float, float]:
        """Return total costs for government and private parties."""
        return self._totale_kost_overheid, self._totale_kost_prive

    def get_timing_stats(self) -> Dict[str, float]:
        """Retained for compatibility; timing stats removed."""
        return {}

    def _calculate_derived_metrics(self, beginjaar: int, eindjaar: int) -> None:
        """
        Calculate derived metrics (persons, ernstig gehinderden) for a year and zone.
        The following metrics are calculated per zone:
        - gehinderde_personen_zonder_isolatie
        - gehinderde_personen_met_isolatie
        - totaal_gehinderde_personen
        - aantal_ernstig_gehinderden
        - aantal_ernstig_gehinderden_met_isolatie
        - aantal_ernstig_gehinderden_zonder_isolatie
        """
        for j in range(beginjaar, eindjaar + 1):
            for zone in self.zones:
                contour_df = self.stock_manager.get_zone_contour_frame(zone, j)
                if contour_df.empty:
                    personen_zonder_isolatie = 0.0
                    personen_met_isolatie = 0.0
                    ernstig_zonder_isolatie = 0.0
                    ernstig_met_isolatie = 0.0
                else:
                    inwoners_per_huis = contour_df["gemiddeld_aantal_inwoners_per_huis"]
                    dosis_effect_relatie = contour_df["dosis_effect_relatie"]

                    personen_zonder_isolatie = float(
                        (
                            contour_df["bewoonde_niet_geïsoleerde_woning"] * inwoners_per_huis
                        ).sum()
                    )
                    personen_met_isolatie = float(
                        (
                            contour_df["bewoonde_geïsoleerde_woning"] * inwoners_per_huis
                        ).sum()
                    )

                    ernstig_zonder_isolatie = float(
                        (
                            contour_df["bewoonde_niet_geïsoleerde_woning"]
                            * inwoners_per_huis
                            * dosis_effect_relatie
                        ).sum()
                    )
                    ernstig_met_isolatie = float(
                        (
                            contour_df["bewoonde_geïsoleerde_woning"]
                            * inwoners_per_huis
                            * dosis_effect_relatie
                        ).sum()
                    )

                totaal_gehinderde_personen = personen_zonder_isolatie + personen_met_isolatie
                aantal_ernstig_gehinderden = ernstig_zonder_isolatie + ernstig_met_isolatie

                self.stock_manager.set_aantal(
                    "gehinderde_personen_zonder_isolatie",
                    j,
                    zone,
                    personen_zonder_isolatie,
                )
                self.stock_manager.set_aantal(
                    "gehinderde_personen_met_isolatie", j, zone, personen_met_isolatie
                )
                self.stock_manager.set_aantal(
                    "totaal_gehinderde_personen", j, zone, totaal_gehinderde_personen
                )
                self.stock_manager.set_aantal(
                    "aantal_ernstig_gehinderden", j, zone, aantal_ernstig_gehinderden
                )
                self.stock_manager.set_aantal(
                    "aantal_ernstig_gehinderden_met_isolatie",
                    j,
                    zone,
                    ernstig_met_isolatie,
                )
                self.stock_manager.set_aantal(
                    "aantal_ernstig_gehinderden_zonder_isolatie",
                    j,
                    zone,
                    ernstig_zonder_isolatie,
                )

    def calculate_leefbaarheidspunten(
        self,
        beginjaar: int,
        eindjaar: int,
        weights_by_zone: Dict[str, Dict[str, float]],
    ) -> None:
        """Bereken leefbaarheidspunten per zone/jaar op basis van instelbare punten per inwoner."""
        default_weights = {"niet_geïsoleerd": 0.0, "geïsoleerd": 0.0}
        for jaar in range(beginjaar, eindjaar + 1):
            for zone in self.zones:
                zone_weights = weights_by_zone.get(zone, default_weights)
                contour_df = self.stock_manager.get_zone_contour_frame(zone, jaar)
                leefbaarheidspunten_zonder, leefbaarheidspunten_met, leefbaarheidspunten_totaal = (
                    calculate_leefbaarheidspunten_for_contour(
                        contour_df,
                        float(zone_weights.get("niet_geïsoleerd", 0.0)),
                        float(zone_weights.get("geïsoleerd", 0.0)),
                    )
                )
                self.stock_manager.set_aantal(
                    "leefbaarheidspunten_zonder_isolatie",
                    jaar,
                    zone,
                    leefbaarheidspunten_zonder,
                )
                self.stock_manager.set_aantal(
                    "leefbaarheidspunten_met_isolatie", jaar, zone, leefbaarheidspunten_met
                )
                self.stock_manager.set_aantal(
                    "leefbaarheidspunten", jaar, zone, leefbaarheidspunten_totaal
                )

        self._update_metric_totals(
            beginjaar,
            eindjaar,
            [
                "leefbaarheidspunten",
                "leefbaarheidspunten_met_isolatie",
                "leefbaarheidspunten_zonder_isolatie",
            ],
        )

    def _update_metric_totals(
        self, beginjaar: int, eindjaar: int, metrics: List[str]
    ) -> None:
        for jaar in range(beginjaar, eindjaar + 1):
            for metric in metrics:
                try:
                    total = sum(
                        self.stock_manager.get_aantal(metric, jaar, zone)
                        for zone in self.zones
                    )
                except KeyError:
                    total = 0.0
                self.stock_manager.set_aantal(metric, jaar, "Totaal", total)

    def _calculate_totals(self, beginjaar: int, eindjaar: int) -> None:
        metrics = [
            "gehinderde_personen_met_isolatie",
            "gehinderde_personen_zonder_isolatie",
            "aantal_ernstig_gehinderden",
            "aantal_ernstig_gehinderden_met_isolatie",
            "aantal_ernstig_gehinderden_zonder_isolatie",
            "leefbaarheidspunten",
            "leefbaarheidspunten_met_isolatie",
            "leefbaarheidspunten_zonder_isolatie",
            "totaal_gehinderde_personen",
            "bewoonde_geïsoleerde_woning",
            "bewoonde_niet_geïsoleerde_woning",
            "niet_bewoonde_geïsoleerde_woning",
            "niet_bewoonde_niet_geïsoleerde_woning",
            "nieuwe_woning",
            "onbebouwde_bebouwbare_percelen",
            "onbebouwde_onbebouwbare_percelen",
            "perceel_eigendom_overheid",
            "woning_eigendom_overheid",
        ]

        for j in range(beginjaar, eindjaar + 1):
            for metric in metrics:
                try:
                    total = sum(
                        self.stock_manager.get_aantal(metric, j, z) for z in self.zones
                    )
                except KeyError:
                    total = 0

                self.stock_manager.set_aantal(metric, j, "Totaal", total)
