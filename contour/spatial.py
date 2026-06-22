"""Spatial allocation: gemeente → dB contour; CaPaKey stub."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from contour.schema import INDEX_NAME, banden_dataframe

OPP_AANDEEL_KOLOM = "Part de la surface du qs dans le noise contour"
GEMEENTE_KOLOM = "T_MUN_NL"


def conversietabel_gemeente_naar_db(
    sector_data: pd.DataFrame,
    gemeente_kolom: str = GEMEENTE_KOLOM,
    indicator: str = "lden",
) -> pd.DataFrame:
    """Gemeente x dB with normalised spatial share (sum sector area shares).

    ``sector_data`` is typically from ``population 2024 par bout de secteur stat.xlsx``
    (Brussel + Vlaanderen) or legacy Brussels-only sector file.
    """
    gewicht = (
        sector_data.groupby([gemeente_kolom, "dB"], as_index=False)[OPP_AANDEEL_KOLOM]
        .sum()
        .rename(columns={gemeente_kolom: "gemeente", OPP_AANDEEL_KOLOM: "gewicht_ruimtelijk"})
    )
    gewicht["aandeel"] = gewicht["gewicht_ruimtelijk"] / gewicht.groupby("gemeente")[
        "gewicht_ruimtelijk"
    ].transform("sum")
    gewicht = gewicht.rename(columns={"dB": "db"})
    gewicht["indicator"] = indicator
    return gewicht


def _banden_van_contour(df_contour: pd.DataFrame) -> pd.DataFrame:
    """Bandmetadata uit FLOW-contour (index) of legacy kolommen."""
    if "geluidscontour" in df_contour.columns and "db_ondergrens" in df_contour.columns:
        return df_contour[["geluidscontour", "db_ondergrens", "db_bovengrens"]].drop_duplicates()
    return banden_dataframe(df_contour.index)


def koppel_conversie_aan_contourband(
    conversie: pd.DataFrame,
    df_contour: pd.DataFrame,
) -> pd.DataFrame:
    """Attach geluidscontour label via db_ondergrens."""
    banden = _banden_van_contour(df_contour)
    return conversie.merge(banden, left_on="db", right_on="db_ondergrens", how="left")


def verdeel_gemeente_naar_contour(
    df_lang: pd.DataFrame,
    conversie_band: pd.DataFrame,
    jaartal: str | int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Allocate gemeente values to contour bands; returns (contour, niet_toewijsbaar)."""
    df = df_lang.copy()
    df = df[df["gemeente"].notna() & ~df["gemeente"].isin(["-", "Totalen", ""])]
    if jaartal is not None:
        df = df[df["jaar_indiening"] == str(jaartal)]

    gekoppeld = df.merge(
        conversie_band[["gemeente", "db", "aandeel", "geluidscontour", "db_ondergrens"]],
        on="gemeente",
        how="left",
    )
    gekoppeld["waarde_contour"] = gekoppeld["waarde"] * gekoppeld["aandeel"]

    niet_toewijsbaar = (
        gekoppeld[gekoppeld["geluidscontour"].isna()]
        .groupby(
            ["bron", "gemeente", "jaar_indiening", "handeling", "gebouw_functie", "metriek"],
            dropna=False,
        )["waarde"]
        .sum()
        .reset_index()
    )

    dim_cols = [
        "bron",
        "geluidscontour",
        "db_ondergrens",
        "jaar_indiening",
        "handeling",
        "gebouw_functie",
        "metriek",
    ]
    contour = (
        gekoppeld.dropna(subset=["geluidscontour"])
        .groupby(dim_cols, dropna=False)["waarde_contour"]
        .sum()
        .reset_index()
        .rename(columns={"waarde_contour": "waarde"})
    )
    return contour, niet_toewijsbaar


def capakey_naar_contour(
    transacties: pd.DataFrame,
    brussel_sector: pd.DataFrame,
    contour_lden: pd.DataFrame,
    extern_pad: Path | None = None,
) -> pd.DataFrame:
    """Attach geluidscontour via external mapping and/or Brussels sector join."""
    from contour.paths import CAPAKEY_CONTOUR_LDEN
    from contour.prices import bouw_capakey_contour_mapping

    mapping = bouw_capakey_contour_mapping(
        transacties, brussel_sector, contour_lden, extern_pad or CAPAKEY_CONTOUR_LDEN
    )
    if mapping.empty:
        out = transacties.copy()
        out["geluidscontour"] = pd.NA
        out["db_ondergrens"] = pd.NA
        return out

    return transacties.merge(
        mapping[["capakey", "geluidscontour", "db_ondergrens", "gewicht_ruimtelijk", "bron_mapping"]],
        on="capakey",
        how="left",
    )
