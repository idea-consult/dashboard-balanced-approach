"""Kolommapping en documentatie voor vastgoedtransacties (woningen / appartementen)."""

from __future__ import annotations

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
