"""Validation rules for incompatible measure combinations."""

from typing import List, Tuple

from models.measure_selection_manager import MeasureSelectionManager
from models.stock_manager import StockManager


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
    # Isolatievoorschriften en woningverbod zijn incompatibel
    ("isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning", "woningverbod"),
    ("isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning", "woningverbod"),
]


def _measure_covers_zone(
    measure_selection_manager: MeasureSelectionManager,
    measure_id: str,
    zone: str,
    stock_manager: StockManager | None,
) -> bool:
    if measure_selection_manager.is_measure_applied(measure_id, zone):
        return True
    overlay = measure_selection_manager.get_selected_overlay(measure_id)
    if overlay is None or stock_manager is None:
        return False
    zone_mask = stock_manager.df_contour["zone"] == zone
    if not zone_mask.any():
        return False
    share_col = f"share_{overlay}"
    if share_col not in stock_manager.df_contour.columns:
        return False
    return float(stock_manager.df_contour.loc[zone_mask, share_col].astype(float).max()) > 0.0


def validate_measure_combinations(
    measure_selection_manager: MeasureSelectionManager,
    zones: Tuple[str, ...],
    stock_manager: StockManager | None = None,
) -> List[Tuple[str, str, str]]:
    """
    Valideer incompatibele maatregelcombinaties per zone (incl. overlay-dekking).

    Returns:
        List van tuples (zone, maatregel1, maatregel2)
    """
    conflicts: List[Tuple[str, str, str]] = []

    for zone in zones:
        for measure1, measure2 in INCOMPATIBLE_MEASURES:
            if _measure_covers_zone(
                measure_selection_manager, measure1, zone, stock_manager
            ) and _measure_covers_zone(
                measure_selection_manager, measure2, zone, stock_manager
            ):
                conflicts.append((zone, measure1, measure2))

    return conflicts


def get_conflict_message(
    zone: str,
    measure1: str,
    measure2: str,
    measure_selection_manager: MeasureSelectionManager,
) -> str:
    """Genereer een gebruiksvriendelijke error message voor een conflict."""
    try:
        name1 = measure_selection_manager.get_measure_descriptions().at[measure1, "naam_mooi"]
        name2 = measure_selection_manager.get_measure_descriptions().at[measure2, "naam_mooi"]
    except KeyError:
        name1 = measure1.replace("_", " ").title()
        name2 = measure2.replace("_", " ").title()

    return (
        f"⚠️ Conflict in zone {zone}: '{name1}' en '{name2}' "
        f"kunnen niet tegelijkertijd worden toegepast."
    )
