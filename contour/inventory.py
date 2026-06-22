"""Data inventory aligned with STOCKS_EN_FLOWS_BEREKENEN.md §2."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from contour.paths import (
    CONTOUR_VLAANDEREN,
    DATA_DIR,
    INWONERS_BRUSSEL,
    POPULATION_SECTOR,
    TRANSACTIES_DIR,
    VERGUNNINGEN_KWETSBAAR,
    VERGUNNINGEN_OMGEVINGSLOKET,
    VERGUNNINGEN_VERKAVELING,
)


INVENTORY_ROWS = [
    ("contour_vlaanderen_stocks.xlsx", CONTOUR_VLAANDEREN, "lden/lnight stocks", "ok"),
    ("inwoners_brussel_sector_contour_2024.xlsx", INWONERS_BRUSSEL, "Brussel sector x dB (inwoners)", "ok"),
    (
        "population 2024 par bout de secteur stat.xlsx",
        POPULATION_SECTOR,
        "Sector x dB Brussel+Vlaanderen (gemeente-contour)",
        "ok",
    ),
    ("vergunningen_omgevingsloket_2026_lang.csv", VERGUNNINGEN_OMGEVINGSLOKET, "Vergunningen lang", "deels"),
    ("vergunningen_kwetsbare_functies_2026_lang.csv", VERGUNNINGEN_KWETSBAAR, "Kwetsbare functies", "deels"),
    ("vergunningen_verkaveling_2026_lang.csv", VERGUNNINGEN_VERKAVELING, "Verkaveling/sloop", "deels"),
    ("transacties_vastgoed/", TRANSACTIES_DIR, "CaPaKey transacties", "deels"),
]


def _lees_metadata(pad: Path) -> tuple[int | None, list[str] | None]:
    if not pad.exists():
        return None, None
    if pad.is_dir():
        bestanden = sorted(pad.glob("*.csv"))
        return len(bestanden), [b.name for b in bestanden]
    if pad.suffix == ".csv":
        df = pd.read_csv(pad, sep=";" if "lang" in pad.name else ",", nrows=0)
        full = pd.read_csv(pad, sep=";" if "lang" in pad.name else ",")
        return len(full), list(df.columns)
    if pad.suffix == ".xlsx":
        xl = pd.ExcelFile(pad)
        return None, xl.sheet_names
    return None, None


def maak_data_inventory(data_dir: Path | None = None) -> pd.DataFrame:
    """Per source file: path, rows, columns, FLOW status."""
    records = []
    for naam, pad, beschrijving, status in INVENTORY_ROWS:
        base = data_dir or DATA_DIR
        volledig_pad = pad if pad.is_absolute() else base / pad.name if pad.parent == DATA_DIR else pad
        if not volledig_pad.exists() and pad.name:
            volledig_pad = base / pad.name if pad != TRANSACTIES_DIR else TRANSACTIES_DIR
        rijen, kolommen = _lees_metadata(volledig_pad if volledig_pad.exists() else pad)
        records.append(
            {
                "bestand": naam,
                "pad": str(pad),
                "beschrijving": beschrijving,
                "rijen": rijen,
                "kolommen": ", ".join(kolommen) if kolommen else None,
                "status": status,
            }
        )
    return pd.DataFrame(records)
