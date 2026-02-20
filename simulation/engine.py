"""Simulation engine for year-by-year stock and flow calculations."""

from typing import Tuple
from models.stock_manager import StockManager
from models.flow_manager import FlowManager
from simulation.calculators import calculate_initial_metrics, calculate_totals
from util.helpers import (
    get_hinder_punten,
    get_hinder_punten_met_isolatie,
    get_hinder_punten_zonder_isolatie,
)
from config import PERSONEN_PER_WOONUNIT


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
    
    def run_simulation(self, beginjaar: int, eindjaar: int) -> None:
        """
        Run the simulation from beginjaar to eindjaar.
        
        Args:
            beginjaar: Starting year
            eindjaar: Ending year (exclusive)
        """
        # Calculate initial metrics
        calculate_initial_metrics(self.stock_manager, self.zones, beginjaar)
        
        # Run year-by-year simulation
        jaren = range(beginjaar, eindjaar)
        for j in jaren:
            for z in self.zones:
                self._simulate_year_zone(j, z)
        
        # Calculate totals across zones
        calculate_totals(self.stock_manager, self.zones, beginjaar, eindjaar)
    
    def _simulate_year_zone(self, jaar: int, zone: str) -> None:
        """Simulate one year for one zone."""
        if self.flow_manager.is_measure_applied("landingsbaan_verschuiven", zone):
            return
        
        # Calculate new houses from parcels (needed for both parcel and house simulation)
        huidige_percelen = self.stock_manager.get_aantal(
            "onbebouwde_bebouwbare_percelen", jaar, zone
        )
        nieuwe_woningen = self._calculate_new_houses_from_parcels(huidige_percelen, zone)
        
        # Simulate parcels and houses
        self._simulate_parcels(jaar, zone, nieuwe_woningen)
        self._simulate_houses(jaar, zone, nieuwe_woningen)
        
        # Calculate derived metrics
        self._calculate_derived_metrics(jaar + 1, zone)
    
    def _flow(self, flow_name: str, zone: str, base_value: float) -> float:
        """Helper: Calculate flow value * base value."""
        return base_value * self.flow_manager.get_flow(flow_name, zone)
    
    def _calculate_new_houses_from_parcels(self, percelen: float, zone: str) -> dict:
        """Calculate new houses from parcel flows."""
        return {
            "klein": self._flow("verbod_kleine_woning", zone, percelen),
            "groot": self._flow("verbod_grote_woning", zone, percelen),
            "kwetsbaar": self._flow("verbod_kwetsbare_groep", zone, percelen),
        }
    
    def _simulate_parcels(self, jaar: int, zone: str, nieuwe_woningen: dict) -> None:
        """Simulate parcel stock changes."""
        huidige_onbebouwde_bebouwbare_percelen = self.stock_manager.get_aantal("onbebouwde_bebouwbare_percelen", jaar, zone)
        
        # Calculate flows
        toevoegingen = (
            self._flow("verkavelingsverbod", zone, huidige_onbebouwde_bebouwbare_percelen) +
            self._flow("woongebiedverbod", zone, huidige_onbebouwde_bebouwbare_percelen)
        )
        verwijderingen = (
            self._flow("aankoopbeleid_percelen", zone, huidige_onbebouwde_bebouwbare_percelen) +
            self._flow("voorkooprecht_percelen", zone, huidige_onbebouwde_bebouwbare_percelen) +
            self._flow("onteigening_percelen", zone, huidige_onbebouwde_bebouwbare_percelen) +
            sum(nieuwe_woningen.values())
        )
        overheid_percelen = (
            self._flow("aankoopbeleid_percelen", zone, huidige_onbebouwde_bebouwbare_percelen) +
            self._flow("voorkooprecht_percelen", zone, huidige_onbebouwde_bebouwbare_percelen) +
            self._flow("onteigening_percelen", zone, huidige_onbebouwde_bebouwbare_percelen)
        )
        
        # Update stocks
        toekomstige = huidige_onbebouwde_bebouwbare_percelen + toevoegingen - verwijderingen
        self.stock_manager.set_aantal("onbebouwde_bebouwbare_percelen", jaar + 1, zone, toekomstige)
        self.stock_manager.set_aantal("onbebouwde_onbebouwbare_percelen", jaar + 1, zone, overheid_percelen)
    
    def _simulate_houses(self, jaar: int, zone: str, nieuwe_woningen: dict) -> None:
        """Simulate house stock changes."""
        bijkomende_woningen = sum(nieuwe_woningen.values())
        huidige_niet_geisoleerd = self.stock_manager.get_aantal("niet_geisoleerde_woningen", jaar, zone)
        huidige_geisoleerd = self.stock_manager.get_aantal("geisoleerde_woningen", jaar, zone)
        
        # Bijkomende woningen vermijden
        opsplitsing_niet = self._flow("woonverdichtingsverbod_woningen", zone, huidige_niet_geisoleerd)
        opsplitsing_geisoleerd = self._flow("woonverdichtingsverbod_woningen", zone, huidige_geisoleerd)
        onteigingen_niet = self._flow("onteigening_woningen", zone, huidige_niet_geisoleerd)
        onteigingen_geisoleerd = self._flow("onteigening_woningen", zone, huidige_geisoleerd)

        overheid_niet = (
            self._flow("aankoopbeleid_woningen", zone, huidige_niet_geisoleerd) +
            self._flow("voorkooprecht_woningen", zone, huidige_niet_geisoleerd)
        )
        overheid_geisoleerd = (
            self._flow("aankoopbeleid_woningen", zone, huidige_geisoleerd) +
            self._flow("voorkooprecht_woningen", zone, huidige_geisoleerd)
        )
        
        # Huidige woningen isoleren
        isolatie = (
            self._flow("verplicht_isoleren_renovatie", zone, huidige_niet_geisoleerd) +
            self._flow("gesubsidieerd_isolatieprogramma", zone, huidige_niet_geisoleerd) +
            self._flow("gestuurd_isolatieprogramma", zone, huidige_niet_geisoleerd) +
            self._flow("aanleg_geluidsbuffers", zone, huidige_niet_geisoleerd)
        )
        
        # Calculate new houses with/without insulation
        isolatie_ratio = self.flow_manager.get_flow("isolatievoorschriften_nieuwbouw", zone)
        nieuwe_geisoleerd = bijkomende_woningen * isolatie_ratio
        nieuwe_niet_geisoleerd = bijkomende_woningen - nieuwe_geisoleerd
        
        # Calculate future stocks
        toekomstige_niet = (
            huidige_niet_geisoleerd 
            + nieuwe_niet_geisoleerd 
            + opsplitsing_niet
            - isolatie 
            - overheid_niet 
            - onteigingen_niet
        )
        toekomstige_geisoleerd = (
            huidige_geisoleerd 
            + nieuwe_geisoleerd 
            + opsplitsing_geisoleerd
            + isolatie 
            - overheid_geisoleerd 
            - onteigingen_geisoleerd
        )
        leegstaand = overheid_niet + overheid_geisoleerd + onteigingen_niet + onteigingen_geisoleerd
        
        # Update stocks
        self.stock_manager.set_aantal("niet_geisoleerde_woningen", jaar + 1, zone, toekomstige_niet)
        self.stock_manager.set_aantal("geisoleerde_woningen", jaar + 1, zone, toekomstige_geisoleerd)
        self.stock_manager.set_aantal("leegstaande_woningen", jaar + 1, zone, leegstaand)
    
    def _calculate_derived_metrics(self, jaar: int, zone: str) -> None:
        """Calculate derived metrics (persons, hinder points) for a year and zone."""
        niet_geisoleerd = self.stock_manager.get_aantal("niet_geisoleerde_woningen", jaar, zone)
        geisoleerd = self.stock_manager.get_aantal("geisoleerde_woningen", jaar, zone)
        
        personen_zonder = niet_geisoleerd * PERSONEN_PER_WOONUNIT
        personen_met = geisoleerd * PERSONEN_PER_WOONUNIT
        
        # Calculate and store metrics
        metrics = {
            "gehinderde_personen_zonder_isolatie": personen_zonder,
            "gehinderde_personen_met_isolatie": personen_met,
            "totaal_gehinderde_personen": personen_zonder + personen_met,
            "hinderpunten": int(get_hinder_punten(personen_zonder, personen_met, zone)),
            "hinderpunten_isolatie": get_hinder_punten_zonder_isolatie(personen_zonder, zone),
            "hinderpunten_zonder_isolatie": get_hinder_punten_met_isolatie(personen_met, zone),
        }
        
        for metric_name, value in metrics.items():
            self.stock_manager.set_aantal(metric_name, jaar, zone, value)
