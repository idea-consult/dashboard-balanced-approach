"""Showcase: flow rates & prijzen (output of contour_analyse_2.py)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import polars as pl
import streamlit as st

from contour_vlaanderen_grafieken import (
    toon_flow_rate_staafdiagram,
    toon_staafdiagram_per_gewest,
)

_FLOW_SIZE_PATH = Path("input/flow_size.csv")
_DATA_2_PATH = Path("data_2/data_2.csv")


@st.cache_data
def load_flow_size() -> pl.DataFrame:
    if not _FLOW_SIZE_PATH.is_file():
        raise FileNotFoundError(_FLOW_SIZE_PATH)
    return pl.read_csv(_FLOW_SIZE_PATH)


@st.cache_data
def load_intersecties() -> pl.DataFrame:
    if not _DATA_2_PATH.is_file():
        raise FileNotFoundError(_DATA_2_PATH)
    return pl.read_csv(_DATA_2_PATH)


def _flow_chart(df_flows: pl.DataFrame, measure_id: str) -> None:
    toon_flow_rate_staafdiagram(df_flows, measure_id)


def _render_prijzen(df_intersecties: pl.DataFrame) -> None:
    toon_staafdiagram_per_gewest(
        df_intersecties,
        kolom="gemiddelde_prijs_van_een_woning",
        titel="Prijs bewoonde woning (geïsoleerd en niet-geïsoleerd)",
        y_label="Gemiddelde prijs (€)",
        aggregatie="gemiddelde",
        gewicht_kolom="aantal_woning_transacties_per_jaar",
        waarde_format=",.0f",
        toon_kaart=False,
    )
    toon_staafdiagram_per_gewest(
        df_intersecties,
        kolom="gemiddelde_prijs_bebouwbaar_perceel",
        titel="Prijs onbebouwd bebouwbare percelen",
        y_label="Gemiddelde prijs (€)",
        aggregatie="gemiddelde",
        gewicht_kolom="aantal_bebouwbare_perceel_transacties_per_jaar",
        waarde_format=",.0f",
        toon_kaart=False,
    )


FlowSection = dict[str, str | str | Callable[..., None] | None]

FLOW_SECTIONS: list[FlowSection] = [
    {
        "markdown": """
# Aggregatie per LDEN-band

`data_2.csv` heeft één rij per **intersectie** (statistische sector × LDEN-band). Voor flow rates
werken we op **contourniveau**: alle intersecties met dezelfde `db_lden` worden samengevoegd.

Telbare grootheden worden **opgeteld**. Daarna berekenen we flow rates als teller / noemer op die
geaggregeerde rij. Het resultaat staat in `input/flow_size.csv`.
""",
    },
    {
        "markdown": """
# Stocks

Stocks werden in `contour_analyse_1.py` berekend. Belangrijke placeholders:

| Stock | Opmerking |
|-------|-----------|
| `onbebouwde_onbebouwbare_percelen` | 3× bebouwbare percelen |
| `bewoonde_niet_geïsoleerde_woning` | 80% (VL) / 95% (BXL) van woningen |
| `bewoonde_geïsoleerde_woning` | 20% (VL) / 5% (BXL) van woningen |
| `nieuwe_woning` | Simulator-tussenstock; steeds 0 |
""",
    },
    {
        "markdown": """
# Flows

Per flow bepalen we een **flow rate** in **baseline** (zonder maatregel) en **active** (maatregel
aan). Een flow rate is een jaarlijks aandeel: teller / noemer, uitgedrukt als percentage in de
grafiek. Onderstaande grafieken tonen de vooraf berekende waarden per LDEN-band.
""",
    },
    {
        "markdown": """
## verkavelings_verbod

Verkavelingsverbod: beperkt de verdichting op onbebouwde bebouwbare percelen.

**Baseline** en **active:** `0` — nog niet gekoppeld aan brondata.
""",
        "measure_id": "verkavelings_verbod",
    },
    {
        "markdown": """
## Woongebiedverbod

Transfer van onbebouwde onbebouwbare naar bebouwbare percelen (of omgekeerd bij schrapping).

**Baseline:** netto woongebied-creatie / stock onbebouwbare percelen.

**Active:** enkel schrapping (bebouwbaar → onbebouwbaar) / stock onbebouwbare percelen.
""",
        "measure_id": "woongebiedverbod",
    },
    {
        "markdown": """
## aankoopbeleid_percelen

Overheid koopt onbebouwde bebouwbare percelen aan.

**Baseline:** `0`. **Active (placeholder):** 25% van bebouwbare perceeltransacties / stock.
""",
        "measure_id": "aankoopbeleid_percelen",
    },
    {
        "markdown": """
## voorkooprecht_percelen

Gemeente/regio oefent voorkooprecht uit op onbebouwde bebouwbare percelen.

**Baseline:** `0`. **Active (placeholder):** 50% van bebouwbare perceeltransacties / stock.
""",
        "measure_id": "voorkooprecht_percelen",
    },
    {
        "markdown": """
## onteigening_percelen

Gedwongen onteigening van onbebouwde bebouwbare percelen.

**Baseline:** `0`. **Active (placeholder):** vaste rate **5%** per band.
""",
        "measure_id": "onteigening_percelen",
    },
    {
        "markdown": """
## verbod_kleine_woning

**Baseline (placeholder):** 97% van nieuwbouwvergunningen / bebouwbare percelen.

**Active:** `0`.
""",
        "measure_id": "verbod_kleine_woning",
    },
    {
        "markdown": """
## verbod_grote_woning

**Baseline (placeholder):** 3% van nieuwbouwvergunningen / bebouwbare percelen.

**Active:** `0`.
""",
        "measure_id": "verbod_grote_woning",
    },
    {
        "markdown": """
## verbod_kwetsbare_groep

**Baseline:** kwetsbare-groepenvergunningen / bebouwbare percelen.

**Active:** `0`.
""",
        "measure_id": "verbod_kwetsbare_groep",
    },
    {
        "markdown": """
## woonverdichtingsverbod_niet_geïsoleerde_woningen

Beperkt jaarlijkse groei van niet-geïsoleerde bewoonde woningen.

**Baseline** en **active (placeholder):** `0` — referentiemodel suggereert baseline **1%**.
""",
        "measure_id": "woonverdichtingsverbod_niet_geïsoleerde_woningen",
    },
    {
        "markdown": """
## woonverdichtingsverbod_geïsoleerde_woningen

Beperkt jaarlijkse groei van geïsoleerde bewoonde woningen.

**Baseline** en **active (placeholder):** `0`.
""",
        "measure_id": "woonverdichtingsverbod_geïsoleerde_woningen",
    },
    {
        "markdown": """
## aankoopbeleid_niet_geïsoleerde_woningen

**Baseline:** `0`. **Active (placeholder):** 25% van transacties niet-geïsoleerde woningen /
niet-geïsoleerde stock.
""",
        "measure_id": "aankoopbeleid_niet_geïsoleerde_woningen",
    },
    {
        "markdown": """
## aankoopbeleid_geïsoleerde_woningen

**Baseline:** `0`. **Active (placeholder):** 25% van transacties geïsoleerde woningen /
geïsoleerde stock.
""",
        "measure_id": "aankoopbeleid_geïsoleerde_woningen",
    },
    {
        "markdown": """
## voorkooprecht_niet_geïsoleerde_woningen

**Baseline:** `0`. **Active (placeholder):** 50% van transacties niet-geïsoleerde woningen /
niet-geïsoleerde stock.
""",
        "measure_id": "voorkooprecht_niet_geïsoleerde_woningen",
    },
    {
        "markdown": """
## voorkooprecht_geïsoleerde_woningen

**Baseline:** `0`. **Active (placeholder):** 50% van transacties geïsoleerde woningen /
geïsoleerde stock.
""",
        "measure_id": "voorkooprecht_geïsoleerde_woningen",
    },
    {
        "markdown": """
## onteigening_niet_geïsoleerde_woningen

**Baseline:** `0`. **Active (placeholder):** vaste rate **5%** per band.
""",
        "measure_id": "onteigening_niet_geïsoleerde_woningen",
    },
    {
        "markdown": """
## onteigening_geïsoleerde_woningen

**Baseline:** `0`. **Active (placeholder):** vaste rate **5%** per band.
""",
        "measure_id": "onteigening_geïsoleerde_woningen",
    },
    {
        "markdown": """
## isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning

**Baseline (placeholder):** 50%. **Active:** `0`.
""",
        "measure_id": "isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning",
    },
    {
        "markdown": """
## isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning

**Baseline (placeholder):** 50%. **Active (placeholder):** 100%.
""",
        "measure_id": "isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning",
    },
    {
        "markdown": """
## renovatie_zonder_maatregel

Spontane renovatie met akoestische isolatie (niet-geïsoleerd → geïsoleerd).

**Baseline:** `0`. **Active (placeholder):** 20% van renovatievergunningen / niet-geïsoleerde stock.
""",
        "measure_id": "renovatie_zonder_maatregel",
    },
    {
        "markdown": """
## verplicht_isoleren_renovatie

**Baseline:** `0`. **Active (placeholder):** 80% van renovatievergunningen / niet-geïsoleerde stock.
""",
        "measure_id": "verplicht_isoleren_renovatie",
    },
    {
        "markdown": """
## gesubsidieerd_isolatieprogramma

**Baseline:** `0`. **Active (placeholder):** 2× renovatiestroom / niet-geïsoleerde stock.
""",
        "measure_id": "gesubsidieerd_isolatieprogramma",
    },
    {
        "markdown": """
## gestuurd_isolatieprogramma

**Baseline:** `0`. **Active (placeholder):** 4× renovatiestroom / niet-geïsoleerde stock.
""",
        "measure_id": "gestuurd_isolatieprogramma",
    },
    {
        "markdown": """
## aanleg_geluidsbuffers

Investering in geluidsbuffers; effect op stocks nog niet gekwantificeerd.

**Baseline** en **active:** `0` — placeholder.
""",
        "measure_id": "aanleg_geluidsbuffers",
    },
    {
        "markdown": """
## compensatie_buitenzone

Compensatie door verplaatsing naar buiten de contourzone. **Nog niet uitgewerkt.**

**Baseline** en **active:** `0`.
""",
        "measure_id": "compensatie_buitenzone",
    },
    {
        "markdown": """
## compensatie_verhuis

Compensatie via verhuis binnen/buiten de contour. **Nog niet uitgewerkt.**

**Baseline** en **active:** `0`.
""",
        "measure_id": "compensatie_verhuis",
    },
    {
        "markdown": """
## versterken_sociale_cohesie

Maatregel rond sociale cohesie; geen kwantitatieve flow in deze analyse.

**Baseline** en **active:** `0`.
""",
        "measure_id": "versterken_sociale_cohesie",
    },
    {
        "markdown": """
## vergroenen_leefomgeving

Maatregel rond vergroening; geen kwantitatieve flow in deze analyse.

**Baseline** en **active:** `0`.
""",
        "measure_id": "vergroenen_leefomgeving",
    },
    {
        "markdown": """
# Prijzen

Eenheidsprijzen per LDEN-band voor kostberekeningen in de simulator.

| Stock | Prijskolom | Bron |
|-------|------------|------|
| `bewoonde_geïsoleerde_woning` | `bewoonde_geïsoleerde_woning_prijs` | `gemiddelde_prijs_van_een_woning` |
| `bewoonde_niet_geïsoleerde_woning` | `bewoonde_niet_geïsoleerde_woning_prijs` | zelfde |
| `onbebouwde_bebouwbare_percelen` | `onbebouwde_bebouwbare_percelen_prijs` | `gemiddelde_prijs_bebouwbaar_perceel` |
""",
        "render_prijzen": True,
    },
    {
        "markdown": """
# Openstaande vragen

- Perceeltransacties: enkel `terrain_batissable` (bebouwbaar).
- Woonverdichtingsverboden: tijdelijk baseline én active op `0`; referentiemodel suggereert
  baseline **1%** — nog te koppelen aan data.
- Compensatiemaatregelen en soft measures (cohesie, vergroening) nog op 0.
- Kwetsbare groepen: aantal projecten bekend, wooneenheden per project nog niet.
- Onbebouwde onbebouwbare percelen in analyse 1 = 3× placeholder.
""",
    },
]


def render() -> None:
    st.title("Flow rates & prijzen per LDEN-band")
    st.caption("Aggregatie en flow-berekening op basis van `data_2/data_2.csv`")
    st.info(
        "Resultaten uit vooraf berekende data; deze pagina voert geen herberekening uit."
    )

    try:
        df_flows = load_flow_size()
        df_intersecties = load_intersecties()
    except FileNotFoundError as exc:
        missing = exc.args[0]
        if missing == _FLOW_SIZE_PATH:
            st.error(
                f"`{_FLOW_SIZE_PATH}` ontbreekt. Voer eerst `contour_analyse_2.py` uit."
            )
        else:
            st.error(
                f"`{_DATA_2_PATH}` ontbreekt. Voer eerst `contour_analyse_1.py` uit."
            )
        return

    st.caption(
        f"{df_flows.height} LDEN-banden · {df_flows.width} kolommen in flow_size.csv"
    )

    for section in FLOW_SECTIONS:
        st.markdown(section["markdown"])
        measure_id = section.get("measure_id")
        if measure_id:
            _flow_chart(df_flows, measure_id)
        if section.get("render_prijzen"):
            _render_prijzen(df_intersecties)
