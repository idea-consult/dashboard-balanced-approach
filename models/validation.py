"""Validation rules for incompatible measure combinations."""

from typing import List, Tuple
from models.measure_selection_manager import MeasureSelectionManager


# Definieer incompatibele maatregel combinaties
# Elke tuple bevat maatregelen die niet samen op dezelfde zone mogen worden toegepast
INCOMPATIBLE_MEASURES = [
    # Aankoopbeleid en voorkooprecht kunnen niet samen
    ("aankoopbeleid_niet_geïsoleerde_woningen", "voorkooprecht_niet_geïsoleerde_woningen"),
    ("aankoopbeleid_geïsoleerde_woningen", "voorkooprecht_geïsoleerde_woningen"),
    ("aankoopbeleid_percelen", "voorkooprecht_percelen"),
    # Nieuw: drie percelenmaatregelen mogen nooit gecombineerd worden
    ("aankoopbeleid_percelen", "onteigening_percelen"),
    ("voorkooprecht_percelen", "onteigening_percelen"),
    ("aankoopbeleid_percelen", "voorkooprecht_percelen"),
    # Isolatievoorschriften en verbod op kleinschalige woningen zijn incompatibel
    ("isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning", "verbod_kleine_woning"),
    ("isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning", "verbod_kleine_woning"),
]


def validate_measure_combinations(
    measure_selection_manager: MeasureSelectionManager, zones: Tuple[str, ...]
) -> List[Tuple[str, str, str]]:
    """
    Valideer of er incompatibele maatregel combinaties zijn per zone.
    
    Args:
        measure_selection_manager: manager om te controleren welke maatregelen actief zijn
        
    Returns:
        List van tuples (zone, maatregel1, maatregel2) voor elke gevonden conflict
    """
    conflicts = []
    
    for zone in zones:
        # Check elke incompatibele combinatie
        for measure1, measure2 in INCOMPATIBLE_MEASURES:
            if (
                measure_selection_manager.is_measure_applied(measure1, zone) and
                measure_selection_manager.is_measure_applied(measure2, zone)
            ):
                conflicts.append((zone, measure1, measure2))
    
    return conflicts


def get_conflict_message(
    zone: str,
    measure1: str,
    measure2: str,
    measure_selection_manager: MeasureSelectionManager,
) -> str:
    """
    Genereer een gebruiksvriendelijke error message voor een conflict.
    
    Args:
        zone: Zone identifier
        measure1: Eerste maatregel naam
        measure2: Tweede maatregel naam
        measure_selection_manager: manager om mooie namen op te halen
        
    Returns:
        Error message string
    """
    # Haal mooie namen op uit beschrijvingen
    try:
        name1 = measure_selection_manager.get_measure_descriptions().at[measure1, "naam_mooi"]
        name2 = measure_selection_manager.get_measure_descriptions().at[measure2, "naam_mooi"]
    except KeyError:
        # Fallback naar technische naam als beschrijving niet gevonden
        name1 = measure1.replace("_", " ").title()
        name2 = measure2.replace("_", " ").title()
    
    return (
        f"⚠️ Conflict in zone {zone}: '{name1}' en '{name2}' "
        f"kunnen niet tegelijkertijd worden toegepast."
    )
