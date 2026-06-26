import polars as pl
import streamlit as st

from contour_vlaanderen_grafieken import (
    toon_flow_rate_staafdiagram,
    toon_staafdiagram_per_gewest,
)

# uv run streamlit run contour_analyse_2.py --server.port 8502
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
]

df = (
    df_intersecties.group_by("db_lden")
    .agg(
        *[pl.col(kolom).sum() for kolom in _DB_SOM_KOLOMMEN],
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

Er zijn 27 flows in het huidige dashboard (24/06/2026). Per flow bepalen we een **flow rate**
in de toestand **baseline** (zonder maatregel) en **active** (maatregel aan). Een flow rate is
steeds een jaarlijks aandeel: hoeveel van de **noemer-stock** per jaar door de maatregel wordt
beïnvloed (teller / noemer, uitgedrukt als percentage in de grafiek).

|flow|baseline berekend? | active berekend |
|---|---|---|
|verkavelingsverbod| x|x  |
|woongebiedverbod|x|x|
|aankoopbeleid_percelen| x| placeholder |
|voorkooprecht_percelen|x | placeholder |
|onteigening_percelen|x |  x|
|verbod_kleine_woning|placeholder |placeholder  |
|verbod_grote_woning|placeholder |placeholder  |
|verbod_kwetsbare_groep|x | x |
|woonverdichtingsverbod_niet_geïsoleerde_woningen| placeholder |placeholder  |
|woonverdichtingsverbod_geïsoleerde_woningen|placeholder |placeholder  |
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
|compensatie_buitenzone|x | x |
|compensatie_verhuis|x | x |
|versterken_sociale_cohesie|x | x |
|vergroenen_leefomgeving|x | x |

### Overzicht placeholders

Onderstaande aannames zijn **geen gemeten data**; ze dienen om flows te kunnen berekenen zolang
brondata ontbreekt. Vervang ze zodra betere cijfers beschikbaar zijn.

| # | Waarde | Gebruikt in | Toelichting |
|---|--------|-------------|-------------|
| 1 | **25%** van bebouwbare perceeltransacties | `aankoopbeleid_percelen` (active), `aankoopbeleid_*_woningen` (active) | Perceel-flows gebruiken echte perceeltransacties; woningflows blijven op woningtransacties. |
| 2 | **50%** van bebouwbare perceeltransacties | `voorkooprecht_percelen` (active), `voorkooprecht_*_woningen` (active) | Zelfde bron als aankoopbeleid percelen, hoger aandeel (expertenschatting). |
| 3 | **5%** vaste flow rate (`0,05`) | `onteigening_percelen`, `onteigening_*_woningen` (active) | Jaarlijks aandeel onteigeningen; niet uit transactiedata afgeleid. |
| 4 | **97%** van nieuwbouwvergunningen | `verbod_kleine_woning` (baseline) | Geen MER-plichtsplitsing per project → 97% van nieuwbouw telt als “kleine woning”. |
| 5 | **3%** van nieuwbouwvergunningen | `verbod_grote_woning` (baseline) | Complement van rij 4 (97% + 3% = 100%). |
| 6 | **50%** vaste rate | `isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning` (baseline) | Aandeel nieuwbouw dat zonder strengere norm naar niet-geïsoleerde stock zou gaan. |
| 7 | **50%** baseline, **100%** active | `isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning` | Bij active gaat volledige nieuwbouw naar geïsoleerde stock (placeholder). |
| 8 | **20%** van renovatievergunningen | `renovatie_zonder_maatregel` (active) | Geschat aandeel renovaties met akoestische isolatie zonder extra maatregel. |
| 9 | **80%** van renovatievergunningen | `verplicht_isoleren_renovatie` (active) | Geschat aandeel renovaties dat wél (verplicht) isoleert. |
| 10 | **×2** renovatierate | `gesubsidieerd_isolatieprogramma` (active) | Subsidie verdubbelt isolatiebereidheid t.o.v. basisrenovatiestroom. |
| 11 | **×4** renovatierate | `gestuurd_isolatieprogramma` (active) | Gestuurd programma: vier keer zoveel isolatie als zonder programma. |
| 12 | **0** (tijdelijk) | `woonverdichtingsverbod_niet_geïsoleerde_woningen` (baseline + active) | Beide op `0` tot woonverdichtingsdruk per band is becijferd. In het referentiemodel (`contour/flows_per_contour.py`) is baseline **1%** (`0,01`) per jaar op de niet-geïsoleerde stock; active = `0`. |
| 13 | **0** (tijdelijk) | `woonverdichtingsverbod_geïsoleerde_woningen` (baseline + active) | Zelfde tijdelijke invulling als rij 12, maar op `bewoonde_geïsoleerde_woning` als noemer-stock. |

**Input-placeholders uit analyse 1** (beïnvloeden meerdere flows): `onbebouwde_onbebouwbare_percelen`
= 3× bebouwbare percelen; isolatieverdeling woningen 80/20 (Vlaanderen) en 95/5 (Brussel);
transacties per isolatietype via dezelfde verdeling; `nieuwe_woning` en overheidseigendom = 0.

Alle berekeningen hieronder gebruiken `df` (één rij per `db_lden`). Eerst worden tellers en
noemers per band opgeteld; daarna wordt de flow rate als teller/noemer berekend. De grafiek
toont die kolommen rechtstreeks (geen tweede aggregatie).

Het resultaat wordt weggeschreven naar `input/flow_size.csv` voor gebruik in de simulator.
"""

flow_rules = pl.read_csv("input/flow_rules.csv")
df_flows = df
"""
## verkavelings_verbod

Verkavelingsverbod: beperkt de verdichting op onbebouwde bebouwbare percelen.

**Baseline:** `0` — nog niet gekoppeld aan brondata; geen gemeten verkavelingsdruk in de contour.

**Active:** `0` — maatregel nog niet uitgewerkt; placeholder tot vergunningen- of planologische
data beschikbaar zijn.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("verkavelings_verbod_baseline"),
    pl.lit(0).alias("verkavelings_verbod_active"),
)
toon_flow_rate_staafdiagram(df_flows, "verkavelings_verbod")
"""
## Woongebiedverbod

Transfer van `onbebouwde_onbebouwbare_percelen` naar `onbebouwde_bebouwbare_percelen` (netto
woongebied-aanduiding) of omgekeerd bij schrapping. Bron: gemiddelde jaarlijkse mutaties
2021–2026 (Vlaanderen), verdeeld over intersecties in analyse 1; Brussel = 0 mutaties.

**Baseline:** huidige netto woongebied-creatie per jaar, als aandeel van de stock onbebouwbare
percelen in de band:

    (onbebouwbaar_naar_bebouwbaar − bebouwbaar_naar_onbebouwbaar) / onbebouwde_onbebouwbare_percelen

Vertaalt: “welk deel van de onbebouwbare stock wordt jaarlijks netto bebouwbaar gemaakt?”

**Active:** bij een woongebiedverbod tellen we enkel nog **schrapping** (bebouwbaar → onbebouwbaar):

    bebouwbaar_naar_onbebouwbaar / onbebouwde_onbebouwbare_percelen

Nieuwe woongebied-aanduiding wordt gestopt (netto creatie = 0 onder de maatregel).

Als de noemer 0 is → flow rate 0. Resultaat wordt begrensd tot maximaal 100%.
"""

df_flows = df_flows.with_columns(
    pl.when(pl.col("onbebouwde_onbebouwbare_percelen") > 0)
    .then(
        (
            pl.col("onbebouwbaar_naar_bebouwbaar")
            - pl.col("bebouwbaar_naar_onbebouwbaar")
        )
        / pl.col("onbebouwde_onbebouwbare_percelen")
    )
    .otherwise(0.0)
    .clip(upper_bound=1.0)
    .alias("woongebiedverbod_baseline"),
    pl.when(pl.col("onbebouwde_onbebouwbare_percelen") > 0)
    .then(
        pl.col("bebouwbaar_naar_onbebouwbaar")
        / pl.col("onbebouwde_onbebouwbare_percelen")
    )
    .otherwise(0.0)
    .clip(upper_bound=1.0)
    .alias("woongebiedverbod_active"),
)
toon_flow_rate_staafdiagram(df_flows, "woongebiedverbod")
"""
## aankoopbeleid_percelen

Overheid koopt onbebouwde bebouwbare percelen aan (stock → `perceel_eigendom_overheid`).

**Baseline:** `0` — zonder aankoopbeleid vloeien geen percelen naar overheidseigendom.

**Active (placeholder):** 25% van het jaarlijkse transactievolume op bebouwbare percelen, per
stock onbebouwde bebouwbare percelen in de band:

    0,25 × aantal_bebouwbare_perceel_transacties_per_jaar / onbebouwde_bebouwbare_percelen

Noemer = stock onbebouwde bebouwbare percelen; teller = geschat aantal perceelaankopen per jaar.
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
## voorkooprecht_percelen

Gemeente/regio oefent voorkooprecht uit op onbebouwde bebouwbare percelen.

**Baseline:** `0` — zonder voorkooprecht geen overdracht naar overheid via dit instrument.

**Active (placeholder):** 50% van het transactievolume op bebouwbare percelen als proxy voor
percelen die onder voorkooprecht zouden vallen:

    0,5 × aantal_bebouwbare_perceel_transacties_per_jaar / onbebouwde_bebouwbare_percelen

Zelfde bron als aankoopbeleid percelen, maar met hoger aandeel (50% i.p.v. 25%).
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
## onteigening_percelen

Gedwongen onteigening van onbebouwde bebouwbare percelen.

**Baseline:** `0` — geen structurele onteigening in de referentiesituatie.

**Active (placeholder):** vaste jaarlijkse flow rate van **5%** (`0,05`) voor elke band —
onafhankelijk van lokale transacties of stockgrootte. Te verfijnen wanneer beleidsdata
beschikbaar zijn.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("onteigening_percelen_baseline"),
    pl.lit(0.05).alias("onteigening_percelen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "onteigening_percelen")
"""
## verbod_kleine_woning

Beperking op kleine woningen bij nieuwbouw op bebouwbare percelen.

**Baseline (placeholder):** 97% van de nieuwbouwvergunningen per band, gedeeld door het
aantal onbebouwde bebouwbare percelen — als proxy voor het aandeel nieuwbouw dat onder een
“kleine woning” valt (geen MER-splitsing in de data):

    0,97 × aantal_vergunningen_nieuwbouw / onbebouwde_bebouwbare_percelen

**Active:** `0` — het verbod stopt de stroom kleine woningen; in deze versie nog niet
ingevuld met een positieve alternatieve flow.
"""
df_flows = df_flows.with_columns(
    (
        0.97
        * (
            pl.col("aantal_vergunningen_nieuwbouw")
            / pl.col("onbebouwde_bebouwbare_percelen")
        )
    ).alias("verbod_kleine_woning_baseline"),
    pl.lit(0).alias("verbod_kleine_woning_active"),
)
toon_flow_rate_staafdiagram(df_flows, "verbod_kleine_woning")

"""
## verbod_grote_woning

Beperking op grote woningen bij nieuwbouw (complement van verbod kleine woning).

**Baseline (placeholder):** 3% van de nieuwbouwvergunningen per band, per bebouwbare perceel:

    0,03 × aantal_vergunningen_nieuwbouw / onbebouwde_bebouwbare_percelen

**Active:** `0` — onder het verbod verdwijnt deze stroom (nog niet vervangen door andere flow).
"""
df_flows = df_flows.with_columns(
    (
        0.03
        * (
            pl.col("aantal_vergunningen_nieuwbouw")
            / pl.col("onbebouwde_bebouwbare_percelen")
        )
    ).alias("verbod_grote_woning_baseline"),
    pl.lit(0).alias("verbod_grote_woning_active"),
)
toon_flow_rate_staafdiagram(df_flows, "verbod_grote_woning")

"""
## verbod_kwetsbare_groep

Nieuwbouw voor kwetsbare groepen op bebouwbare percelen.

**Baseline:** gemeten verhouding kwetsbare-groepenvergunningen tot bebouwbare percelen in de
band (data uit analyse 1, Vlaanderen + Brusselse proxy):

    aantal_vergunningen_kwetsbare_groepen / onbebouwde_bebouwbare_percelen

**Active:** `0` — het verbod zet deze nieuwbouwstroom uit.
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
## woonverdichtingsverbod_niet_geïsoleerde_woningen

Beperkt jaarlijkse groei (woonverdichting) van niet-geïsoleerde bewoonde woningen. Noemer-stock:
`bewoonde_niet_geïsoleerde_woning`.

**Baseline (placeholder):** `0` — tijdelijk geen gemeten verdedigingsdruk in de contour. Ter
referentie gebruikt het dashboard-referentiemodel **1%** jaarlijkse groei (`0,01`) op deze stock.

**Active (placeholder):** `0` — onder het verbod stopt de verdichtingsstroom volledig (nog niet
gekoppeld aan lokale transacties of vergunningen).
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("woonverdichtingsverbod_niet_geïsoleerde_woningen_baseline"),
    pl.lit(0).alias("woonverdichtingsverbod_niet_geïsoleerde_woningen_active"),
)

"""
## woonverdichtingsverbod_geïsoleerde_woningen

Beperkt jaarlijkse groei van geïsoleerde bewoonde woningen. Noemer-stock:
`bewoonde_geïsoleerde_woning`.

**Baseline (placeholder):** `0` — zelfde tijdelijke invulling als bij niet-geïsoleerde woningen;
referentiemodel: **1%** (`0,01`) per jaar.

**Active (placeholder):** `0` — verbod zet verdichting op geïsoleerde stock uit.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("woonverdichtingsverbod_geïsoleerde_woningen_baseline"),
    pl.lit(0).alias("woonverdichtingsverbod_geïsoleerde_woningen_active"),
)

"""
## aankoopbeleid_niet_geïsoleerde_woningen

Overheid koopt niet-geïsoleerde bewoonde woningen aan.

**Baseline:** `0` — geen aankoopbeleid op woningen.

**Active (placeholder):** 25% van het geschatte transactievolume voor niet-geïsoleerde woningen,
per niet-geïsoleerde stock in de band:

    0,25 × aantal_transacties_niet_geïsoleerde_woningen / bewoonde_niet_geïsoleerde_woning

De transacties per isolatietype komen uit analyse 1 (80/20- of 95/5-verdeling per gewest).
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
"""
## aankoopbeleid_geïsoleerde_woningen

Overheid koopt geïsoleerde bewoonde woningen aan.

**Baseline:** `0`

**Active (placeholder):** 25% van transacties geïsoleerde woningen, per geïsoleerde stock:

    0,25 × aantal_transacties_geïsoleerde_woningen / bewoonde_geïsoleerde_woning
"""
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
## voorkooprecht_niet_geïsoleerde_woningen

Voorkooprecht op niet-geïsoleerde bewoonde woningen.

**Baseline:** `0` — zonder voorkooprecht geen overdracht naar overheid.

**Active (placeholder):** 50% van transacties niet-geïsoleerde woningen, per niet-geïsoleerde stock:

    0,5 × aantal_transacties_niet_geïsoleerde_woningen / bewoonde_niet_geïsoleerde_woning

Zelfde patroon als `aankoopbeleid_niet_geïsoleerde_woningen`, maar met factor 50% i.p.v. 25%.
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
"""
## voorkooprecht_geïsoleerde_woningen

Voorkooprecht op geïsoleerde bewoonde woningen.

**Baseline:** `0`

**Active (placeholder):** 50% van transacties geïsoleerde woningen, per geïsoleerde stock:

    0,5 × aantal_transacties_geïsoleerde_woningen / bewoonde_geïsoleerde_woning
"""
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
## onteigening_niet_geïsoleerde_woningen

Gedwongen onteigening van niet-geïsoleerde bewoonde woningen.

**Baseline:** `0`

**Active (placeholder):** vaste rate **5%** per band (`0,05`), onafhankelijk van stock of
transacties.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("onteigening_niet_geïsoleerde_woningen_baseline"),
    pl.lit(0.05).alias("onteigening_niet_geïsoleerde_woningen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "onteigening_niet_geïsoleerde_woningen")

"""
## onteigening_geïsoleerde_woningen

Gedwongen onteigening van geïsoleerde bewoonde woningen.

**Baseline:** `0`

**Active (placeholder):** vaste rate **5%** per band (`0,05`).
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("onteigening_geïsoleerde_woningen_baseline"),
    pl.lit(0.05).alias("onteigening_geïsoleerde_woningen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "onteigening_geïsoleerde_woningen")
"""
## isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning

Waar nieuwbouw naartoe stroomt: van `nieuwe_woning` naar niet-geïsoleerde bewoonde stock.

**Baseline (placeholder):** vaste rate **50%** (`0,50`) — helft van nieuwbouw zou zonder
strengere norm naar niet-geïsoleerde woningen gaan.

**Active:** `0` — strengere voorschriften stoppen deze stroom (alles moet geïsoleerd worden).
"""
df_flows = df_flows.with_columns(
    pl.lit(0.50).alias(
        "isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning_baseline"
    ),
    pl.lit(0).alias(
        "isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning_active"
    ),
)
toon_flow_rate_staafdiagram(
    df_flows, "isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning"
)
"""
## isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning

Nieuwbouw die direct in de geïsoleerde bewoonde stock landt.

**Baseline (placeholder):** vaste rate **50%** (`0,50`).

**Active (placeholder):** vaste rate **100%** (`1,0`) — alle nieuwbouw moet aan
isolatienormen voldoen en in geïsoleerde stock terechtkomen.
"""
df_flows = df_flows.with_columns(
    pl.lit(0.5).alias(
        "isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning_baseline"
    ),
    pl.lit(1).alias("isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning_active"),
)
toon_flow_rate_staafdiagram(
    df_flows, "isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning"
)
"""
## renovatie_zonder_maatregel

Spontane renovatie met akoestische isolatie (niet-geïsoleerd → geïsoleerd), zonder beleidsmaatregel.

**Baseline:** `0` — in het dashboard staat renovatie zonder maatregel uit in baseline; de
“natuurlijke” isolatierate zit in de active-schatting hieronder.

**Active (placeholder):** 20% van renovatievergunningen per niet-geïsoleerde woning in de band:

    0,20 × aantal_vergunningen_renovatie / bewoonde_niet_geïsoleerde_woning
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("renovatie_zonder_maatregel_baseline"),
    (
        pl.col("aantal_vergunningen_renovatie")
        / pl.col("bewoonde_niet_geïsoleerde_woning")
        * 0.2
    ).alias("renovatie_zonder_maatregel_active"),
)
toon_flow_rate_staafdiagram(df_flows, "renovatie_zonder_maatregel")
"""
## verplicht_isoleren_renovatie

Verplichte akoestische isolatie bij ingrijpende renovatie.

**Baseline:** `0` — geen verplichting in referentiesituatie.

**Active (placeholder):** 80% van renovatievergunningen leidt tot isolatie, per
niet-geïsoleerde stock:

    0,80 × aantal_vergunningen_renovatie / bewoonde_niet_geïsoleerde_woning

Schatting: de meeste renovaties worden nog uitgevoerd, maar dan mét isolatie.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("verplicht_isoleren_renovatie_baseline"),
    (
        pl.col("aantal_vergunningen_renovatie")
        / pl.col("bewoonde_niet_geïsoleerde_woning")
        * 0.8
    ).alias("verplicht_isoleren_renovatie_active"),
)
toon_flow_rate_staafdiagram(df_flows, "verplicht_isoleren_renovatie")
"""
## gesubsidieerd_isolatieprogramma

Subsidie stimuleert vrijwillige isolatie bij renovatie.

**Baseline:** `0`

**Active (placeholder):** isolatierate = **2×** de renovatiestroom per niet-geïsoleerde woning:

    2 × aantal_vergunningen_renovatie / bewoonde_niet_geïsoleerde_woning
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
## gestuurd_isolatieprogramma

Actief gestuurd isolatieprogramma (hogere intensiteit dan subsidie).

**Baseline:** `0`

**Active (placeholder):** isolatierate = **4×** de renovatiestroom:

    4 × aantal_vergunningen_renovatie / bewoonde_niet_geïsoleerde_woning
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("gestuurd_isolatieprogramma_baseline"),
    (
        pl.col("aantal_vergunningen_renovatie")
        / pl.col("bewoonde_niet_geïsoleerde_woning")
        * 4
    ).alias("gestuurd_isolatieprogramma_active"),
)
toon_flow_rate_staafdiagram(df_flows, "gestuurd_isolatieprogramma")

"""
## aanleg_geluidsbuffers

Investering in geluidsbuffers; effect op stocks nog niet gekwantificeerd.

**Baseline:** `0` — placeholder.

**Active:** `0` — placeholder tot effect op woning-/perceelstocks is gemodelleerd.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("aanleg_geluidsbuffers_baseline"),
    pl.lit(0).alias("aanleg_geluidsbuffers_active"),
)
toon_flow_rate_staafdiagram(df_flows, "aanleg_geluidsbuffers")

"""
## compensatie_buitenzone

Compensatie door verplaatsing naar buiten de contourzone. **Nog niet uitgewerkt.**

**Baseline:** `0` — placeholder.

**Active:** `0` — placeholder.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("compensatie_buitenzone_baseline"),
    pl.lit(0).alias("compensatie_buitenzone_active"),
)
toon_flow_rate_staafdiagram(df_flows, "compensatie_buitenzone")

"""
## compensatie_verhuis

Compensatie via verhuis binnen/buiten de contour. **Nog niet uitgewerkt.**

**Baseline:** `0` — placeholder.

**Active:** `0` — placeholder.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("compensatie_verhuis_baseline"),
    pl.lit(0).alias("compensatie_verhuis_active"),
)
toon_flow_rate_staafdiagram(df_flows, "compensatie_verhuis")

"""
## versterken_sociale_cohesie

Maatregel rond sociale cohesie; geen kwantitatieve flow in deze analyse.

**Baseline:** `0` — placeholder.

**Active:** `0` — placeholder.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("versterken_sociale_cohesie_baseline"),
    pl.lit(0).alias("versterken_sociale_cohesie_active"),
)
toon_flow_rate_staafdiagram(df_flows, "versterken_sociale_cohesie")

"""
## vergroenen_leefomgeving

Maatregel rond vergroening; geen kwantitatieve flow in deze analyse.

**Baseline:** `0` — placeholder.

**Active:** `0` — placeholder.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("vergroenen_leefomgeving_baseline"),
    pl.lit(0).alias("vergroenen_leefomgeving_active"),
)
toon_flow_rate_staafdiagram(df_flows, "vergroenen_leefomgeving")

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
- Woonverdichtingsverboden: tijdelijk baseline én active op `0`; referentiemodel suggereert baseline **1%** — nog te koppelen aan data.
- Compensatiemaatregelen en soft measures (cohesie, vergroening) nog op 0.
- Kwetsbare groepen: aantal projecten bekend, wooneenheden per project nog niet.
- Onbebouwde onbebouwbare percelen in analyse 1 = 3× placeholder.
"""
