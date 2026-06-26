"""Showcase: stocks & intersecties (output of contour_analyse_1.py)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import polars as pl
import streamlit as st

from contour_vlaanderen_grafieken import toon_staafdiagram_per_gewest

_DATA_2_PATH = Path("data_2/data_2.csv")
_GEWEST_VLAANDEREN = "Vlaams Gewest"
_GEWEST_BRUSSEL = "Brussels Hoofdstedelijk Gewest"


@st.cache_data
def load_data_2() -> pl.DataFrame:
    if not _DATA_2_PATH.is_file():
        raise FileNotFoundError(_DATA_2_PATH)
    return pl.read_csv(_DATA_2_PATH)


def _staaf(
    df: pl.DataFrame,
    kolom: str,
    *,
    titel: str,
    y_label: str,
    aggregatie: str = "som",
    gewicht_kolom: str | None = None,
    waarde_format: str = ",.0f",
) -> None:
    toon_staafdiagram_per_gewest(
        df,
        kolom,
        titel=titel,
        y_label=y_label,
        aggregatie=aggregatie,
        gewicht_kolom=gewicht_kolom,
        waarde_format=waarde_format,
        toon_kaart=False,
    )


def _gemiddelde_inwoners_per_woning(df: pl.DataFrame) -> float:
    vla = df.filter(pl.col("regio_nl") == _GEWEST_VLAANDEREN)
    totaal_inwoners = vla.select(pl.col("inwoners").sum()).item()
    totaal_woningen = vla.select(pl.col("aantal_woningen").sum()).item()
    return totaal_inwoners / totaal_woningen


def _render_inwoners_per_woning(df: pl.DataFrame) -> None:
    gemiddelde = _gemiddelde_inwoners_per_woning(df)
    st.write(
        f"Gemiddelde aantal inwoners per woning in Vlaams Gewest: **{gemiddelde:.2f}**"
    )


def _render_renovatie_ratio(df: pl.DataFrame) -> None:
    vla = df.filter(pl.col("regio_nl") == _GEWEST_VLAANDEREN)
    totaal_renovaties = vla.select(pl.col("aantal_vergunningen_renovatie").sum()).item()
    totaal_woningen = vla.select(pl.col("aantal_woningen").sum()).item()
    ratio = totaal_renovaties / totaal_woningen
    st.write(
        "Gemiddeld aantal vergunde renovaties per woning per jaar in Vlaanderen (contour): "
        f"**{ratio:.4f}** "
        f"({totaal_renovaties:,.1f} renovaties / {totaal_woningen:,.0f} woningen)"
    )


def _render_kwetsbare_ratio(df: pl.DataFrame) -> None:
    vla = df.filter(pl.col("regio_nl") == _GEWEST_VLAANDEREN)
    totaal_nieuwbouw = vla.select(pl.col("aantal_vergunningen_nieuwbouw").sum()).item()
    totaal_kwetsbaar = vla.select(
        pl.col("aantal_vergunningen_kwetsbare_groepen").sum()
    ).item()
    ratio = totaal_kwetsbaar / totaal_nieuwbouw
    st.write(
        f"Het totaal aantal nieuwbouwvergunningen per jaar in het Vlaams Gewest bedraagt "
        f"{totaal_nieuwbouw:,.0f}. "
        f"Het totaal aantal vergunningen voor kwetsbare groepen per jaar in het Vlaams Gewest "
        f"bedraagt {totaal_kwetsbaar:,.0f}. "
        f"De ratio kwetsbare groepen / nieuwbouw in Vlaanderen bedraagt **{ratio:.4f}**."
    )


def _render_perceel_transacties(df: pl.DataFrame) -> None:
    _staaf(
        df,
        "aantal_bebouwbare_perceel_transacties_per_jaar",
        titel="Aantal transacties — bebouwbare percelen",
        y_label="Aantal transacties",
    )
    _staaf(
        df,
        "gemiddelde_prijs_bebouwbaar_perceel",
        titel="Gemiddelde prijs — bebouwbare percelen",
        y_label="Gemiddelde prijs (€)",
        aggregatie="gemiddelde",
        gewicht_kolom="aantal_bebouwbare_perceel_transacties_per_jaar",
        waarde_format=",.0f",
    )


Section = dict[str, str | Callable[[pl.DataFrame], None] | None]

SECTIONS: list[Section] = [
    {
        "markdown": """
Volgende termen zijn belangrijk voor de analyse:

|Term|Definitie|
|----|---------|
|Contour| Decibelcontouren rond de luchthaven (1 dB-schaal).|
|Statistische sector| Regio's waarop statistische informatie normaal wordt geregistreerd.|
|Intersectie| Overlap van een contour en een statistische sector.|

Dit script bouwt variabele voor variabele een dataset op intersectieniveau op. Elke sectie
voegt kolommen toe aan `df`; het eindresultaat wordt weggeschreven naar `data_2/data_2.csv`
voor de flow-analyse in `contour_analyse_2.py`.
""",
    },
    {
        "markdown": """
## Basisdata

### Inwoners

#### Bron
- **Vlaanderen:** `inwoners_client` — adresniveau, toegekend aan overlap.
- **Brussel:** `inwoners_overlap` — sectorniveau, naar overlap gespreid op oppervlakte.
- **Overig (Waals Gewest):** `inwoners_overlap`.

#### Bewerkingen
1. Nieuwe kolom `inwoners` via `pl.when` op `regio_nl`.
2. Per gewest de meest geschikte bronkolom kiezen.

#### Visualisatie
Staafdiagram per LDEN-band, opgesplitst naar Vlaanderen vs. Brussel (som per band).
""",
        "render": lambda df: _staaf(
            df, "inwoners", titel="Inwoners per zone", y_label="Inwoners"
        ),
    },
    {
        "markdown": """
### Aantal inwoners per woning

#### Doel
Eén referentiewaarde voor Brussel, waar geen woningtelling op adresniveau beschikbaar is.

#### Bewerkingen
1. Filter op Vlaams Gewest; totaal inwoners en totaal woningen optellen.
2. Delen: `gemiddelde_inwoners_per_woning = totaal_inwoners / totaal_woningen`.

Dit gemiddelde wordt gebruikt om Brusselse woningen te schatten.
""",
        "render": _render_inwoners_per_woning,
    },
    {
        "markdown": """
### Aantal woningen

#### Bron
- **Vlaanderen:** bestaande kolom `aantal_woningen` (adresniveau).
- **Brussel:** afgeleid uit inwoners / gemiddelde inwoners per woning.

#### Visualisatie
Staafdiagram per LDEN-band en gewest.
""",
        "render": lambda df: _staaf(
            df,
            "aantal_woningen",
            titel="Aantal woningen per zone",
            y_label="Aantal woningen",
        ),
    },
    {
        "markdown": """
### Onbebouwde bebouwbare percelen

#### Bron
`aantal_percelen_onbebouwd_woongebied` — gemeten op adresniveau (Vlaanderen).

Kolom gekopieerd naar `onbebouwde_bebouwbare_percelen` zonder transformatie.
""",
        "render": lambda df: _staaf(
            df,
            "onbebouwde_bebouwbare_percelen",
            titel="Onbebouwde bebouwbare percelen",
            y_label="Aantal onbebouwde bebouwbare percelen",
        ),
    },
    {
        "markdown": """
### Onbebouwde onbebouwbare percelen

#### Bron
Geen directe meting — **placeholder**.

#### Bewerkingen
`onbebouwde_onbebouwbare_percelen = aantal_percelen_onbebouwd_woongebied × 3`.

Factor 3 is een tijdelijke schatting tot echte stockdata beschikbaar is.
""",
        "render": lambda df: _staaf(
            df,
            "onbebouwde_onbebouwbare_percelen",
            titel="Onbebouwde onbebouwbare percelen",
            y_label="Aantal onbebouwde onbebouwbare percelen",
        ),
    },
    {
        "markdown": """
### Bewoonde niet-geïsoleerde woning

#### Bron
Geen isolatieregister per woning — **gewestaannames** (placeholder).

- Vlaanderen: **80%** van `aantal_woningen`
- Brussel: **95%** (expert opinion)
""",
        "render": lambda df: _staaf(
            df,
            "bewoonde_niet_geïsoleerde_woning",
            titel="Bewoonde niet-geïsoleerde woningen per gewest",
            y_label="Bewoonde niet-geïsoleerde woningen",
        ),
    },
    {
        "markdown": """
### Bewoonde geïsoleerde woning

Complement van de verdeling hierboven: Vlaanderen **20%**, Brussel **5%**.
""",
        "render": lambda df: _staaf(
            df,
            "bewoonde_geïsoleerde_woning",
            titel="Bewoonde geïsoleerde woningen per gewest",
            y_label="Bewoonde geïsoleerde woningen",
        ),
    },
    {
        "markdown": """
### Woongebied-mutaties (onbebouwbaar ↔ bebouwbaar)

Jaarlijkse planologische verschuivingen tussen onbebouwbaar en bebouwbare percelen.

#### Bron
Excel met jaarlijks gemiddelde 2021–2026 per LDEN-band (Vlaanderen); proportioneel
verdeeld over intersecties op basis van `oppervlakte_overlap_m2`. Brussel = 0 mutaties.
""",
        "render": lambda df: (
            _staaf(
                df,
                "onbebouwbaar_naar_bebouwbaar",
                titel="Onbebouwbaar naar bebouwbaar",
                y_label="Aantal percelen",
            ),
            _staaf(
                df,
                "bebouwbaar_naar_onbebouwbaar",
                titel="Bebouwbaar naar onbebouwbaar",
                y_label="Aantal percelen",
            ),
        ),
    },
    {
        "markdown": """
### Totaal aantal transacties van woningen

Jaarlijks transactievolume en prijs per intersectie — input voor aankoopbeleid, voorkooprecht
en prijsanalyses. Transacties van woningen en appartementen geaggregeerd per sector en
proportioneel toegewezen aan intersecties (gewicht = `aantal_woningen`).
""",
        "render": lambda df: _staaf(
            df,
            "aantal_woning_transacties_per_jaar",
            titel="Aantal transacties per jaar",
            y_label="Aantal transacties",
        ),
    },
    {
        "markdown": """
### Aantal transacties niet-geïsoleerde en geïsoleerde woningen

Zelfde gewestaandelen als bewoonde stocks (80/20 Vlaanderen, 95/5 Brussel) toegepast op
totaal transacties per intersectie.
""",
        "render": lambda df: (
            _staaf(
                df,
                "aantal_transacties_niet_geïsoleerde_woningen",
                titel="Transacties niet-geïsoleerde woningen per jaar",
                y_label="Aantal transacties",
            ),
            _staaf(
                df,
                "aantal_transacties_geïsoleerde_woningen",
                titel="Transacties geïsoleerde woningen per jaar",
                y_label="Aantal transacties",
            ),
        ),
    },
    {
        "markdown": """
### Gemiddelde prijs van een woning

Transactiegewogen gemiddelde prijs per gewest en LDEN-band.
""",
        "render": lambda df: _staaf(
            df,
            "gemiddelde_prijs_van_een_woning",
            titel="Gemiddelde prijs van een woning",
            y_label="Gemiddelde prijs (€)",
            aggregatie="gemiddelde",
            gewicht_kolom="aantal_woning_transacties_per_jaar",
            waarde_format=",.0f",
        ),
    },
    {
        "markdown": """
### Totaal aantal transacties van percelen

Jaarlijks transactievolume en prijs voor onbebouwde **bebouwbare** percelen
(`terrain_batissable`). Proportioneel toegewezen met gewicht `onbebouwde_bebouwbare_percelen`.
""",
        "render": _render_perceel_transacties,
    },
    {
        "markdown": """
### Aantal vergunningen nieuwbouw

#### Bron
- **Vlaanderen:** omgevingsloket, handeling *Nieuwbouw*; toewijzing per gemeente met gewicht
  `onbebouwde_bebouwbare_percelen`.
- **Brussel:** gemiddelde groei geregistreerd woningbestand 2021–2025; toewijzing met gewicht
  `aantal_woningen`.
""",
        "render": lambda df: _staaf(
            df,
            "aantal_vergunningen_nieuwbouw",
            titel="Vergunde wooneenheden nieuwbouw per zone",
            y_label="Wooneenheden per jaar (gem.)",
        ),
    },
    {
        "markdown": """
### Jaarlijks aantal vergunningen voor renovatie

#### Bron
Omgevingsloket, handeling *Verbouwen of hergebruik* (Vlaanderen). Brussel: proxy via
Vlaamse renovatie/woning-ratio.
""",
        "render": lambda df: (
            _render_renovatie_ratio(df),
            _staaf(
                df,
                "aantal_vergunningen_renovatie",
                titel="Vergunde renovaties per zone per jaar",
                y_label="Wooneenheden per jaar (gem.)",
            ),
        ),
    },
    {
        "markdown": """
### Aantal vergunningen kwetsbare groepen

Vlaanderen: projecten per gemeente. Brussel: proxy via Vlaamse ratio kwetsbare groepen /
nieuwbouw.
""",
        "render": lambda df: (
            _render_kwetsbare_ratio(df),
            _staaf(
                df,
                "aantal_vergunningen_kwetsbare_groepen",
                titel="Vergunde projecten kwetsbare groepen per zone",
                y_label="Projecten per jaar (gem.)",
            ),
        ),
    },
    {
        "markdown": """
### Renovatie en isolatie

Placeholder-verdeling van renovatievergunningen:
- **20%** met akoestische isolatie (`jaarlijks_aantal_vergunningen_met_isolatie`)
- **80%** zonder (`jaarlijks_aantal_vergunningen_zonder_isolatie`)
""",
        "render": lambda df: (
            _staaf(
                df,
                "jaarlijks_aantal_vergunningen_met_isolatie",
                titel="Renovaties met akoestische isolatie per jaar",
                y_label="Renovaties met isolatie per jaar (gem.)",
            ),
            _staaf(
                df,
                "jaarlijks_aantal_vergunningen_zonder_isolatie",
                titel="Renovaties zonder akoestische isolatie per jaar",
                y_label="Renovaties zonder isolatie per jaar (gem.)",
            ),
        ),
    },
    {
        "markdown": """
## Export

Volledige dataset weggeschreven naar `data_2/data_2.csv` — input voor `contour_analyse_2.py`.

### Openstaande vragen

- Kwetsbare groepen: aantal **projecten** bekend, wooneenheden per project niet.
- Onbebouwde onbebouwbare percelen = 3× placeholder.
- Nieuwbouw in Brussel via woningbestand-groei; in Vlaanderen via woongebied-percelen.
- Perceeltransacties: enkel `terrain_batissable` (bebouwbaar).
""",
    },
]


def render() -> None:
    st.title("Data analyse contour Vlaanderen")
    st.caption("Sector–contour-overlappen rond de luchthaven (LDEN, Vlaanderen + Brussel)")
    st.info(
        "Resultaten uit vooraf berekende data; deze pagina voert geen herberekening uit."
    )

    try:
        df = load_data_2()
    except FileNotFoundError:
        st.error(
            f"`{_DATA_2_PATH}` ontbreekt. Voer eerst `contour_analyse_1.py` uit om de "
            "intersectiedata te genereren."
        )
        return

    st.caption(f"{df.height:,} rijen · {df.width} kolommen")

    for section in SECTIONS:
        st.markdown(section["markdown"])
        render_fn = section.get("render")
        if callable(render_fn):
            render_fn(df)
