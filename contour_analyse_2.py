import polars as pl
import streamlit as st

from contour_vlaanderen_grafieken import (
    toon_flow_rate_staafdiagram,
    toon_staafdiagram_per_gewest,
)

# uv run streamlit run contour_analyse_2.py --server.port 8502

st.set_page_config(page_title="Contour analyse 2 — flows", layout="wide")
with st.sidebar:
    TOON_MAATREGEL_HELP = st.toggle(
        "Toon maatregel-uitleg",
        value=False,
        help="Toont of verbergt de narratieve helptekst (uit measures.csv) onder elke maatregel-titel.",
    )

_df_measures_help = pl.read_csv("input/measures.csv")
_MAATREGEL_HELP: dict[str, str] = {
    str(row["measure_id"]): str(row["help"])
    for row in _df_measures_help.select("measure_id", "help").iter_rows(named=True)
}


def toon_maatregel_info(*measure_ids: str) -> None:
    """Toon narratieve UI-help uit measures.csv als st.info (indien toggle aan)."""
    if not TOON_MAATREGEL_HELP:
        return
    for measure_id in measure_ids:
        help_text = _MAATREGEL_HELP.get(measure_id, "").strip()
        if help_text:
            st.info(help_text)


df_intersecties = pl.read_csv("data_2/data_2.csv")

"""
# Aggregatie per LDEN-band

`data_2.csv` heeft één rij per **intersectie** (statistische sector × LDEN-band). Voor flow rates
werken we op **contourniveau**: alle intersecties met dezelfde `db_lden` worden samengevoegd.

Telbare grootheden (stocks, transacties, vergunningen, woongebied-mutaties, …) worden **opgeteld**.
Transacties zijn opgesplitst in `aantal_transacties_niet_geïsoleerde_woningen` en
`aantal_transacties_geïsoleerde_woningen` (berekend in analyse 1, zelfde gewestelijke
80/20- en 95/5-verdeling als de bewoonde stocks).
Daarna berekenen we flow rates als teller / noemer op die geaggregeerde rij.

`df_intersecties` blijft beschikbaar voor kaarten op intersectieniveau; `df` is één rij per band.
"""
_DB_SOM_KOLOMMEN = [
    "oppervlakte_overlap_m2",
    "inwoners_overlap",
    "inwoners",
    "onbebouwde_bebouwbare_percelen",
    "onbebouwde_onbebouwbare_percelen",
    "bewoonde_niet_geïsoleerde_woning",
    "bewoonde_geïsoleerde_woning",
    "nieuwe_woning",
    "perceel_eigendom_overheid",
    "woning_eigendom_overheid",
    "onbebouwbaar_naar_bebouwbaar",
    "bebouwbaar_naar_onbebouwbaar",
    "aantal_woning_transacties_per_jaar",
    "aantal_transacties_niet_geïsoleerde_woningen",
    "aantal_transacties_geïsoleerde_woningen",
    "aantal_bebouwbare_perceel_transacties_per_jaar",
    "aantal_vergunningen_nieuwbouw",
    "aantal_vergunningen_renovatie",
    "aantal_vergunningen_kwetsbare_groepen",
    "jaarlijks_aantal_vergunningen_met_isolatie",
    "jaarlijks_aantal_vergunningen_zonder_isolatie",
    "aantal_vergunningen_sloop",
    "aantal_nieuwe_percelen_verkaveling",
]

df = (
    df_intersecties.group_by("db_lden")
    .agg(
        *[pl.col(kolom).sum() for kolom in _DB_SOM_KOLOMMEN],
        pl.col("inwoners_lnight45").sum().alias("inwoners_lnight45"),
        pl.col("inwoners_na70").sum().alias("inwoners_na70"),
        pl.col("oppervlakte_lnight45_m2").sum().alias("oppervlakte_lnight45_m2"),
        pl.col("oppervlakte_na70_m2").sum().alias("oppervlakte_na70_m2"),
        (
            pl.col("gemiddelde_prijs_van_een_woning")
            * pl.col("aantal_woning_transacties_per_jaar")
        )
        .sum()
        .alias("_prijs_woning_gewogen"),
        (
            pl.col("gemiddelde_prijs_bebouwbaar_perceel")
            * pl.col("aantal_bebouwbare_perceel_transacties_per_jaar")
        )
        .sum()
        .alias("_prijs_bebouwbaar_gewogen"),
    )
    .with_columns(
        pl.when(pl.col("aantal_woning_transacties_per_jaar") > 0)
        .then(
            pl.col("_prijs_woning_gewogen")
            / pl.col("aantal_woning_transacties_per_jaar")
        )
        .otherwise(0.0)
        .alias("gemiddelde_prijs_van_een_woning"),
        pl.when(pl.col("aantal_bebouwbare_perceel_transacties_per_jaar") > 0)
        .then(
            pl.col("_prijs_bebouwbaar_gewogen")
            / pl.col("aantal_bebouwbare_perceel_transacties_per_jaar")
        )
        .otherwise(0.0)
        .alias("gemiddelde_prijs_bebouwbaar_perceel"),
        pl.when(pl.col("inwoners") > 0)
        .then(pl.col("inwoners_lnight45") / pl.col("inwoners"))
        .when(pl.col("oppervlakte_overlap_m2") > 0)
        .then(pl.col("oppervlakte_lnight45_m2") / pl.col("oppervlakte_overlap_m2"))
        .otherwise(0.0)
        .alias("share_lnight45"),
        pl.when(pl.col("inwoners") > 0)
        .then(pl.col("inwoners_na70") / pl.col("inwoners"))
        .when(pl.col("oppervlakte_overlap_m2") > 0)
        .then(pl.col("oppervlakte_na70_m2") / pl.col("oppervlakte_overlap_m2"))
        .otherwise(0.0)
        .alias("share_na70"),
    )
    .drop("_prijs_woning_gewogen", "_prijs_bebouwbaar_gewogen")
    .sort("db_lden")
)

"""
# Stocks

Deze werden in `contour_analyse_1.py` berekend en worden hier overgenomen via `df_intersecties`
(voor eventuele kaarten op intersectieniveau). In de flow-berekeningen gebruiken we de
geaggregeerde `df` per LDEN-band.

| Stock | Bron / opmerking |
|-------|------------------|
| `onbebouwde_bebouwbare_percelen` | Gemeten (adresniveau Vlaanderen) |
| `onbebouwde_onbebouwbare_percelen` | **Placeholder:** 3× bebouwbare percelen |
| `bewoonde_niet_geïsoleerde_woning` | **Placeholder:** 80% (VL) / 95% (BXL) van woningen |
| `bewoonde_geïsoleerde_woning` | **Placeholder:** 20% (VL) / 5% (BXL) van woningen |
| `nieuwe_woning` | Simulator-tussenstock; hier steeds 0 |
| `perceel_eigendom_overheid` | Interne variabele; steeds 0 |
| `woning_eigendom_overheid` | Interne variabele; steeds 0 |
"""
df_stocks = df_intersecties.select(
    [
        "id_inter_ss_lden",
        "geometrie_inter_ss_lden",
        "nis_sector",
        "geometrie_sector",
        "naam_sector_nl",
        "nis_gemeente",
        "naam_gemeente_nl",
        "nis_arrondissement",
        "naam_arrondissement_nl",
        "nis_provincie",
        "naam_provincie_nl",
        "nis_regio",
        "regio_nl",
        "oppervlakte_sector_m2",
        "db_lden",
        "oppervlakte_overlap_m2",
        "aandeel_sector_in_contour",
        "pct_lnight45",
        "pct_na70",
        "oppervlakte_lnight45_m2",
        "oppervlakte_na70_m2",
        "inwoners",
        "inwoners_lnight45",
        "inwoners_na70",
        "onbebouwde_bebouwbare_percelen",  # stock 1
        "onbebouwde_onbebouwbare_percelen",  # stock 2
        "bewoonde_niet_geïsoleerde_woning",  # stock 3
        "bewoonde_geïsoleerde_woning",  # stock 4
        "nieuwe_woning",  # stock 5
        "perceel_eigendom_overheid",  # stock 6
        "woning_eigendom_overheid",  # stock 7
    ]
)
df_stocks.write_csv("input/stocks.csv")
"""
# Flows

Er zijn 25 flows in het huidige dashboard (29/07/2026). Per flow bepalen we een **flow rate**
in de toestand **baseline** (zonder maatregel) en **active** (maatregel aan). Een flow rate is
steeds een jaarlijks aandeel: hoeveel van de **noemer-stock** per jaar door de maatregel wordt
beïnvloed (teller / noemer, uitgedrukt als percentage in de grafiek).

|flow|baseline berekend? | active berekend |
|---|---|---|
|slopen_niet_geïsoleerde_woningen| x (altijd actief) | — (0) |
|slopen_geïsoleerde_woningen| x (altijd actief) | — (0) |
|verkavelingsverbod| x |x  |
|natuurlijke_woongebied_schrapping| x (altijd actief) | — (0) |
|woongebiedverbod|x|x|
|aankoopbeleid_percelen| x| placeholder |
|voorkooprecht_percelen|x | placeholder |
|onteigening_percelen|x |  x|
|woningverbod|x | x |
|verbod_kwetsbare_groep|x | x |
|woonverdichtingsverbod_niet_geïsoleerde_woningen|x | x |
|woonverdichtingsverbod_geïsoleerde_woningen|x | x |
|aankoopbeleid_niet_geïsoleerde_woningen|x | x |
|aankoopbeleid_geïsoleerde_woningen|x | x |
|voorkooprecht_niet_geïsoleerde_woningen|x | x |
|voorkooprecht_geïsoleerde_woningen|x | x |
|onteigening_niet_geïsoleerde_woningen|x | x |
|onteigening_geïsoleerde_woningen|x | x |
|isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning|placeholder |placeholder  |
|isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning|placeholder |placeholder  |
|renovatie_zonder_maatregel| x| placeholder |
|verplicht_isoleren_renovatie| x| placeholder |
|gesubsidieerd_isolatieprogramma| placeholder |placeholder  |
|gestuurd_isolatieprogramma| placeholder |placeholder  |
|aanleg_geluidsbuffers|placeholder |placeholder  |

### Overzicht placeholders

Onderstaande aannames zijn **geen gemeten data**; ze dienen om flows te kunnen berekenen zolang
brondata ontbreekt. Vervang ze zodra betere cijfers beschikbaar zijn.

| # | Waarde | Gebruikt in | Toelichting |
|---|--------|-------------|-------------|
| 1 | **25%** van bebouwbare perceeltransacties | `aankoopbeleid_percelen` (active), `aankoopbeleid_*_woningen` (active) | Perceel-flows gebruiken echte perceeltransacties; woningflows blijven op woningtransacties. |
| 2 | **50%** van bebouwbare perceeltransacties | `voorkooprecht_percelen` (active), `voorkooprecht_*_woningen` (active) | Zelfde bron als aankoopbeleid percelen, hoger aandeel (expertenschatting). |
| 3 | **100%** vaste flow rate (`1,00`) | `onteigening_percelen`, `onteigening_*_woningen` (active) | Jaarlijks aandeel onteigeningen; niet uit transactiedata afgeleid. |
| 4 | **50%** (`>55 dB`); **0%** (`≤55 dB`) | `isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning` (baseline) | Boven 55 dB: helft van nieuwbouw naar niet-geïsoleerd. ≤55 dB: moderne isolatie ⇒ alles akoestisch geïsoleerd (`0`). |
| 5 | **100%** baseline én active; sequentieel op rest | `isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning` | Baseline `1,00` van de **resterende** `nieuwe_woning` na de niet-geïsoleerde flow (niet `0,50`: anders blijft 25% over). ≤55 dB: baseline/active beide `1,00` en niet-flow `0`. |
| 6 | **20%** (`>55 dB`); **100%** (`≤55 dB`) van renovatievergunningen | `renovatie_zonder_maatregel` (active) | ≤55 dB: elke renovatie levert akoestische isolatie (moderne standaard). |
| 7 | **80%** (`>55 dB`); **100%** (`≤55 dB`) van renovatievergunningen | `verplicht_isoleren_renovatie` (active) | ≤55 dB: verplicht = 100% van renovaties. |
| 8 | **×2** renovatierate | `gesubsidieerd_isolatieprogramma` (active) | Subsidie verdubbelt isolatiebereidheid t.o.v. basisrenovatiestroom. |
| 9 | **100%** vaste flow rate (`1,00`) | `gestuurd_isolatieprogramma` (active) | Alle niet-geïsoleerde woningen (niet enkel renovatie); jaarlijks aandeel van de hele stock. |
| 10 | **25%** van gesloopte gebouwen had woonfunctie | `slopen_*_woningen` (baseline) | Sloopvergunningen registreren gebouwen, niet woonfunctie. Placeholder tot woonfunctie-uitsplitsing beschikbaar is. |
| 11 | **5 percelen** per verkavelingsproject | `verkavelingsverbod` (baseline) | Aantal nieuwe percelen per verkavelingsproject niet beschikbaar in brondata. Factor 5 is een ruwe schatting. Zie `contour_analyse_1.py`. |

**Input-placeholders uit analyse 1** (beïnvloeden meerdere flows): `onbebouwde_onbebouwbare_percelen`
= 3× bebouwbare percelen; isolatieverdeling woningen 80/20 (Vlaanderen) en 95/5 (Brussel);
transacties per isolatietype via dezelfde verdeling; `nieuwe_woning` en overheidseigendom = 0;
sloop in Brussel via Vlaamse ratio sloop/woning; verkaveling in Brussel = 0.

Alle berekeningen hieronder gebruiken `df` (één rij per `db_lden`). Eerst worden tellers en
noemers per band opgeteld; daarna wordt de flow rate als teller/noemer berekend. De grafiek
toont die kolommen rechtstreeks (geen tweede aggregatie).

Het resultaat wordt weggeschreven naar `input/flow_size.csv` voor gebruik in de simulator.
"""

flow_rules = pl.read_csv("input/flow_rules.csv")
df_flows = df
"""
## Slopen (niet-geïsoleerd / geïsoleerd)
"""
toon_maatregel_info(
    "slopen_niet_geïsoleerde_woningen",
    "slopen_geïsoleerde_woningen",
)
"""
Naast nieuwbouw verdwijnen er jaarlijks ook gebouwen door sloop. De sloopvergunningen uit het
omgevingsloket registreren het **aantal gesloopte gebouwen** (metriek *Aantal gebouwen*), maar
bevatten **geen woonfunctie-aanduiding** en **geen isolatiestatus**. Niet elk gesloopt gebouw
was een woning.

#### Flows

- `slopen_niet_geïsoleerde_woningen` — `transfer` —
  `bewoonde_niet_geïsoleerde_woning` → `onbebouwde_bebouwbare_percelen`
- `slopen_geïsoleerde_woningen` — `transfer` —
  `bewoonde_geïsoleerde_woning` → `onbebouwde_bebouwbare_percelen`

Beide flows gebruiken dezelfde rate (isolatie-aandelen heffen op).

#### Placeholder

**25% van de gesloopte gebouwen had een woonfunctie** (`_AANDEEL_SLOOP_WOONFUNCTIE = 0,25`).
Ruwe schatting tot de sloopdata een woonfunctie-kolom bevatten.

#### Formule

    baseline = (aantal_vergunningen_sloop × 0,25)
             / (bewoonde_niet_geïsoleerde_woning + bewoonde_geïsoleerde_woning)
    active   = 0

#### Baseline vs. active

- **Baseline:** natuurlijke jaarlijkse sloopstroom — altijd toegepast (geen beleidskeuze).
- **Active:** `0` — sloop staat niet als UI-maatregel aan/uit; `hidden_in_ui=True`.

#### Visualisatie

Twee staafdiagrammen per LDEN-band.
"""
_AANDEEL_SLOOP_WOONFUNCTIE = 0.25

_sloop_rate = (
    pl.when(
        (pl.col("bewoonde_niet_geïsoleerde_woning") + pl.col("bewoonde_geïsoleerde_woning"))
        > 0
    )
    .then(
        pl.col("aantal_vergunningen_sloop")
        * _AANDEEL_SLOOP_WOONFUNCTIE
        / (
            pl.col("bewoonde_niet_geïsoleerde_woning")
            + pl.col("bewoonde_geïsoleerde_woning")
        )
    )
    .otherwise(0.0)
)

df_flows = df_flows.with_columns(
    _sloop_rate.alias("slopen_niet_geïsoleerde_woningen_baseline"),
    pl.lit(0.0).alias("slopen_niet_geïsoleerde_woningen_active"),
    _sloop_rate.alias("slopen_geïsoleerde_woningen_baseline"),
    pl.lit(0.0).alias("slopen_geïsoleerde_woningen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "slopen_niet_geïsoleerde_woningen")
toon_flow_rate_staafdiagram(df_flows, "slopen_geïsoleerde_woningen")

"""
## Verkavelingsverbod
"""
toon_maatregel_info("verkavelingsverbod")
"""
Een verkavelingsvergunning splitst een bestaand perceel op in meerdere kleinere percelen. Dat
vergroot `onbebouwde_bebouwbare_percelen` en daarmee het potentieel voor nieuwe woningen in de
geluidszone. Een **verkavelingsverbod** blokkeert die opsplitsing.

#### Flows

- `verkavelingsverbod` — `growth` op `onbebouwde_bebouwbare_percelen`
  (zelfde stock in/uit: stock += rate × stock)

#### Bron

`aantal_nieuwe_percelen_verkaveling` — berekend in `contour_analyse_1.py`:
- **Vlaanderen:** gemiddeld aantal verkavelingsprojecten/jaar (2021–2025) uit
  `vergunningen_verkaveling_2026_lang.csv`, handeling `-` (pure verkaveling zonder sloop).
- **Placeholder:** 5 nieuwe percelen per project (geen brondata per project).
- **Brussel:** 0.

#### Formule

    baseline = aantal_nieuwe_percelen_verkaveling / onbebouwde_bebouwbare_percelen
    active   = 0

#### Baseline vs. active

- **Baseline:** historische verkavelingsdruk zonder verbod (aandeel groei van de perceelstock).
- **Active:** `0` — het verbod stopt de instroom van nieuwe percelen volledig.

#### Visualisatie

Staafdiagram per LDEN-band: baseline vs. active.
"""
df_flows = df_flows.with_columns(
    pl.when(pl.col("onbebouwde_bebouwbare_percelen") > 0)
    .then(
        pl.col("aantal_nieuwe_percelen_verkaveling")
        / pl.col("onbebouwde_bebouwbare_percelen")
    )
    .otherwise(0.0)
    .alias("verkavelings_verbod_baseline"),
    pl.lit(0.0).alias("verkavelings_verbod_active"),
)
toon_flow_rate_staafdiagram(df_flows, "verkavelings_verbod")
"""
## Natuurlijke woongebied-schrapping
"""
toon_maatregel_info("natuurlijke_woongebied_schrapping")
"""
Jaarlijks wordt een deel van het bestaand woongebied **geschrapt** (bebouwbaar → onbebouwbaar).
Dit is een natuurlijke uitstroom in de referentiesituatie — geen beleidsmaatregel.

#### Flows

- `natuurlijke_woongebied_schrapping` — `transfer` —
  `onbebouwde_bebouwbare_percelen` → `onbebouwde_onbebouwbare_percelen`

#### Bron

`bebouwbaar_naar_onbebouwbaar` — gemiddelde jaarlijkse mutaties 2021–2026 (Vlaanderen),
verdeeld over intersecties in `contour_analyse_1.py`; Brussel = 0.

#### Formule

    baseline = bebouwbaar_naar_onbebouwbaar / onbebouwde_bebouwbare_percelen
    active   = 0

#### Baseline vs. active

- **Baseline:** natuurlijke schrapping — altijd toegepast.
- **Active:** `0` — niet via UI; `hidden_in_ui=True`.

#### Visualisatie

Staafdiagram per LDEN-band.
"""
df_flows = df_flows.with_columns(
    pl.when(pl.col("onbebouwde_bebouwbare_percelen") > 0)
    .then(
        pl.col("bebouwbaar_naar_onbebouwbaar")
        / pl.col("onbebouwde_bebouwbare_percelen")
    )
    .otherwise(0.0)
    .clip(upper_bound=1.0)
    .alias("natuurlijke_woongebied_schrapping_baseline"),
    pl.lit(0.0).alias("natuurlijke_woongebied_schrapping_active"),
)
toon_flow_rate_staafdiagram(df_flows, "natuurlijke_woongebied_schrapping")

"""
## Woongebiedverbod
"""
toon_maatregel_info("woongebiedverbod")
"""
Verbod op het **bijmaken** van nieuw woongebied. Zonder verbod worden jaarlijks onbebouwbare
percelen bebouwbaar gemaakt; met verbod stopt die creatie. De omgekeerde richting (schrapping)
zit in `natuurlijke_woongebied_schrapping`.

#### Flows

- `woongebiedverbod` — `transfer` —
  `onbebouwde_onbebouwbare_percelen` → `onbebouwde_bebouwbare_percelen`

#### Bron

`onbebouwbaar_naar_bebouwbaar` — gemiddelde jaarlijkse mutaties 2021–2026 (Vlaanderen);
Brussel = 0.

#### Formule

    baseline = onbebouwbaar_naar_bebouwbaar / onbebouwde_onbebouwbare_percelen
    active   = 0

(Noemer 0 → rate 0; resultaat begrensd tot max. 100%.)

#### Baseline vs. active

- **Baseline:** historische creatie van nieuw woongebied zonder verbod.
- **Active:** `0` — het verbod stopt nieuwe aanduiding volledig.

#### Visualisatie

Staafdiagram per LDEN-band.
"""
df_flows = df_flows.with_columns(
    pl.when(pl.col("onbebouwde_onbebouwbare_percelen") > 0)
    .then(
        pl.col("onbebouwbaar_naar_bebouwbaar")
        / pl.col("onbebouwde_onbebouwbare_percelen")
    )
    .otherwise(0.0)
    .clip(upper_bound=1.0)
    .alias("woongebiedverbod_baseline"),
    pl.lit(0.0).alias("woongebiedverbod_active"),
)
toon_flow_rate_staafdiagram(df_flows, "woongebiedverbod")
"""
## Aankoopbeleid percelen
"""
toon_maatregel_info("aankoopbeleid_percelen")
"""
Overheid koopt onbebouwde bebouwbare percelen aan om bebouwing in de geluidszone te vermijden.

#### Flows

- `aankoopbeleid_percelen` — `transfer` —
  `onbebouwde_bebouwbare_percelen` → `perceel_eigendom_overheid`

#### Placeholder

**25%** van het jaarlijkse bebouwbare-perceeltransactievolume.

#### Formule

    baseline = 0
    active   = 0,25 × aantal_bebouwbare_perceel_transacties_per_jaar
                     / onbebouwde_bebouwbare_percelen

#### Baseline vs. active

- **Baseline:** `0` — zonder aankoopbeleid geen overdracht naar overheid.
- **Active:** geschatte aankoopintensiteit wanneer het beleid aanstaat.

#### Visualisatie

Staafdiagram per LDEN-band.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("aankoopbeleid_percelen_baseline"),
    (
        pl.col("aantal_bebouwbare_perceel_transacties_per_jaar")
        * pl.lit(0.25)
        / pl.col("onbebouwde_bebouwbare_percelen")
    ).alias("aankoopbeleid_percelen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "aankoopbeleid_percelen")
"""
## Voorkooprecht percelen
"""
toon_maatregel_info("voorkooprecht_percelen")
"""
Gemeente/regio oefent voorkooprecht uit op onbebouwde bebouwbare percelen.

#### Flows

- `voorkooprecht_percelen` — `transfer` —
  `onbebouwde_bebouwbare_percelen` → `perceel_eigendom_overheid`

#### Placeholder

**50%** van het bebouwbare-perceeltransactievolume (hoger aandeel dan aankoopbeleid).

#### Formule

    baseline = 0
    active   = 0,5 × aantal_bebouwbare_perceel_transacties_per_jaar
                    / onbebouwde_bebouwbare_percelen

#### Baseline vs. active

- **Baseline:** `0` — zonder voorkooprecht geen overdracht via dit instrument.
- **Active:** geschatte intensiteit wanneer voorkooprecht actief is.

#### Visualisatie

Staafdiagram per LDEN-band.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("voorkooprecht_percelen_baseline"),
    (
        pl.col("aantal_bebouwbare_perceel_transacties_per_jaar")
        * pl.lit(0.5)
        / pl.col("onbebouwde_bebouwbare_percelen")
    ).alias("voorkooprecht_percelen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "voorkooprecht_percelen")

"""
## Onteigening percelen
"""
toon_maatregel_info("onteigening_percelen")
"""
Gedwongen onteigening van onbebouwde bebouwbare percelen.

#### Flows

- `onteigening_percelen` — `transfer` —
  `onbebouwde_bebouwbare_percelen` → `perceel_eigendom_overheid`

#### Placeholder

Vaste jaarlijkse rate **100%** (`1,00`), onafhankelijk van lokale transacties.

#### Formule

    baseline = 0
    active   = 1,00

#### Baseline vs. active

- **Baseline:** `0` — geen structurele onteigening in de referentiesituatie.
- **Active:** volledige jaarlijkse onteigeningsrate wanneer het instrument aanstaat.

#### Visualisatie

Staafdiagram per LDEN-band.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("onteigening_percelen_baseline"),
    pl.lit(1.0).alias("onteigening_percelen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "onteigening_percelen")
"""
## Woningverbod
"""
toon_maatregel_info("woningverbod")
"""
Verbod op het bouwen van nieuwe woningen op onbebouwde (bebouwbare) percelen. De rate is
**gedeeld** met woonverdichtingsverbod (zie hieronder), zodat bands met weinig percelen geen
opgeblazen rate krijgen.

#### Flows

- `woningverbod` — `transfer` —
  `onbebouwde_bebouwbare_percelen` → `nieuwe_woning`
  (absolute transfer ≈ rate × percelen)

#### Formule

    rate = aantal_vergunningen_nieuwbouw
         / (bewoonde_niet_geïsoleerde_woning
            + bewoonde_geïsoleerde_woning
            + onbebouwde_bebouwbare_percelen)
    baseline = rate
    active   = 0

Samen met verdichting (`rate × woningen`) benadert dit het aantal nieuwbouwvergunningen.

#### Baseline vs. active

- **Baseline:** historische nieuwbouw op onbebouwde percelen zonder verbod.
- **Active:** `0` — het verbod stopt die nieuwbouwstroom volledig.

#### Visualisatie

Staafdiagram per LDEN-band.
"""
_nieuwbouw_noemer = (
    pl.col("bewoonde_niet_geïsoleerde_woning")
    + pl.col("bewoonde_geïsoleerde_woning")
    + pl.col("onbebouwde_bebouwbare_percelen")
)
_nieuwbouw_rate = (
    pl.when(_nieuwbouw_noemer > 0)
    .then(pl.col("aantal_vergunningen_nieuwbouw") / _nieuwbouw_noemer)
    .otherwise(0.0)
)
df_flows = df_flows.with_columns(
    _nieuwbouw_rate.alias("woningverbod_baseline"),
    pl.lit(0.0).alias("woningverbod_active"),
)
toon_flow_rate_staafdiagram(df_flows, "woningverbod")

"""
## Verbod kwetsbare groepen
"""
toon_maatregel_info("verbod_kwetsbare_groep")
"""
Verbod op nieuwbouw voor kwetsbare groepen (bv. scholen) op bebouwbare percelen.

#### Flows

- `verbod_kwetsbare_groep` — `transfer` —
  `onbebouwde_bebouwbare_percelen` → `nieuwe_woning`

#### Bron

`aantal_vergunningen_kwetsbare_groepen` — analyse 1 (Vlaanderen + Brusselse proxy).

#### Formule

    baseline = aantal_vergunningen_kwetsbare_groepen / onbebouwde_bebouwbare_percelen
    active   = 0

#### Baseline vs. active

- **Baseline:** historische nieuwbouwstroom voor kwetsbare functies zonder verbod.
- **Active:** `0` — het verbod zet die stroom uit.

#### Visualisatie

Staafdiagram per LDEN-band.
"""
df_flows = df_flows.with_columns(
    (
        pl.col("aantal_vergunningen_kwetsbare_groepen")
        / pl.col("onbebouwde_bebouwbare_percelen")
    ).alias("verbod_kwetsbare_groep_baseline"),
    pl.lit(0).alias("verbod_kwetsbare_groep_active"),
)
toon_flow_rate_staafdiagram(df_flows, "verbod_kwetsbare_groep")
"""
## Woonverdichtingsverbod (niet-geïsoleerd / geïsoleerd)
"""
toon_maatregel_info(
    "woonverdichtingsverbod_niet_geïsoleerde_woningen",
    "woonverdichtingsverbod_geïsoleerde_woningen",
)
"""
Beperkt jaarlijkse groei door woonverdichting op bestaande woningen. Zelfde **gedeelde
nieuwbouwrate** als `woningverbod` (zie hierboven).

#### Flows

- `woonverdichtingsverbod_niet_geïsoleerde_woningen` — `growth` op
  `bewoonde_niet_geïsoleerde_woning` (stock += rate × stock)
- `woonverdichtingsverbod_geïsoleerde_woningen` — `growth` op
  `bewoonde_geïsoleerde_woning` (stock += rate × stock)

Beide flows hebben identieke baseline/active-waarden.

#### Formule

    rate = aantal_vergunningen_nieuwbouw
         / (bewoonde_niet_geïsoleerde_woning
            + bewoonde_geïsoleerde_woning
            + onbebouwde_bebouwbare_percelen)
    baseline = rate
    active   = 0

#### Baseline vs. active

- **Baseline:** historische verdichtingsdruk zonder verbod.
- **Active:** `0` — het verbod stopt verdichting op de betreffende woningstock.

#### Visualisatie

Twee staafdiagrammen per LDEN-band.
"""
df_flows = df_flows.with_columns(
    _nieuwbouw_rate.alias("woonverdichtingsverbod_niet_geïsoleerde_woningen_baseline"),
    pl.lit(0.0).alias("woonverdichtingsverbod_niet_geïsoleerde_woningen_active"),
)
toon_flow_rate_staafdiagram(
    df_flows, "woonverdichtingsverbod_niet_geïsoleerde_woningen"
)

df_flows = df_flows.with_columns(
    _nieuwbouw_rate.alias("woonverdichtingsverbod_geïsoleerde_woningen_baseline"),
    pl.lit(0.0).alias("woonverdichtingsverbod_geïsoleerde_woningen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "woonverdichtingsverbod_geïsoleerde_woningen")

"""
## Aankoopbeleid woningen (niet-geïsoleerd / geïsoleerd)
"""
toon_maatregel_info(
    "aankoopbeleid_niet_geïsoleerde_woningen",
    "aankoopbeleid_geïsoleerde_woningen",
)
"""
Overheid koopt bewoonde woningen aan om bewoning in de geluidszone te verminderen.
Opgesplitst naar isolatiestatus; zelfde placeholder-factor (25% van transacties).

#### Flows

- `aankoopbeleid_niet_geïsoleerde_woningen` — `transfer` —
  `bewoonde_niet_geïsoleerde_woning` → `woning_eigendom_overheid`
- `aankoopbeleid_geïsoleerde_woningen` — `transfer` —
  `bewoonde_geïsoleerde_woning` → `woning_eigendom_overheid`

#### Placeholder

**25%** van het geschatte transactievolume per isolatietype (analyse 1: 80/20 of 95/5).

#### Formule

    baseline = 0
    active_niet = 0,25 × aantal_transacties_niet_geïsoleerde_woningen
                        / bewoonde_niet_geïsoleerde_woning
    active_geo  = 0,25 × aantal_transacties_geïsoleerde_woningen
                        / bewoonde_geïsoleerde_woning

#### Baseline vs. active

- **Baseline:** `0` — zonder aankoopbeleid geen overdracht naar overheid.
- **Active:** geschatte aankoopintensiteit per isolatietype wanneer het beleid aanstaat.

#### Visualisatie

Twee staafdiagrammen per LDEN-band.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("aankoopbeleid_niet_geïsoleerde_woningen_baseline"),
    (
        (
            pl.col("aantal_transacties_niet_geïsoleerde_woningen")
            / pl.col("bewoonde_niet_geïsoleerde_woning")
        )
        * pl.lit(0.25)
    ).alias("aankoopbeleid_niet_geïsoleerde_woningen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "aankoopbeleid_niet_geïsoleerde_woningen")
df_flows = df_flows.with_columns(
    pl.lit(0).alias("aankoopbeleid_geïsoleerde_woningen_baseline"),
    (
        (
            pl.col("aantal_transacties_geïsoleerde_woningen")
            / pl.col("bewoonde_geïsoleerde_woning")
        )
        * pl.lit(0.25)
    ).alias("aankoopbeleid_geïsoleerde_woningen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "aankoopbeleid_geïsoleerde_woningen")

"""
## Voorkooprecht woningen (niet-geïsoleerd / geïsoleerd)
"""
toon_maatregel_info(
    "voorkooprecht_niet_geïsoleerde_woningen",
    "voorkooprecht_geïsoleerde_woningen",
)
"""
Voorkooprecht op bewoonde woningen. Zelfde patroon als aankoopbeleid woningen, met hogere
intensiteit (50% van transacties).

#### Flows

- `voorkooprecht_niet_geïsoleerde_woningen` — `transfer` —
  `bewoonde_niet_geïsoleerde_woning` → `woning_eigendom_overheid`
- `voorkooprecht_geïsoleerde_woningen` — `transfer` —
  `bewoonde_geïsoleerde_woning` → `woning_eigendom_overheid`

#### Placeholder

**50%** van het transactievolume per isolatietype.

#### Formule

    baseline = 0
    active_niet = 0,5 × aantal_transacties_niet_geïsoleerde_woningen
                       / bewoonde_niet_geïsoleerde_woning
    active_geo  = 0,5 × aantal_transacties_geïsoleerde_woningen
                       / bewoonde_geïsoleerde_woning

#### Baseline vs. active

- **Baseline:** `0` — zonder voorkooprecht geen overdracht via dit instrument.
- **Active:** geschatte intensiteit per isolatietype wanneer voorkooprecht actief is.

#### Visualisatie

Twee staafdiagrammen per LDEN-band.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("voorkooprecht_niet_geïsoleerde_woningen_baseline"),
    (
        (
            pl.col("aantal_transacties_niet_geïsoleerde_woningen")
            / pl.col("bewoonde_niet_geïsoleerde_woning")
        )
        * pl.lit(0.5)
    ).alias("voorkooprecht_niet_geïsoleerde_woningen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "voorkooprecht_niet_geïsoleerde_woningen")
df_flows = df_flows.with_columns(
    pl.lit(0).alias("voorkooprecht_geïsoleerde_woningen_baseline"),
    (
        (
            pl.col("aantal_transacties_geïsoleerde_woningen")
            / pl.col("bewoonde_geïsoleerde_woning")
        )
        * pl.lit(0.5)
    ).alias("voorkooprecht_geïsoleerde_woningen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "voorkooprecht_geïsoleerde_woningen")
"""
## Onteigening woningen (niet-geïsoleerd / geïsoleerd)
"""
toon_maatregel_info(
    "onteigening_niet_geïsoleerde_woningen",
    "onteigening_geïsoleerde_woningen",
)
"""
Gedwongen onteigening van bewoonde woningen, parallel voor beide isolatietypes.

#### Flows

- `onteigening_niet_geïsoleerde_woningen` — `transfer` —
  `bewoonde_niet_geïsoleerde_woning` → `woning_eigendom_overheid`
- `onteigening_geïsoleerde_woningen` — `transfer` —
  `bewoonde_geïsoleerde_woning` → `woning_eigendom_overheid`

#### Placeholder

Vaste rate **100%** (`1,00`) per band, voor beide flows.

#### Formule

    baseline = 0
    active   = 1,00   (beide isolatietypes)

#### Baseline vs. active

- **Baseline:** `0` — geen structurele onteigening van woningen in de referentiesituatie.
- **Active:** volledige jaarlijkse onteigeningsrate wanneer het instrument aanstaat.

#### Visualisatie

Twee staafdiagrammen per LDEN-band.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("onteigening_niet_geïsoleerde_woningen_baseline"),
    pl.lit(1.0).alias("onteigening_niet_geïsoleerde_woningen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "onteigening_niet_geïsoleerde_woningen")

df_flows = df_flows.with_columns(
    pl.lit(0).alias("onteigening_geïsoleerde_woningen_baseline"),
    pl.lit(1.0).alias("onteigening_geïsoleerde_woningen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "onteigening_geïsoleerde_woningen")
"""
## Isolatievoorschriften nieuwbouw (niet-geïsoleerd / geïsoleerd)
"""
toon_maatregel_info(
    "isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning",
    "isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning",
)
"""
Bepaalt waar nieuwbouw naartoe stroomt vanuit `nieuwe_woning`.

**Belangrijk — sequentiële rates:** de engine past eerst de niet-geïsoleerde flow toe, daarna
de geïsoleerde flow op de **resterende** `nieuwe_woning`. Daarom is baseline naar geïsoleerd
`1,00` (van de rest), niet `0,50`: anders blijft 25% van nieuwbouw ongeplaatst.

**≤55 dB:** moderne bouw is standaard akoestisch geïsoleerd → alle nieuwbouw naar geïsoleerd
(niet-flow = 0), ongeacht of de maatregel aanstaat.

#### Flows

- `isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning` — `transfer` —
  `nieuwe_woning` → `bewoonde_niet_geïsoleerde_woning`
- `isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning` — `transfer` —
  `nieuwe_woning` → `bewoonde_geïsoleerde_woning`

#### Formule (`db_lden > 55`)

    # naar niet-geïsoleerd
    baseline = 0,50
    active   = 0

    # naar geïsoleerd (op rest na vorige flow)
    baseline = 1,00
    active   = 1,00

#### Formule (`db_lden ≤ 55`)

    # naar niet-geïsoleerd
    baseline = 0
    active   = 0

    # naar geïsoleerd
    baseline = 1,00
    active   = 1,00

#### Baseline vs. active

- **Baseline (>55):** 50/50-splitsing zonder strengere norm; `nieuwe_woning` wordt leeggemaakt.
- **Active (>55):** stroom naar niet-geïsoleerd stopt; alle rest naar geïsoleerd.
- **≤55:** altijd volledig geïsoleerd (maatregel aan/uit maakt geen verschil).

#### Visualisatie

Twee staafdiagrammen per LDEN-band.
"""
_le55 = pl.col("db_lden") <= 55
df_flows = df_flows.with_columns(
    pl.when(_le55)
    .then(0.0)
    .otherwise(0.50)
    .alias("isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning_baseline"),
    pl.lit(0.0).alias(
        "isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning_active"
    ),
)
toon_flow_rate_staafdiagram(
    df_flows, "isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning"
)
df_flows = df_flows.with_columns(
    pl.lit(1.0).alias(
        "isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning_baseline"
    ),
    pl.lit(1.0).alias(
        "isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning_active"
    ),
)
toon_flow_rate_staafdiagram(
    df_flows, "isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning"
)
"""
## Renovatie zonder maatregel
"""
toon_maatregel_info("renovatie_zonder_maatregel")
"""
Spontane renovatie met akoestische isolatie (niet-geïsoleerd → geïsoleerd), zonder extra
beleidsmaatregel.

#### Flows

- `renovatie_zonder_maatregel` — `transfer` —
  `bewoonde_niet_geïsoleerde_woning` → `bewoonde_geïsoleerde_woning`

#### Placeholder

- **`db_lden > 55`:** **20%** van renovatievergunningen leidt tot akoestische isolatie.
- **`db_lden ≤ 55`:** **100%** — moderne renovatie isoleert standaard ook akoestisch.

#### Formule

    baseline = 0
    active   = factor × aantal_vergunningen_renovatie / bewoonde_niet_geïsoleerde_woning
    # factor = 1,00 als db_lden ≤ 55, anders 0,20

#### Baseline vs. active

- **Baseline:** `0` — in dit model staat de “natuurlijke” renovatiestroom in active
  (dashboard-keuze; zie ook `hidden_in_ui` / uitzonderingslogica in `flow_rules`).
- **Active:** geschatte spontane isolatierate wanneer deze referentiestroom actief is.

#### Visualisatie

Staafdiagram per LDEN-band.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("renovatie_zonder_maatregel_baseline"),
    (
        pl.col("aantal_vergunningen_renovatie")
        / pl.col("bewoonde_niet_geïsoleerde_woning")
        * pl.when(_le55).then(1.0).otherwise(0.2)
    ).alias("renovatie_zonder_maatregel_active"),
)
toon_flow_rate_staafdiagram(df_flows, "renovatie_zonder_maatregel")
"""
## Verplicht isoleren bij renovatie
"""
toon_maatregel_info("verplicht_isoleren_renovatie")
"""
Verplichte akoestische isolatie bij ingrijpende renovatie.

#### Flows

- `verplicht_isoleren_renovatie` — `transfer` —
  `bewoonde_niet_geïsoleerde_woning` → `bewoonde_geïsoleerde_woning`

#### Placeholder

- **`db_lden > 55`:** **80%** van renovatievergunningen leidt tot isolatie.
- **`db_lden ≤ 55`:** **100%** van renovatievergunningen.

#### Formule

    baseline = 0
    active   = factor × aantal_vergunningen_renovatie / bewoonde_niet_geïsoleerde_woning
    # factor = 1,00 als db_lden ≤ 55, anders 0,80

#### Baseline vs. active

- **Baseline:** `0` — geen isolatieplicht in de referentiesituatie.
- **Active:** geschatte isolatie-intensiteit wanneer de verplichting geldt.

#### Visualisatie

Staafdiagram per LDEN-band.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("verplicht_isoleren_renovatie_baseline"),
    (
        pl.col("aantal_vergunningen_renovatie")
        / pl.col("bewoonde_niet_geïsoleerde_woning")
        * pl.when(_le55).then(1.0).otherwise(0.8)
    ).alias("verplicht_isoleren_renovatie_active"),
)
toon_flow_rate_staafdiagram(df_flows, "verplicht_isoleren_renovatie")
"""
## Gesubsidieerd isolatieprogramma
"""
toon_maatregel_info("gesubsidieerd_isolatieprogramma")
"""
Subsidie stimuleert vrijwillige isolatie bij renovatie (hogere intensiteit dan spontane renovatie).

#### Flows

- `gesubsidieerd_isolatieprogramma` — `transfer` —
  `bewoonde_niet_geïsoleerde_woning` → `bewoonde_geïsoleerde_woning`

#### Placeholder

Isolatierate = **2×** de renovatiestroom.

#### Formule

    baseline = 0
    active   = 2 × aantal_vergunningen_renovatie / bewoonde_niet_geïsoleerde_woning

#### Baseline vs. active

- **Baseline:** `0` — geen subsidieprogramma in de referentiesituatie.
- **Active:** verdubbelde isolatiebereidheid wanneer het programma loopt.

#### Visualisatie

Staafdiagram per LDEN-band.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("gesubsidieerd_isolatieprogramma_baseline"),
    (
        pl.col("aantal_vergunningen_renovatie")
        / pl.col("bewoonde_niet_geïsoleerde_woning")
        * 2
    ).alias("gesubsidieerd_isolatieprogramma_active"),
)
toon_flow_rate_staafdiagram(df_flows, "gesubsidieerd_isolatieprogramma")

"""
## Gestuurd isolatieprogramma
"""
toon_maatregel_info("gestuurd_isolatieprogramma")
"""
Gestuurd isolatieprogramma: niet alleen verplicht voor wie renoveert, maar voor **iedereen**
met een niet-geïsoleerde woning.

#### Flows

- `gestuurd_isolatieprogramma` — `transfer` —
  `bewoonde_niet_geïsoleerde_woning` → `bewoonde_geïsoleerde_woning`

#### Placeholder

Vaste jaarlijkse flow rate **100%** (`1,00`) van de niet-geïsoleerde woningstock —
onafhankelijk van renovatievergunningen.

#### Formule

    baseline = 0
    active   = 1,00

#### Baseline vs. active

- **Baseline:** `0` — geen gestuurd programma in de referentiesituatie.
- **Active:** volledige niet-geïsoleerde stock per jaar naar geïsoleerd (engine clippt op
  beschikbare stock).

#### Visualisatie

Staafdiagram per LDEN-band.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("gestuurd_isolatieprogramma_baseline"),
    pl.lit(1.0).alias("gestuurd_isolatieprogramma_active"),
)
toon_flow_rate_staafdiagram(df_flows, "gestuurd_isolatieprogramma")

"""
## Aanleg geluidsbuffers
"""
toon_maatregel_info("aanleg_geluidsbuffers")
"""
Investering in geluidsbuffers; effect op stocks is nog niet gekwantificeerd.

#### Flows

- `aanleg_geluidsbuffers` — nog geen stock-effect gemodelleerd

#### Placeholder

Beide rates tijdelijk `0`.

#### Formule

    baseline = 0
    active   = 0

#### Baseline vs. active

- **Baseline:** `0` — geen gemodelleerd effect zonder maatregel.
- **Active:** `0` — placeholder tot het effect op woning-/perceelstocks is uitgewerkt.

#### Visualisatie

Staafdiagram per LDEN-band (nu leeg / nul).
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("aanleg_geluidsbuffers_baseline"),
    pl.lit(0).alias("aanleg_geluidsbuffers_active"),
)
toon_flow_rate_staafdiagram(df_flows, "aanleg_geluidsbuffers")

df_flows.write_csv("input/flow_size.csv")

"""
# Prijzen

Eenheidsprijzen per LDEN-band voor kostberekeningen in de simulator.

| Stock | Prijskolom | Bron |
|-------|------------|------|
| `bewoonde_geïsoleerde_woning` | `bewoonde_geïsoleerde_woning_prijs` | `gemiddelde_prijs_van_een_woning` |
| `bewoonde_niet_geïsoleerde_woning` | `bewoonde_niet_geïsoleerde_woning_prijs` | zelfde (geen aparte isolatieprijs) |
| `onbebouwde_bebouwbare_percelen` | `onbebouwde_bebouwbare_percelen_prijs` | `gemiddelde_prijs_bebouwbaar_perceel` |

#### Visualisatie
Staafdiagrammen per gewest en LDEN-band (zonder kaart).
"""
df_prices = df.with_columns(
    bewoonde_geïsoleerde_woning_prijs=pl.col("gemiddelde_prijs_van_een_woning"),
    bewoonde_niet_geïsoleerde_woning_prijs=pl.col("gemiddelde_prijs_van_een_woning"),
    onbebouwde_bebouwbare_percelen_prijs=pl.col("gemiddelde_prijs_bebouwbaar_perceel"),
)

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
df_prices.write_csv("input/stock_prices.csv")

"""
# Openstaande vragen

- Perceeltransacties: enkel `terrain_batissable` (bebouwbaar).
- Compensatiemaatregelen en soft measures verwijderd; geluidsbuffers-kost nog open.
- Kwetsbare groepen: aantal projecten bekend, wooneenheden per project nog niet.
- Onbebouwde onbebouwbare percelen in analyse 1 = 3× placeholder.
"""
