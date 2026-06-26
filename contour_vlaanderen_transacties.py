"""Kolommapping en documentatie voor vastgoedtransacties (woningen, appartementen, percelen)."""

from __future__ import annotations

import polars as pl
import streamlit as st

WONING_TRANSACTIE_HERNAMING = {
    "NISCode": "capakey",
    "houses_sum_ParcelsNumber": "huis_aantal_transacties",
    "houses_avg_PriceP25": "huis_prijs_p25_gemeten",
    "houses_avg_PriceP50": "huis_prijs_p50_gemeten",
    "houses_avg_PriceP75": "huis_prijs_p75_gemeten",
    "houses_avg_ParcelsAreaP50": "huis_oppervlakte_p50_m2",
    "houses_average_price_m2": "huis_prijs_per_m2_gemeten",
    "houses_avg_PriceP50_filled": "huis_prijs_p50_ingevuld",
    "houses_avg_PriceP50_status": "huis_prijs_p50_status",
    "houses_avg_PriceP50_distance_m": "huis_prijs_p50_afstand_buur_m",
    "houses_average_price_m2_filled": "huis_prijs_per_m2_ingevuld",
    "houses_average_price_m2_status": "huis_prijs_per_m2_status",
    "houses_average_price_m2_distance_m": "huis_prijs_per_m2_afstand_buur_m",
}

APPARTEMENT_TRANSACTIE_HERNAMING = {
    "NISCode": "capakey",
    "Appartment_sum_ParcelsNumber": "appartement_aantal_transacties",
    "Appartment_avg_PriceP25": "appartement_prijs_p25_gemeten",
    "Appartment_avg_PriceP50": "appartement_prijs_p50_gemeten",
    "Appartment_avg_PriceP75": "appartement_prijs_p75_gemeten",
    "Appartment_avg_ParcelsAreaP50": "appartement_oppervlakte_p50_m2",
    "Appartment_average_price_m2": "appartement_prijs_per_m2_gemeten",
    "Appartment_avg_PriceP50_filled": "appartement_prijs_p50_ingevuld",
    "Appartment_avg_PriceP50_status": "appartement_prijs_p50_status",
    "Appartment_avg_PriceP50_source_CS01012024": "appartement_prijs_p50_bron_capakey",
    "Appartment_avg_PriceP50_distance_m": "appartement_prijs_p50_afstand_buur_m",
}

PERCEEL_TRANSACTIE_HERNAMING = {
    "NISCode": "capakey",
    "terrain_batissable_sum_ParcelsNumber": "bebouwbaar_aantal_transacties",
    "terrain_batissable_avg_PriceP25": "bebouwbaar_prijs_p25_gemeten",
    "terrain_batissable_avg_PriceP50": "bebouwbaar_prijs_p50_gemeten",
    "terrain_batissable_avg_PriceP75": "bebouwbaar_prijs_p75_gemeten",
    "terrain_batissable_avg_ParcelsAreaP50": "bebouwbaar_oppervlakte_p50_m2",
    "terrain_batissable_average_price_m2": "bebouwbaar_prijs_per_m2_gemeten",
}

PERCEEL_TRANSACTIE_SEGMENTEN = (
    {
        "aantal_kolom": "bebouwbaar_aantal_transacties",
        "prijs_kolom": "bebouwbaar_prijs_p50_gemeten",
        "transacties_uitvoer": "aantal_bebouwbare_perceel_transacties_per_jaar",
        "prijs_uitvoer": "gemiddelde_prijs_bebouwbaar_perceel",
        "gewicht_kolom": "onbebouwde_bebouwbare_percelen",
        "label": "bebouwbare percelen (terrain bâtissable)",
    },
)

TRANSACTIE_KOLOM_UITLEG = [
    (
        "capakey",
        "CaPaKey (kadastraal perceel); in de bronbestanden heet deze kolom `NISCode`.",
    ),
    (
        "huis_aantal_transacties / appartement_aantal_transacties",
        "Aantal vastgoedtransacties op dat perceel in het betreffende segment (woning of "
        "appartement). Dit is het gewicht bij prijsaggregatie.",
    ),
    (
        "*_prijs_p50_gemeten (en p25/p75, prijs_per_m2_gemeten)",
        "**Direct gemeten** mediaanprijs op basis van transacties in de statistische sector. "
        "Ontbreekt wanneer er te weinig transacties zijn om de sector GDPR-proof te publiceren.",
    ),
    (
        "*_prijs_p50_ingevuld (en prijs_per_m2_ingevuld)",
        "**Ingevulde** prijs: voor sectoren zonder voldoende transacties berekend via "
        "*closest neighbours* in GIS (gemiddelde van naburige sectoren/percelen). Gebruiken "
        "we in de analyse omdat elke CaPaKey zo een bruikbare prijs heeft.",
    ),
    (
        "*_prijs_p50_status",
        "Of de ingevulde prijs overeenkomt met de gemeten prijs (`measured`) of een schatting "
        "is (`filled` / buur-imputatie).",
    ),
    (
        "*_prijs_p50_afstand_buur_m",
        "Afstand (m) tot de dichtstbijzijnde buur gebruikt bij GIS-imputatie; leeg bij "
        "gemeten prijzen.",
    ),
    (
        "appartement_prijs_p50_bron_capakey",
        "CaPaKey van de bronpercelen waaruit de appartementsprijs is afgeleid (alleen bij "
        "ingevulde waarden).",
    ),
]

PERCEEL_TRANSACTIE_KOLOM_UITLEG = [
    (
        "terrain_batissable",
        "Onbebouwd **bebouwbaar** woongebied-perceel; komt overeen met de stock "
        "`onbebouwde_bebouwbare_percelen`. Segmenten voor onbebouwbare percelen "
        "(`terrain_non_batissable`, …) worden niet ingelezen.",
    ),
    (
        "*_prijs_p50_gemeten",
        "Mediaanprijs (P50) per CaPaKey op basis van transacties in de statistische sector. "
        "Geen aparte GIS-ingevulde kolom in deze bron — ontbrekende waarden blijven leeg.",
    ),
]


def aggregeer_transacties_naar_sector(
    df_capakey: pl.DataFrame,
    *,
    transactie_kolom: str,
    prijs_kolom: str,
    transacties_uitvoer: str,
    prijs_uitvoer: str,
) -> pl.DataFrame:
    """Aggregeer CaPaKey-transacties naar statistische sector (zelfde logica als woningen)."""
    return (
        df_capakey.with_columns(
            pl.col("capakey").str.strip_chars_end("-").alias("nis_sector"),
            pl.col(transactie_kolom).fill_null(0).alias("_transacties"),
            pl.col(prijs_kolom).alias("_prijs"),
        )
        .group_by("nis_sector")
        .agg(
            pl.col("_transacties").sum().alias(transacties_uitvoer),
            pl.when(pl.col("_transacties").sum() > 0)
            .then((pl.col("_prijs") * pl.col("_transacties")).sum() / pl.col("_transacties").sum())
            .otherwise(pl.col("_prijs").mean())
            .alias(prijs_uitvoer),
        )
    )


def toon_transactie_kolomdocumentatie() -> None:
    """Toon kolomuitleg voor de transactie-CSV's in Streamlit."""
    st.markdown(
        "Prijzen staan per segment (**woning** = eengezinswoning, **appartement**). "
        "Kolommen met suffix `_gemeten` komen rechtstreeks uit transactiedata (alleen waar "
        "voldoende volume voor GDPR-publicatie). Kolommen met `_ingevuld` zijn via GIS-buren "
        "aangevuld voor sectoren met te weinig transacties."
    )
    for naam, uitleg in TRANSACTIE_KOLOM_UITLEG:
        st.markdown(f"**{naam}** — {uitleg}")


def toon_perceel_transactie_kolomdocumentatie() -> None:
    """Toon kolomuitleg voor de perceeltransactie-CSV in Streamlit."""
    st.markdown(
        "Perceeltransacties staan per CaPaKey in één bestand; we importeren enkel "
        "**bebouwbaar** woongebied (`terrain_batissable`). De analyse gebruikt mediaanprijs "
        "P50 (`*_avg_PriceP50`)."
    )
    for naam, uitleg in PERCEEL_TRANSACTIE_KOLOM_UITLEG:
        st.markdown(f"**{naam}** — {uitleg}")
