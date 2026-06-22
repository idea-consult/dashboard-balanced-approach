"""Column renaming helpers."""

from __future__ import annotations

import pandas as pd

# FLOW §2.0 tellernamen (was lange Excel-kolomnamen)
KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR = "bebouwbare_percelen_woongebied(5jr)"
KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR = "niet_bebouwbare_percelen_woongebied_schrapping(5jr)"

# Ruwe Excel-kolomnamen (alleen voor mapping bij inladen)
_EXCEL_WOONGEBIED_AANDUIDING = (
    "aantal bebouwbare percelen die werden gecreëerd door woongebieden aan te duiden"
)
_EXCEL_WOONGEBIED_SCHRAPPING = (
    "aantal niet-bebouwbarepercelen die worden gecreëerd door woongebied te schrappen"
)

WOONGEBIED_KOLOMMEN = [KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR, KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR]

# Backwards-compat aliassen (tests / imports)
KOL_WOONGEBIED_AANDUIDING = KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR
KOL_WOONGEBIED_SCHRAPPING = KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR


def hernoem_vlaanderen_kolommen(df: pd.DataFrame) -> pd.DataFrame:
    """Map contour_vlaanderen_stocks.xlsx naar technische + FLOW-kolommen."""
    mapping = {
        "db_contour": "geluidscontour",
        "lower": "db_ondergrens",
        "upper": "db_bovengrens",
        "huizen": "aantal_woningen",
        "woningen": "aantal_woningen",
        _EXCEL_WOONGEBIED_AANDUIDING: KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR,
        _EXCEL_WOONGEBIED_SCHRAPPING: KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR,
    }
    return df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})


def hernoem_brussel_kolommen(df: pd.DataFrame) -> pd.DataFrame:
    """Map French Brussels population column names."""
    return df.rename(
        columns={
            "dB": "db",
            "Population dans le contour": "inwoners",
        }
    )
