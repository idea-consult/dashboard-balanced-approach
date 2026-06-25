import polars as pl
import streamlit as st

from contour_vlaanderen_grafieken import toon_flow_rate_staafdiagram

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
        .alias("_prijs_gewogen"),
    )
    .with_columns(
        pl.when(pl.col("aantal_woning_transacties_per_jaar") > 0)
        .then(pl.col("_prijs_gewogen") / pl.col("aantal_woning_transacties_per_jaar"))
        .otherwise(0.0)
        .alias("gemiddelde_prijs_van_een_woning"),
    )
    .drop("_prijs_gewogen")
    .sort("db_lden")
)

"""
# Stocks

Deze werden in de vorige file berekend en worden hier gewoon overgenomen. Hieronder op de kaart kan je lezen waar hoeveel van elke stock zit. Bepaalde getallen zijn exacte getallen, andere zijn op basis van schatting.
- "onbebouwde_bebouwbare_percelen"
- "onbebouwde_onbebouwbare_percelen"
- "bewoonde_niet_geïsoleerde_woning"
- "bewoonde_geïsoleerde_woning"
- "nieuwe_woning"
- "perceel_eigendom_overheid"
- "woning_eigendom_overheid"
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

"""
# Flows

Er zijn 27 flows in het huidige dashboard (24/06/2026), voor elk van deze flows moet bepaald worden wat de flow rate is in de "baseline" toestand en in de "active" toestand.
|flow|baseline berekend? | active berekend |
|---|---|---|
|verkavelingsverbod| |  |
|woongebiedverbod|x|x|
|aankoopbeleid_percelen| x| placeholder |
|voorkooprecht_percelen|x | placeholder |
|onteigening_percelen|x |  x|
|verbod_kleine_woning|placeholder |placeholder  |
|verbod_grote_woning|placeholder |placeholder  |
|verbod_kwetsbare_groep|x | x |
|woonverdichtingsverbod_niet_geïsoleerde_woningen| |  |
|woonverdichtingsverbod_geïsoleerde_woningen| |  |
|aankoopbeleid_niet_geïsoleerde_woningen| |  |
|aankoopbeleid_geïsoleerde_woningen| |  |
|voorkooprecht_niet_geïsoleerde_woningen| |  |
|voorkooprecht_geïsoleerde_woningen| |  |
|onteigening_niet_geïsoleerde_woningen| |  |
|onteigening_geïsoleerde_woningen| |  |
|isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning| |  |
|isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning| |  |
|renovatie_zonder_maatregel| |  |
|verplicht_isoleren_renovatie| |  |
|gesubsidieerd_isolatieprogramma| |  |
|gestuurd_isolatieprogramma| |  |
|aanleg_geluidsbuffers| |  |
|compensatie_buitenzone| |  |
|compensatie_verhuis| |  |
|versterken_sociale_cohesie| |  |
|vergroenen_leefomgeving| |  |

Alle berekeningen hieronder gebruiken `df` (geaggregeerd per `db_lden`). Flow rates zijn
teller / noemer op bandniveau; de staafdiagrammen lezen die kolommen rechtstreeks af.

Alle kolommen df_flows:
    [
      "db_lden",
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
      "aantal_vergunningen_nieuwbouw",
      "aantal_vergunningen_renovatie",
      "aantal_vergunningen_kwetsbare_groepen",
      "jaarlijks_aantal_vergunningen_met_isolatie",
      "jaarlijks_aantal_vergunningen_zonder_isolatie",
      "gemiddelde_prijs_van_een_woning",
      "woongebiedverbod_baseline",
      "woongebiedverbod_active",
      "aankoopbeleid_percelen_baseline",
      "aankoopbeleid_percelen_active",
      "voorkooprecht_percelen_baseline",
      "voorkooprecht_percelen_active",
      "onteigening_percelen_baseline",
      "onteigening_percelen_active",
      "verbod_kleine_woning_baseline",
      "verbod_kleine_woning_active",
      "verbod_grote_woning_baseline",
      "verbod_grote_woning_active",
      "verbod_kwetsbare_groep_baseline",
      "verbod_kwetsbare_groep_active",
      "aankoopbeleid_niet_geïsoleerde_woningen_baseline",
      "aankoopbeleid_niet_geïsoleerde_woningen_active",
      "aankoopbeleid_geïsoleerde_woningen_baseline",
      "aankoopbeleid_geïsoleerde_woningen_active"
    ]
"""

flow_rules = pl.read_csv("input/flow_rules.csv")

"""
## Woongebiedverbod

Transfer van `onbebouwde_onbebouwbare_percelen` naar `onbebouwde_bebouwbare_percelen` (netto
woongebied-aanduiding) of omgekeerd bij schrapping.

**Baseline:** netto jaarlijkse woongebied-creatie gedeeld door de stock onbebouwbare percelen:

    (onbebouwbaar_naar_bebouwbaar − bebouwbaar_naar_onbebouwbaar) / onbebouwde_onbebouwbare_percelen

**Active:** jaarlijkse schrapping van woongebied gedeeld door dezelfde noemer:

    bebouwbaar_naar_onbebouwbaar / onbebouwde_onbebouwbare_percelen

Als de noemer 0 is → flow rate 0. Resultaat wordt begrensd tot maximaal 1.
"""
df_flows = df

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
toon_flow_rate_staafdiagram(df_flows, "woongebiedverbod", aggregatie="gemiddelde")
"""
## aankoopbeleid_percelen
### Baseline
Als er geen aankoopbeleid wordt gevoerd dan worden geen percelen aangekocht.

### Active
Placeholder: 25% van de jaarlijkse woningtransacties op bandniveau:

    0,25 × aantal_woning_transacties_per_jaar / (bewoonde_niet_geïsoleerde_woning + bewoonde_geïsoleerde_woning)

Momenteel geen aparte perceeltransacties → `aantal_woning_transacties_per_jaar` als proxy.
Als de noemer 0 is → rate 0 (niet NaN).
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("aankoopbeleid_percelen_baseline"),
    (
        pl.col("aantal_woning_transacties_per_jaar")
        * pl.lit(0.25)
        / (
            pl.col("bewoonde_niet_geïsoleerde_woning")
            + pl.col("bewoonde_geïsoleerde_woning")
        )
    ).alias("aankoopbeleid_percelen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "aankoopbeleid_percelen", aggregatie="gemiddelde")
"""
## voorkooprecht_percelen
### Baseline

Als er geen voorkooprecht is dan worden geen percelen aangekocht.

### Active

Placeholder: 50% van de jaarlijkse woningtransacties op bandniveau:

    0,5 × aantal_woning_transacties_per_jaar / (bewoonde_niet_geïsoleerde_woning + bewoonde_geïsoleerde_woning)

Momenteel geen aparte perceeltransacties → `aantal_woning_transacties_per_jaar` als proxy.
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("voorkooprecht_percelen_baseline"),
    (
        pl.col("aantal_woning_transacties_per_jaar")
        * pl.lit(0.5)
        / (
            pl.col("bewoonde_niet_geïsoleerde_woning")
            + pl.col("bewoonde_geïsoleerde_woning")
        )
    ).alias("voorkooprecht_percelen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "voorkooprecht_percelen", aggregatie="gemiddelde")

"""
## onteigening_percelen
### Baseline
0
### Active
We na
"""
df_flows = df_flows.with_columns(
    pl.lit(0).alias("onteigening_percelen_baseline"),
    pl.lit(0.05).alias("onteigening_percelen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "onteigening_percelen", aggregatie="gemiddelde")
"""
## verbod_kleine_woning
We weten niet hoeveel van de woningen wel merplichtig zijn en hoeveel niet, hierdoor nemen we een placeholder-waarde van 0.97 van alle vergunningen voor nieuwbouw.
"""
df_flows = df_flows.with_columns(
   ( 0.97 * (pl.col("aantal_vergunningen_nieuwbouw")/ pl.col("onbebouwde_bebouwbare_percelen"))).alias("verbod_kleine_woning_baseline"),
    pl.lit(0).alias("verbod_kleine_woning_active"),
)
toon_flow_rate_staafdiagram(df_flows, "verbod_kleine_woning", aggregatie="gemiddelde")

"""
## verbod_grote_woning
### Baseline
We weten niet hoeveel van de woningen wel merplichtig zijn en hoeveel niet, hierdoor nemen we een placeholder-waarde van 0.03 van alle vergunningen voor nieuwbouw.
### Active

"""
df_flows = df_flows.with_columns(
   ( 0.03 * (pl.col("aantal_vergunningen_nieuwbouw")/ pl.col("onbebouwde_bebouwbare_percelen"))).alias("verbod_grote_woning_baseline"),
    pl.lit(0).alias("verbod_grote_woning_active"),
)
toon_flow_rate_staafdiagram(df_flows, "verbod_grote_woning", aggregatie="gemiddelde")

"""
## verbod_kwetsbare_groep

"""
df_flows = df_flows.with_columns(
    (pl.col("aantal_vergunningen_kwetsbare_groepen")/ pl.col("onbebouwde_bebouwbare_percelen")).alias("verbod_kwetsbare_groep_baseline"),
    pl.lit(0).alias("verbod_kwetsbare_groep_active"),
)
toon_flow_rate_staafdiagram(df_flows, "verbod_kwetsbare_groep", aggregatie="gemiddelde")
"""
## woonverdichtingsverbod_niet_geïsoleerde_woningen
Nog geen informatie.
"""
"""
## woonverdichtingsverbod_geïsoleerde_woningen
Nog geen informatie.
"""
"""
## aankoopbeleid_niet_geïsoleerde_woningen
"""
df_flows = df_flows.with_columns(
    (pl.col("aantal_transacties_niet_geïsoleerde_woningen") / pl.col("bewoonde_niet_geïsoleerde_woning")).alias("aankoopbeleid_niet_geïsoleerde_woningen_baseline"),
    pl.lit(0).alias("aankoopbeleid_niet_geïsoleerde_woningen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "aankoopbeleid_niet_geïsoleerde_woningen", aggregatie="gemiddelde")
"""
## aankoopbeleid_geïsoleerde_woningen
Nog geen informatie.
"""
df_flows = df_flows.with_columns(
    (pl.col("aantal_transacties_geïsoleerde_woningen") / pl.col("bewoonde_geïsoleerde_woning")).alias("aankoopbeleid_geïsoleerde_woningen_baseline"),
    pl.lit(0).alias("aankoopbeleid_geïsoleerde_woningen_active"),
)
toon_flow_rate_staafdiagram(df_flows, "aankoopbeleid_geïsoleerde_woningen", aggregatie="gemiddelde")
df_flows.columns
"""
# Vragen
- Momenteel nog geen data over de transacties van percelen, dus gebruikten we aantal_woning_transacties_per_jaar

"""
