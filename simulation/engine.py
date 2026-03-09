"""Simulation engine for year-by-year stock and flow calculations."""

from typing import Tuple
import csv
import os
from models.stock_manager import StockManager
from models.flow_manager import FlowManager
from simulation.helpers import (
    get_hinder_punten,
    get_hinder_punten_met_isolatie,
    get_hinder_punten_zonder_isolatie,
)
from config import PERSONEN_PER_WOONUNIT, OUTPUT_DIR


class SimulationEngine:
    """Engine for running year-by-year simulations."""

    def __init__(
        self,
        stock_manager: StockManager,
        flow_manager: FlowManager,
        zones: Tuple[str, ...],
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
        self._flow_log_rows = []

    def run_simulation(self, beginjaar: int, eindjaar: int) -> None:
        """
        Run the simulation from beginjaar to eindjaar.

        Args:
            beginjaar: Starting year
            eindjaar: Ending year (exclusive)
        """
        # Run year-by-year simulation
        jaren = range(beginjaar, eindjaar)
        for j in jaren:
            for zone in self.zones:
                self._simulate_year_zone(j, zone)

        self._calculate_derived_metrics(beginjaar, eindjaar)
        self._calculate_totals(beginjaar, eindjaar)

        # Schrijf flow-log naar CSV
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
            "outflow_stock_name",
            "orig_future_outflow_stock_value",
            "new_future_outflow_stock_value",
        ]
        with open(log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(self._flow_log_rows)

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

            current_inflow_stock_value = self.stock_manager.get_aantal(
                inflow_stock_name, jaar, zone
            )
            current_outflow_stock_value = self.stock_manager.get_aantal(
                outflow_stock_name, jaar, zone
            )
            future_inflow_stock_value = self.stock_manager.get_aantal(
                inflow_stock_name, jaar + 1, zone
            )
            future_outflow_stock_value = self.stock_manager.get_aantal(
                outflow_stock_name, jaar + 1, zone
            )

            inflow_relative, outflow_relative = row.get_flow()
            inflow_absolute = current_inflow_stock_value * inflow_relative
            outflow_absolute = current_inflow_stock_value * outflow_relative

            orig_future_inflow = future_inflow_stock_value
            orig_future_outflow = future_outflow_stock_value

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
                    "orig_future_inflow_stock_value": orig_future_inflow,
                    "new_future_inflow_stock_value": future_inflow_stock_value,
                    "outflow_stock_name": outflow_stock_name,
                    "orig_future_outflow_stock_value": orig_future_outflow,
                    "new_future_outflow_stock_value": future_outflow_stock_value,
                }
            )

            self.stock_manager.set_aantal(
                inflow_stock_name, jaar + 1, zone, future_inflow_stock_value
            )
            self.stock_manager.set_aantal(
                outflow_stock_name, jaar + 1, zone, future_outflow_stock_value
            )

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
                niet_geisoleerde_woningen = self.stock_manager.get_aantal(
                    "bewoonde_niet_geïsoleerde_woning", j, zone
                )
                geisoleerde_woningen = self.stock_manager.get_aantal(
                    "bewoonde_geïsoleerde_woning", j, zone
                )

                personen_zonder_isolatie = (
                    niet_geisoleerde_woningen * PERSONEN_PER_WOONUNIT
                )
                personen_met_isolatie = geisoleerde_woningen * PERSONEN_PER_WOONUNIT

                totaal_gehinderde_personen = (
                    personen_zonder_isolatie + personen_met_isolatie
                )

                hinderpunten = get_hinder_punten(
                    personen_zonder_isolatie, personen_met_isolatie, zone
                )
                hinderpunten_isolatie = get_hinder_punten_zonder_isolatie(
                    personen_zonder_isolatie, zone
                )
                hinderpunten_zonder_isolatie = get_hinder_punten_met_isolatie(
                    personen_met_isolatie, zone
                )

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
