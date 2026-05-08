"""Simulation engine for year-by-year stock and flow calculations."""

from typing import Dict, List, Tuple
import csv
import os
from time import perf_counter
import numpy as np
from models.stock_manager import StockManager
from models.flow_manager import FlowManager
from config import OUTPUT_DIR, ZONES_FILE


class SimulationEngine:
    """Engine for running year-by-year simulations."""

    def __init__(
        self,
        stock_manager: StockManager,
        flow_manager: FlowManager,
        zones: Tuple[str, ...],
        zones_file: str = ZONES_FILE,
    ):
        """
        Initialize the simulation engine.

        Args:
            stock_manager: StockManager instance
            flow_manager: FlowManager instance
            zones: Tuple of zone identifiers
        """
        self.stock_manager = stock_manager
        self.flow_manager = flow_manager
        self.zones = zones
        self.zones_file = zones_file
        self._flow_log_rows = []
        self._totale_kost_overheid = 0.0
        self._totale_kost_prive = 0.0
        self._timings: Dict[str, float] = {}
        self._price_column_by_stock = {
            "onbebouwde_bebouwbare_percelen": "prijs_onbebouwde_bebouwbare_percelen",
            "onbebouwde_onbebouwbare_percelen": "prijs_onbebouwde_onbebouwbare_percelen",
            "bewoonde_niet_geïsoleerde_woning": "prijs_bewoonde_niet_geïsoleerde_woning",
            "bewoonde_geïsoleerde_woning": "prijs_bewoonde_geïsoleerde_woning",
        }

    def run_simulation(self, beginjaar: int, eindjaar: int) -> None:
        """
        Run the simulation from beginjaar to eindjaar.

        Args:
            beginjaar: Starting year
            eindjaar: Ending year (exclusive)
        """
        total_start = perf_counter()
        self._timings = {}
        self._flow_log_rows = []
        self._totale_kost_overheid = 0.0
        self._totale_kost_prive = 0.0

        stock_names = [
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
        stock_to_idx = {stock: idx for idx, stock in enumerate(stock_names)}
        zone_to_idx = {zone: idx for idx, zone in enumerate(self.zones)}
        n_years = (eindjaar - beginjaar) + 1
        sim_state = np.zeros((n_years, len(self.zones), len(stock_names)), dtype=float)

        init_state_start = perf_counter()
        for stock_idx, stock_name in enumerate(stock_names):
            for zone_idx, zone in enumerate(self.zones):
                sim_state[0, zone_idx, stock_idx] = self.stock_manager.get_aantal(
                    stock_name, beginjaar, zone
                )
        self._timings["simulation.init_state"] = perf_counter() - init_state_start

        precompute_flows_start = perf_counter()
        zone_flows = self._build_zone_flow_records(stock_to_idx)
        self._timings["simulation.precompute_flows"] = (
            perf_counter() - precompute_flows_start
        )

        # Run year-by-year simulation using NumPy state.
        sim_loop_start = perf_counter()
        for year_offset, jaar in enumerate(range(beginjaar, eindjaar)):
            next_year_offset = year_offset + 1
            for zone in self.zones:
                zone_idx = zone_to_idx[zone]
                sim_state[next_year_offset, zone_idx, :] = sim_state[
                    year_offset, zone_idx, :
                ]
                for flow in zone_flows[zone]:
                    inflow_stock_value = sim_state[
                        next_year_offset, zone_idx, flow["inflow_idx"]
                    ]
                    outflow_stock_value = sim_state[
                        next_year_offset, zone_idx, flow["outflow_idx"]
                    ]

                    inflow_relative = flow["inflow_relative"]
                    outflow_relative = flow["outflow_relative"]
                    inflow_absolute = inflow_stock_value * inflow_relative
                    outflow_absolute = inflow_stock_value * outflow_relative

                    if flow["applied"]:
                        row_cost = self._calculate_row_cost(
                            zone, flow["kost_stock"], outflow_absolute
                        )
                        self._totale_kost_overheid += (
                            row_cost * flow["rel_cost_overheid"]
                        )
                        self._totale_kost_prive += row_cost * flow["rel_cost_prive"]

                    new_inflow_stock_value = inflow_stock_value - inflow_absolute
                    if new_inflow_stock_value < 0:
                        raise ValueError(
                            f"Future inflow stock value is negative for {flow['inflow_stock_name']} in {zone} in {jaar}, using {flow['name']}."
                        )
                    new_outflow_stock_value = outflow_stock_value + outflow_absolute

                    self._flow_log_rows.append(
                        {
                            "zone": zone,
                            "jaar": jaar,
                            "naam_flow": flow["name"],
                            "maatregel_toegepast": flow["applied"],
                            "inflow_relative": inflow_relative,
                            "outflow_relative": outflow_relative,
                            "inflow_stock_name": flow["inflow_stock_name"],
                            "orig_future_inflow_stock_value": inflow_stock_value,
                            "new_future_inflow_stock_value": new_inflow_stock_value,
                            "delta_inflow": new_inflow_stock_value - inflow_stock_value,
                            "outflow_stock_name": flow["outflow_stock_name"],
                            "orig_future_outflow_stock_value": outflow_stock_value,
                            "new_future_outflow_stock_value": new_outflow_stock_value,
                            "delta_outflow": new_outflow_stock_value
                            - outflow_stock_value,
                        }
                    )

                    sim_state[next_year_offset, zone_idx, flow["inflow_idx"]] = (
                        new_inflow_stock_value
                    )
                    sim_state[next_year_offset, zone_idx, flow["outflow_idx"]] = (
                        new_outflow_stock_value
                    )
        self._timings["simulation.loop"] = perf_counter() - sim_loop_start

        flush_start = perf_counter()
        self._flush_sim_state_to_stock_manager(
            sim_state=sim_state,
            stock_names=stock_names,
            beginjaar=beginjaar,
            eindjaar=eindjaar,
        )
        self._timings["simulation.flush_state"] = perf_counter() - flush_start

        derived_start = perf_counter()
        self._calculate_derived_metrics(beginjaar, eindjaar)
        self._timings["simulation.derived_metrics"] = perf_counter() - derived_start

        totals_start = perf_counter()
        self._calculate_totals(beginjaar, eindjaar)
        self._timings["simulation.totals"] = perf_counter() - totals_start

        # Schrijf flow-log naar CSV
        write_flow_log_start = perf_counter()
        log_path = os.path.join(OUTPUT_DIR, "flow_log.csv")
        fieldnames = [
            "zone",
            "jaar", 
            "naam_flow",
            "maatregel_toegepast",
            "inflow_relative",
            "outflow_relative",
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
        self._timings["simulation.write_flow_log"] = perf_counter() - write_flow_log_start

        write_zone_log_start = perf_counter()
        self._write_flow_log_zone(log_path, fieldnames)
        self._timings["simulation.write_flow_log_zone"] = (
            perf_counter() - write_zone_log_start
        )
        self._timings["simulation.total"] = perf_counter() - total_start

    def _build_zone_flow_records(
        self, stock_to_idx: Dict[str, int]
    ) -> Dict[str, List[Dict[str, object]]]:
        """Precompute flow records per zone for faster core-loop execution."""
        records: Dict[str, List[Dict[str, object]]] = {zone: [] for zone in self.zones}
        for zone in self.zones:
            for row in self.flow_manager.get_flows(zone):
                inflow_stock_name = row.get_inflow_stock_name()
                outflow_stock_name = row.get_outflow_stock_name()
                if (
                    inflow_stock_name not in stock_to_idx
                    or outflow_stock_name not in stock_to_idx
                ):
                    continue
                inflow_relative, outflow_relative = row.get_flow()
                records[zone].append(
                    {
                        "name": row.get_name_measure(),
                        "applied": row.is_applied(),
                        "inflow_stock_name": inflow_stock_name,
                        "outflow_stock_name": outflow_stock_name,
                        "inflow_idx": stock_to_idx[inflow_stock_name],
                        "outflow_idx": stock_to_idx[outflow_stock_name],
                        "inflow_relative": inflow_relative,
                        "outflow_relative": outflow_relative,
                        "rel_cost_overheid": row.get_relative_cost_overheid(),
                        "rel_cost_prive": row.get_relative_cost_prive(),
                        "kost_stock": row.get_kost_stock(),
                    }
                )
        return records

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
                        "inflow_relative": float(row["inflow_relative"]),
                        "outflow_relative": float(row["outflow_relative"]),
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

    def _simulate_year_zone(self, jaar: int, zone: str) -> None:
        """Simulate one year for one zone."""
        stocks = [
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
        for stock in stocks:
            current_stock_value = self.stock_manager.get_aantal(stock, jaar, zone)
            future_stock_value = current_stock_value
            self.stock_manager.set_aantal(stock, jaar + 1, zone, future_stock_value)

        for row in self.flow_manager.get_flows(zone):
            name_measure = row.get_name_measure()
            inflow_stock_name = row.get_inflow_stock_name()
            outflow_stock_name = row.get_outflow_stock_name()

            future_inflow_stock_value = self.stock_manager.get_aantal(
                inflow_stock_name, jaar + 1, zone
            )
            future_outflow_stock_value = self.stock_manager.get_aantal(
                outflow_stock_name, jaar + 1, zone
            )

            inflow_relative, outflow_relative = row.get_flow()
            # Gebruik de future-waarde als basis zodat eerdere flows binnen hetzelfde jaar
            # (bv. opbouw van nieuwe_woning) effectief kunnen worden afgebouwd later in dat jaar.
            inflow_absolute = future_inflow_stock_value * inflow_relative
            outflow_absolute = future_inflow_stock_value * outflow_relative

            if row.is_applied():
                row_cost = self._calculate_row_cost(zone, row.get_kost_stock(), outflow_absolute)
                self._totale_kost_overheid += row_cost * row.get_relative_cost_overheid()
                self._totale_kost_prive += row_cost * row.get_relative_cost_prive()

            orig_inflow_before_flow = future_inflow_stock_value
            orig_outflow_before_flow = future_outflow_stock_value

            future_inflow_stock_value = future_inflow_stock_value - inflow_absolute
            if future_inflow_stock_value < 0:
                raise ValueError(
                    f"Future inflow stock value is negative for {inflow_stock_name} in {zone} in {jaar}, using {name_measure}."
                )
            future_outflow_stock_value = future_outflow_stock_value + outflow_absolute

            # Log regel toevoegen
            self._flow_log_rows.append(
                {
                    "zone": zone,
                    "jaar": jaar,
                    "naam_flow": name_measure,
                    "maatregel_toegepast": row.is_applied(),
                    "inflow_relative": inflow_relative,
                    "outflow_relative": outflow_relative,
                    "inflow_stock_name": inflow_stock_name,
                    "orig_future_inflow_stock_value": orig_inflow_before_flow,
                    "new_future_inflow_stock_value": future_inflow_stock_value,
                    "delta_inflow": future_inflow_stock_value - orig_inflow_before_flow,
                    "outflow_stock_name": outflow_stock_name,
                    "orig_future_outflow_stock_value": orig_outflow_before_flow,
                    "new_future_outflow_stock_value": future_outflow_stock_value,
                    "delta_outflow": future_outflow_stock_value - orig_outflow_before_flow,
                }
            )

            self.stock_manager.set_aantal(
                inflow_stock_name, jaar + 1, zone, future_inflow_stock_value
            )
            self.stock_manager.set_aantal(
                outflow_stock_name, jaar + 1, zone, future_outflow_stock_value
            )

    def _calculate_row_cost(self, zone: str, kost_stock: str, outflow_absolute: float) -> float:
        if kost_stock == "-" or not kost_stock:
            return 0.0

        price_col = self._price_column_by_stock.get(kost_stock)
        if not price_col or price_col not in self.stock_manager.df_contour.columns:
            return 0.0

        zone_mask = self.stock_manager.df_contour["zone"] == zone
        zone_df = self.stock_manager.df_contour.loc[zone_mask, [price_col, "huizen"]].dropna()
        if zone_df.empty:
            return 0.0

        huizen_sum = float(zone_df["huizen"].sum())
        if huizen_sum <= 0:
            return 0.0

        weighted_price = float((zone_df[price_col] * zone_df["huizen"]).sum() / huizen_sum)
        return float(outflow_absolute) * weighted_price

    def get_total_costs(self) -> Tuple[float, float]:
        """Return total costs for government and private parties."""
        return self._totale_kost_overheid, self._totale_kost_prive

    def get_timing_stats(self) -> Dict[str, float]:
        """Return simulation timing stats in seconds."""
        return dict(self._timings)

    def _calculate_derived_metrics(self, beginjaar: int, eindjaar: int) -> None:
        """
        Calculate derived metrics (persons, hinder points) for a year and zone.
        The following metrics are calculated per zone:
        - gehinderde_personen_zonder_isolatie
        - gehinderde_personen_met_isolatie
        - totaal_gehinderde_personen
        - hinderpunten
        - hinderpunten_isolatie
        - hinderpunten_zonder_isolatie
        """
        for j in range(beginjaar, eindjaar + 1):
            for zone in self.zones:
                contour_df = self.stock_manager.get_zone_contour_frame(zone, j)
                if contour_df.empty:
                    personen_zonder_isolatie = 0.0
                    personen_met_isolatie = 0.0
                    hinderpunten_zonder_isolatie = 0.0
                    hinderpunten_isolatie = 0.0
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

                    hinderpunten_zonder_isolatie = float(
                        (
                            contour_df["bewoonde_niet_geïsoleerde_woning"]
                            * inwoners_per_huis
                            * dosis_effect_relatie
                        ).sum()
                    )
                    hinderpunten_isolatie = float(
                        (
                            contour_df["bewoonde_geïsoleerde_woning"]
                            * inwoners_per_huis
                            * dosis_effect_relatie
                        ).sum()
                    )

                totaal_gehinderde_personen = personen_zonder_isolatie + personen_met_isolatie
                hinderpunten = hinderpunten_zonder_isolatie + hinderpunten_isolatie

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
                self.stock_manager.set_aantal("hinderpunten", j, zone, hinderpunten)
                self.stock_manager.set_aantal(
                    "hinderpunten_isolatie", j, zone, hinderpunten_isolatie
                )
                self.stock_manager.set_aantal(
                    "hinderpunten_zonder_isolatie",
                    j,
                    zone,
                    hinderpunten_zonder_isolatie,
                )

    def _calculate_totals(self, beginjaar: int, eindjaar: int) -> None:
        metrics = [
            "gehinderde_personen_met_isolatie",
            "gehinderde_personen_zonder_isolatie",
            "hinderpunten",
            "hinderpunten_isolatie",
            "hinderpunten_zonder_isolatie",
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
