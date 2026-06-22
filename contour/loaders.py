"""Load raw contour, permit and transaction sources."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from contour.columns import hernoem_brussel_kolommen, hernoem_vlaanderen_kolommen
from contour.paths import (
    CONTOUR_VLAANDEREN,
    INWONERS_BRUSSEL,
    POPULATION_SECTOR,
    POPULATION_SECTOR_SHEETS,
    TRANSACTIES_DIR,
    VERGUNNINGEN_KWETSBAAR,
    VERGUNNINGEN_OMGEVINGSLOKET,
    VERGUNNINGEN_VERKAVELING,
)
from contour.vergunningen import lees_vergunningen_lang as _lees_vergunningen_csv


def _lees_excel(pad: Path, **kwargs: Any) -> pd.DataFrame:
    """Read Excel; copy to temp file when OneDrive or Excel locks the source."""
    try:
        return pd.read_excel(pad, **kwargs)
    except PermissionError:
        fd, tmp = tempfile.mkstemp(suffix=pad.suffix)
        os.close(fd)
        try:
            shutil.copy2(pad, tmp)
            return pd.read_excel(tmp, **kwargs)
        except PermissionError as exc:
            raise PermissionError(
                f"Kan '{pad.name}' niet lezen (bestand vergrendeld?). "
                "Sluit het in Excel en wacht tot OneDrive klaar is met synchroniseren."
            ) from exc
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


def lees_contour_vlaanderen() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (lden, lnight) raw Vlaanderen contour tables."""
    lden = _lees_excel(CONTOUR_VLAANDEREN, sheet_name="lden")
    lnight = _lees_excel(CONTOUR_VLAANDEREN, sheet_name="lnight")
    return hernoem_vlaanderen_kolommen(lden), hernoem_vlaanderen_kolommen(lnight)


def lees_brussel_sector() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (lden, lnight) Brussels statistical-sector tables (inwoners Brussel)."""
    lden = _lees_excel(INWONERS_BRUSSEL, sheet_name="lden")
    lnight = _lees_excel(INWONERS_BRUSSEL, sheet_name="lnight")
    return lden, lnight


def lees_sector_contour(indicator: str = "lden") -> pd.DataFrame:
    """Statistical-sector x dB table for Brussel + Vlaanderen (gemeente-contour gewichten)."""
    sheet = POPULATION_SECTOR_SHEETS[indicator]
    return _lees_excel(POPULATION_SECTOR, sheet_name=sheet)


def lees_sector_contour_beide() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (lden, lnight) sector-contour intersection tables."""
    return lees_sector_contour("lden"), lees_sector_contour("lnight")


def lees_brussel_inwoners_per_db() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate Brussels population to dB band."""
    lden_ruw, lnight_ruw = lees_brussel_sector()
    lden = hernoem_brussel_kolommen(lden_ruw[["dB", "Population dans le contour"]])
    lnight = hernoem_brussel_kolommen(lnight_ruw[["dB", "Population dans le contour"]])
    lden = lden.groupby("db", as_index=False)["inwoners"].sum()
    lnight = lnight.groupby("db", as_index=False)["inwoners"].sum()
    return lden, lnight


def lees_vergunningen() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (omgevingsloket, kwetsbare, verkaveling) long-format permit tables."""
    return (
        _lees_vergunningen_csv(VERGUNNINGEN_OMGEVINGSLOKET),
        _lees_vergunningen_csv(VERGUNNINGEN_KWETSBAAR),
        _lees_vergunningen_csv(VERGUNNINGEN_VERKAVELING),
    )


TRANSACTIE_BESTANDEN = {
    "woningen": "transacties_woningen.csv",
    "appartementen": "transacties_appartementen.csv",
    "handel": "transacties_handel.csv",
    "kantoren": "transacties_kantoren.csv",
    "industrie_bebouwd": "transacties_industrie_bebouwd.csv",
    "industrie_terrein": "transacties_industrie_terrein.csv",
}


def lees_transacties(transacties_dir: Path | None = None) -> pd.DataFrame:
    """Load all transaction segment CSVs into one long table."""
    base = transacties_dir or TRANSACTIES_DIR
    frames: list[pd.DataFrame] = []
    for segment, bestand in TRANSACTIE_BESTANDEN.items():
        pad = base / bestand
        if not pad.exists():
            continue
        df = pd.read_csv(pad, sep="\t")
        df = df.rename(columns={"NISCode": "capakey"})
        df["segment"] = segment
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["segment", "capakey", "sum_ParcelsNumber"])
    return pd.concat(frames, ignore_index=True)
