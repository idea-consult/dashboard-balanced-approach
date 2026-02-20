"""Calculation functions for derived metrics."""

from util.helpers import (
    get_hinder_punten,
    get_hinder_punten_met_isolatie,
    get_hinder_punten_zonder_isolatie,
)
from config import PERSONEN_PER_WOONUNIT


def calculate_initial_metrics(stock_manager, zones: tuple, beginjaar: int) -> None:
    """
    Calculate initial metrics for the starting year.
    
    Args:
        stock_manager: StockManager instance
        zones: Tuple of zone identifiers
        beginjaar: Starting year
    """
    for z in zones:
        niet_geisoleerde_woningen = stock_manager.get_aantal(
            "niet_geisoleerde_woningen", beginjaar, z
        )
        geisoleerde_woningen = stock_manager.get_aantal(
            "geisoleerde_woningen", beginjaar, z
        )
        
        # Calculate hindered persons
        gehinderde_personen_zonder_isolatie = (
            niet_geisoleerde_woningen * PERSONEN_PER_WOONUNIT
        )
        gehinderde_personen_met_isolatie = (
            geisoleerde_woningen * PERSONEN_PER_WOONUNIT
        )
        totaal_gehinderde_personen = (
            gehinderde_personen_zonder_isolatie + gehinderde_personen_met_isolatie
        )
        
        # Calculate hinder points
        hinderpunten = get_hinder_punten(
            gehinderde_personen_zonder_isolatie,
            gehinderde_personen_met_isolatie,
            z,
        )
        hinderpunten_isolatie = get_hinder_punten_zonder_isolatie(
            gehinderde_personen_zonder_isolatie, z
        )
        hinderpunten_zonder_isolatie = get_hinder_punten_met_isolatie(
            gehinderde_personen_met_isolatie, z
        )
        
        # Set all calculated values
        stock_manager.set_aantal("hinderpunten", beginjaar, z, hinderpunten)
        stock_manager.set_aantal(
            "hinderpunten_isolatie", beginjaar, z, hinderpunten_isolatie
        )
        stock_manager.set_aantal(
            "hinderpunten_zonder_isolatie", beginjaar, z, hinderpunten_zonder_isolatie
        )
        stock_manager.set_aantal(
            "gehinderde_personen_zonder_isolatie",
            beginjaar,
            z,
            gehinderde_personen_zonder_isolatie,
        )
        stock_manager.set_aantal(
            "gehinderde_personen_met_isolatie",
            beginjaar,
            z,
            gehinderde_personen_met_isolatie,
        )
        stock_manager.set_aantal(
            "totaal_gehinderde_personen", beginjaar, z, totaal_gehinderde_personen
        )


def calculate_totals(stock_manager, zones: tuple, beginjaar: int, eindjaar: int) -> None:
    """
    Calculate total values across all zones for each year.
    
    Args:
        stock_manager: StockManager instance
        zones: Tuple of zone identifiers
        beginjaar: Starting year
        eindjaar: Ending year (inclusive)
    """
    metrics = [
        "gehinderde_personen_met_isolatie",
        "gehinderde_personen_zonder_isolatie",
        "hinderpunten",
        "hinderpunten_isolatie",
        "hinderpunten_zonder_isolatie",
        "totaal_gehinderde_personen",
    ]
    
    for j in range(beginjaar, eindjaar + 1):
        for metric in metrics:
            total = sum(
                stock_manager.get_aantal(metric, j, z) for z in zones
            )
            stock_manager.set_aantal(metric, j, "Totaal", total)
