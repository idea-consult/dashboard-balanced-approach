"""Conservatietests voor proportionele vergunningen-toewijzing."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from contour_vlaanderen_kolommen import KOLOM_HERNAMING
from contour_vlaanderen_vergunningen import (
    vergunningen_gemiddeld_per_gemeente,
    wijs_proportioneel_toe,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_EXCEL = ROOT / "data/20260623 data vlaanderen 1.xlsx"
VERG_CSV = ROOT / "data/vergunningen_omgevingsloket_2026_lang.csv"
KWETS_CSV = ROOT / "data/vergunningen_kwetsbare_functies_2026_lang.csv"

TOLERANTIE = 1e-6


def _laad_overlap_df() -> pl.DataFrame:
    df = pl.read_excel(DATA_EXCEL).rename(KOLOM_HERNAMING)
    df = df.with_columns(
        inwoners=pl.when(pl.col("regio_nl") == "Vlaams Gewest")
        .then(pl.col("inwoners_client"))
        .when(pl.col("regio_nl") == "Brussels Hoofdstedelijk Gewest")
        .then(pl.col("inwoners_overlap"))
        .otherwise(pl.col("inwoners_overlap"))
    )
    totaal_inwoners_vlaanderen = (
        df.filter(pl.col("regio_nl") == "Vlaams Gewest").select(pl.col("inwoners")).sum().item()
    )
    totaal_woningen_vlaanderen = (
        df.filter(pl.col("regio_nl") == "Vlaams Gewest")
        .select(pl.col("aantal_woningen"))
        .sum()
        .item()
    )
    gemiddelde_inwoners_per_woning = totaal_inwoners_vlaanderen / totaal_woningen_vlaanderen
    return df.with_columns(
        aantal_woningen=pl.when(pl.col("regio_nl") == "Brussels Hoofdstedelijk Gewest")
        .then(pl.col("inwoners") / gemiddelde_inwoners_per_woning)
        .otherwise(pl.col("aantal_woningen"))
    )


def _wijs_nieuwbouw_toe(df: pl.DataFrame, df_vergunningen: pl.DataFrame) -> pl.DataFrame:
    df_gemeente = vergunningen_gemiddeld_per_gemeente(df_vergunningen, handeling="Nieuwbouw")
    return wijs_proportioneel_toe(
        df,
        df_gemeente,
        groep_kolom="naam_gemeente_nl",
        bron_groep_kolom="gemeente",
        bron_waarde_kolom="gemiddeld_per_jaar",
        gewicht_kolom="aantal_percelen_onbebouwd_woongebied",
        uitvoer_kolom="aantal_vergunningen_nieuwbouw",
    )


def _wijs_renovatie_toe(df: pl.DataFrame, df_vergunningen: pl.DataFrame) -> pl.DataFrame:
    df_gemeente = vergunningen_gemiddeld_per_gemeente(
        df_vergunningen,
        handeling="Verbouwen of hergebruik",
    )
    return wijs_proportioneel_toe(
        df,
        df_gemeente,
        groep_kolom="naam_gemeente_nl",
        bron_groep_kolom="gemeente",
        bron_waarde_kolom="gemiddeld_per_jaar",
        gewicht_kolom="aantal_woningen",
        uitvoer_kolom="aantal_vergunningen_renovatie",
    )


def _wijs_kwetsbare_toe(df: pl.DataFrame, df_kwetsbare: pl.DataFrame) -> pl.DataFrame:
    df_gemeente = vergunningen_gemiddeld_per_gemeente(
        df_kwetsbare,
        handeling="Totalen",
        metriek="Aantal projecten",
        gebouw_functie=None,
    )
    return wijs_proportioneel_toe(
        df,
        df_gemeente,
        groep_kolom="naam_gemeente_nl",
        bron_groep_kolom="gemeente",
        bron_waarde_kolom="gemiddeld_per_jaar",
        gewicht_kolom="aantal_percelen_onbebouwd_woongebied",
        uitvoer_kolom="aantal_vergunningen_kwetsbare_groepen",
    )


def _assert_totaal_behouden(
    out: pl.DataFrame,
    df: pl.DataFrame,
    df_gemeente: pl.DataFrame,
    *,
    uitvoer_kolom: str,
    gewicht_kolom: str,
) -> None:
    toegewezen = out[uitvoer_kolom].sum()
    verwacht = (
        df_gemeente.join(
            df.group_by("naam_gemeente_nl")
            .agg(pl.col(gewicht_kolom).fill_null(0).sum().alias("totaal_gewicht"))
            .rename({"naam_gemeente_nl": "gemeente"}),
            on="gemeente",
            how="inner",
        )
        .filter(pl.col("totaal_gewicht") > 0)["gemiddeld_per_jaar"]
        .sum()
    )
    assert toegewezen == pytest.approx(verwacht, abs=TOLERANTIE)


def _assert_per_gemeente_behouden(
    out: pl.DataFrame,
    df: pl.DataFrame,
    df_gemeente: pl.DataFrame,
    *,
    uitvoer_kolom: str,
    gewicht_kolom: str,
) -> None:
    totaal_gewicht = df.group_by("naam_gemeente_nl").agg(
        pl.col(gewicht_kolom).fill_null(0).sum().alias("totaal_gewicht")
    )
    per_gemeente = (
        out.group_by("naam_gemeente_nl")
        .agg(pl.col(uitvoer_kolom).sum().alias("toegewezen"))
        .join(
            df_gemeente,
            left_on="naam_gemeente_nl",
            right_on="gemeente",
            how="inner",
        )
        .join(totaal_gewicht, on="naam_gemeente_nl", how="left")
        .filter(pl.col("totaal_gewicht") > 0)
        .with_columns(
            (pl.col("toegewezen") - pl.col("gemiddeld_per_jaar")).abs().alias("afwijking")
        )
    )
    assert per_gemeente.filter(pl.col("afwijking") > TOLERANTIE).is_empty()


# --- Nieuwbouw ---


def test_nieuwbouw_synthetisch_voorbeeld_60_en_40() -> None:
    df = pl.DataFrame(
        {
            "naam_gemeente_nl": ["GemeenteX", "GemeenteX"],
            "aantal_percelen_onbebouwd_woongebied": [30.0, 20.0],
        }
    )
    df_gemeente = pl.DataFrame({"gemeente": ["GemeenteX"], "gemiddeld_per_jaar": [100.0]})

    out = wijs_proportioneel_toe(
        df,
        df_gemeente,
        groep_kolom="naam_gemeente_nl",
        bron_groep_kolom="gemeente",
        bron_waarde_kolom="gemiddeld_per_jaar",
        gewicht_kolom="aantal_percelen_onbebouwd_woongebied",
        uitvoer_kolom="aantal_vergunningen_nieuwbouw",
    )

    assert out["aantal_vergunningen_nieuwbouw"].to_list() == pytest.approx([60.0, 40.0])
    assert out["aantal_vergunningen_nieuwbouw"].sum() == pytest.approx(100.0)


@pytest.mark.skipif(not DATA_EXCEL.exists() or not VERG_CSV.exists(), reason="Data ontbreekt")
def test_nieuwbouw_real_data_totaal_behouden() -> None:
    df = pl.read_excel(DATA_EXCEL).rename(KOLOM_HERNAMING)
    df_vergunningen = pl.read_csv(VERG_CSV, separator=";")
    df_gemeente = vergunningen_gemiddeld_per_gemeente(df_vergunningen, handeling="Nieuwbouw")
    out = _wijs_nieuwbouw_toe(df, df_vergunningen)
    _assert_totaal_behouden(
        out,
        df,
        df_gemeente,
        uitvoer_kolom="aantal_vergunningen_nieuwbouw",
        gewicht_kolom="aantal_percelen_onbebouwd_woongebied",
    )


@pytest.mark.skipif(not DATA_EXCEL.exists() or not VERG_CSV.exists(), reason="Data ontbreekt")
def test_nieuwbouw_real_data_per_gemeente_behouden() -> None:
    df = pl.read_excel(DATA_EXCEL).rename(KOLOM_HERNAMING)
    df_vergunningen = pl.read_csv(VERG_CSV, separator=";")
    df_gemeente = vergunningen_gemiddeld_per_gemeente(df_vergunningen, handeling="Nieuwbouw")
    out = _wijs_nieuwbouw_toe(df, df_vergunningen)
    _assert_per_gemeente_behouden(
        out,
        df,
        df_gemeente,
        uitvoer_kolom="aantal_vergunningen_nieuwbouw",
        gewicht_kolom="aantal_percelen_onbebouwd_woongebied",
    )


# --- Renovatie ---


def test_renovatie_synthetisch_voorbeeld_60_en_40() -> None:
    df = pl.DataFrame(
        {
            "naam_gemeente_nl": ["GemeenteX", "GemeenteX"],
            "aantal_woningen": [30.0, 20.0],
        }
    )
    df_gemeente = pl.DataFrame({"gemeente": ["GemeenteX"], "gemiddeld_per_jaar": [100.0]})

    out = wijs_proportioneel_toe(
        df,
        df_gemeente,
        groep_kolom="naam_gemeente_nl",
        bron_groep_kolom="gemeente",
        bron_waarde_kolom="gemiddeld_per_jaar",
        gewicht_kolom="aantal_woningen",
        uitvoer_kolom="aantal_vergunningen_renovatie",
    )

    assert out["aantal_vergunningen_renovatie"].to_list() == pytest.approx([60.0, 40.0])
    assert out["aantal_vergunningen_renovatie"].sum() == pytest.approx(100.0)


@pytest.mark.skipif(not DATA_EXCEL.exists() or not VERG_CSV.exists(), reason="Data ontbreekt")
def test_renovatie_real_data_totaal_behouden() -> None:
    df = _laad_overlap_df()
    df_vergunningen = pl.read_csv(VERG_CSV, separator=";")
    df_gemeente = vergunningen_gemiddeld_per_gemeente(
        df_vergunningen,
        handeling="Verbouwen of hergebruik",
    )
    out = _wijs_renovatie_toe(df, df_vergunningen)
    _assert_totaal_behouden(
        out,
        df,
        df_gemeente,
        uitvoer_kolom="aantal_vergunningen_renovatie",
        gewicht_kolom="aantal_woningen",
    )


@pytest.mark.skipif(not DATA_EXCEL.exists() or not VERG_CSV.exists(), reason="Data ontbreekt")
def test_renovatie_real_data_per_gemeente_behouden() -> None:
    df = _laad_overlap_df()
    df_vergunningen = pl.read_csv(VERG_CSV, separator=";")
    df_gemeente = vergunningen_gemiddeld_per_gemeente(
        df_vergunningen,
        handeling="Verbouwen of hergebruik",
    )
    out = _wijs_renovatie_toe(df, df_vergunningen)
    _assert_per_gemeente_behouden(
        out,
        df,
        df_gemeente,
        uitvoer_kolom="aantal_vergunningen_renovatie",
        gewicht_kolom="aantal_woningen",
    )


# --- Kwetsbare groepen ---


def test_kwetsbare_synthetisch_voorbeeld_60_en_40() -> None:
    df = pl.DataFrame(
        {
            "naam_gemeente_nl": ["GemeenteX", "GemeenteX"],
            "aantal_percelen_onbebouwd_woongebied": [30.0, 20.0],
        }
    )
    df_gemeente = pl.DataFrame({"gemeente": ["GemeenteX"], "gemiddeld_per_jaar": [100.0]})

    out = wijs_proportioneel_toe(
        df,
        df_gemeente,
        groep_kolom="naam_gemeente_nl",
        bron_groep_kolom="gemeente",
        bron_waarde_kolom="gemiddeld_per_jaar",
        gewicht_kolom="aantal_percelen_onbebouwd_woongebied",
        uitvoer_kolom="aantal_vergunningen_kwetsbare_groepen",
    )

    assert out["aantal_vergunningen_kwetsbare_groepen"].to_list() == pytest.approx([60.0, 40.0])
    assert out["aantal_vergunningen_kwetsbare_groepen"].sum() == pytest.approx(100.0)


@pytest.mark.skipif(
    not DATA_EXCEL.exists() or not KWETS_CSV.exists(),
    reason="Data ontbreekt",
)
def test_kwetsbare_real_data_totaal_behouden() -> None:
    df = pl.read_excel(DATA_EXCEL).rename(KOLOM_HERNAMING)
    df_kwetsbare = pl.read_csv(KWETS_CSV, separator=";")
    df_gemeente = vergunningen_gemiddeld_per_gemeente(
        df_kwetsbare,
        handeling="Totalen",
        metriek="Aantal projecten",
        gebouw_functie=None,
    )
    out = _wijs_kwetsbare_toe(df, df_kwetsbare)
    _assert_totaal_behouden(
        out,
        df,
        df_gemeente,
        uitvoer_kolom="aantal_vergunningen_kwetsbare_groepen",
        gewicht_kolom="aantal_percelen_onbebouwd_woongebied",
    )


@pytest.mark.skipif(
    not DATA_EXCEL.exists() or not KWETS_CSV.exists(),
    reason="Data ontbreekt",
)
def test_kwetsbare_real_data_per_gemeente_behouden() -> None:
    df = pl.read_excel(DATA_EXCEL).rename(KOLOM_HERNAMING)
    df_kwetsbare = pl.read_csv(KWETS_CSV, separator=";")
    df_gemeente = vergunningen_gemiddeld_per_gemeente(
        df_kwetsbare,
        handeling="Totalen",
        metriek="Aantal projecten",
        gebouw_functie=None,
    )
    out = _wijs_kwetsbare_toe(df, df_kwetsbare)
    _assert_per_gemeente_behouden(
        out,
        df,
        df_gemeente,
        uitvoer_kolom="aantal_vergunningen_kwetsbare_groepen",
        gewicht_kolom="aantal_percelen_onbebouwd_woongebied",
    )
