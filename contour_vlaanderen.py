import polars as pl
import streamlit as st

import contour_vlaanderen_grafieken as grafieken
from contour_vlaanderen_grafieken import TOON_KAARTEN as _DEFAULT_TOON_KAARTEN
from contour_vlaanderen_grafieken import toon_staafdiagram_per_gewest
from contour_vlaanderen_kaart import toon_overlap_kaart
from contour_vlaanderen_kolommen import KOLOM_HERNAMING, toon_kolomdocumentatie

# uv run streamlit run contour_vlaanderen.py

TOON_KAARTEN = False
grafieken.TOON_KAARTEN = TOON_KAARTEN

st.set_page_config(page_title="Data analyse contour Vlaanderen", layout="wide")
st.title("Data analyse contour Vlaanderen")
st.caption("Sector–contour-overlappen rond de luchthaven (LDEN, Vlaanderen + Brussel)")

with st.expander("Kolomoverzicht & uitleg", expanded=False):
    toon_kolomdocumentatie()

st.subheader("Kaart")
df = pl.read_excel("data/20260623 data vlaanderen 1.xlsx").rename(KOLOM_HERNAMING)
if TOON_KAARTEN:
    toon_overlap_kaart(df)

st.subheader("Data")
st.caption(f"{df.height:,} rijen · {df.width} kolommen")
st.dataframe(df, use_container_width=True)

"""
## Basisdata
### Inwoners
De inwoners van Vlaanderen werden op basis van gegevens van het departement Omgeving berekend. Deze gegevens zijn op het niveau van de adressen verkregen en verwerkt tot een inonweraantal van een overlap tussen een statistische sector en 1 db contour.

Voor Brussel is er geen data beschikbaar op het niveau van de adressen. Hierdoor werd de data gebruikt van de statistische sectoren van Brussel. Deze data op sectorniveau werd dan via overlap op basis van oppervlakte met de db contouren berekend.
"""
df = df.with_columns(
    inwoners=pl.when(pl.col("regio_nl") == "Vlaams Gewest")
    .then(pl.col("inwoners_client"))
    .when(pl.col("regio_nl") == "Brussels Hoofdstedelijk Gewest")
    .then(pl.col("inwoners_overlap"))
    .otherwise(pl.col("inwoners_overlap"))  # Waals Gewest (7 rijen)
)

toon_staafdiagram_per_gewest(
    df,
    "inwoners",
    titel="Inwoners per zone",
    y_label="Inwoners",
)

"""
### Aantal inwoners per woning
Voor Vlaanderen weten we exact hoeveel inwoners er zijn per woning. Voor Brussel weten we dat niet, omdat er geen data beschikbaar is op het niveau van de adressen. We berekenen dus één gemiddelde voor het aantal inwoners per woning, dat we vervolgens gebruiken voor de rest van de analyse.
"""
totaal_inwoners_vlaanderen = (
    df.filter(pl.col("regio_nl") == "Vlaams Gewest")
    .select(pl.col("inwoners"))
    .sum()
    .item()
)
totaal_aantal_woningen_vlaanderen = (
    df.filter(pl.col("regio_nl") == "Vlaams Gewest")
    .select(pl.col("aantal_woningen"))
    .sum()
    .item()
)
gemiddelde_inwoners_per_woning_vlaanderen = (
    totaal_inwoners_vlaanderen / totaal_aantal_woningen_vlaanderen
)
gemiddelde_inwoners_per_woning = gemiddelde_inwoners_per_woning_vlaanderen
st.write(
    f"Gemiddelde aantal inwoners per woning in Vlaams Gewest: **{gemiddelde_inwoners_per_woning:.2f}**"
)
"""
### Aantal woningen
Voor Vlaanderen weten we hoeveel woningen er zijn per adres in de zones. Voor Brussel weten we dat niet, omdat er geen data beschikbaar is op het niveau van de adressen. Om te weten hoeveel woningen er zijn in Brussel, delen we het aantal inwoners door het gemiddelde aantal inwoners per woning.
"""

df = df.with_columns(
    aantal_woningen=pl.when(pl.col("regio_nl") == "Brussels Hoofdstedelijk Gewest")
    .then(pl.col("inwoners") / gemiddelde_inwoners_per_woning)
    .otherwise(pl.col("aantal_woningen"))
)
toon_staafdiagram_per_gewest(
    df,
    "aantal_woningen",
    titel="Aantal woningen per zone",
    y_label="Aantal woningen",
)
"""
### Onbebouwde bebouwbare percelen
Momenteel geen data over onbebouwde bebouwbare percelen, maanda g doorgestuurd

### Onbebouwde onbebouwbare percelen
Momenteel geen data over onbebouwde onbebouwbare percelen

### Bewoonde_niet_geïsoleerde_woning
Als placeholder gebruiken we 80% van de bewoonde woningen.

Expert opinion: 95% niet geïsoleerd voor Brussel. Er moet een tekst geschreven worden waarbij blijkt dat jedat input heel precies is maar langs je output kant is het geaggregeerd. dus eigenlijk maakt het voor bepaalde data niet echt uit hoe specifiek het is.
"""
df = df.with_columns(bewoonde_niet_geïsoleerde_woning=pl.col("aantal_woningen") * 0.8)
# maak een barchart van de bewoonde niet geisoleerde woningen, splits het op naargelang brussels en vlaams gewest
toon_staafdiagram_per_gewest(
    df,
    "bewoonde_niet_geïsoleerde_woning",
    titel="Bewoonde niet-geïsoleerde woningen per gewest",
    y_label="Bewoonde niet-geïsoleerde woningen",
)
"""
### Bewoonde_geïsoleerde_woning
Als placeholder gebruiken we 20% van de bewoonde woningen
! 5% make voor brussel
"""
df = df.with_columns(bewoonde_geïsoleerde_woning=pl.col("aantal_woningen") * 0.2)
toon_staafdiagram_per_gewest(
    df,
    "bewoonde_geïsoleerde_woning",
    titel="Bewoonde geïsoleerde woningen per gewest",
    y_label="Bewoonde geïsoleerde woningen",
)
"""
### Nieuwe woning
De variabele nieuwe woning is gewoon een interne variabele die we gebruiken voor het dashboard, hierdoor is dit steeds 0. Deuidelijker schrijven
"""
df = df.with_columns(nieuwe_woning=pl.lit(0))
"""
### Perceel eigendom overheid
De variabele nieuwe woning is gewoon een interne variabele die we gebruiken voor het dashboard, hierdoor is dit steeds 0.
"""
df = df.with_columns(perceel_eigendom_overheid=pl.lit(0))
"""
### Woning eigendom overheid
De variabele woning_eigendom_overheid is gewoon een interne variabele die we gebruiken voor het dashboard, hierdoor is dit steeds 0.
"""
df = df.with_columns(woning_eigendom_overheid=pl.lit(0))

"""
### Aantal onbebouwbare percelen die bebouwbaar zijn geworden jaarlijks
Om het effect van een woongebiedverbod te weten te komen, is het belangrijk om te weten hoeveel percelen die onbebouwbaar zijn, bebouwbaar gemaakt worden door het aanduiden van woongebied. We nemen een gemiddelde over de periode 2021-2026 voor elke db contour en we verdelen dit over elke inter_ss_lden. We delen dus het aantal percelen door het totaal aantal vierkante meter per db contour en we vermenigvuldigen dit met "oppervlakte_overlap_m2" van df.
Kolommen van df_bebouwbaar_onbebouwbaar:

- "db lden"
- "aantal percelen niet bebouwbaar naar bebouwbaar"
- "aantal percelen bebouwbaar naar niet bebouwbaar"

Er is geen data van Brussel hierover te vinden.
Geheel gewestelijk bestemmingsplan hoofdzakelijk vastligt, behalve bij demografisch gewestelijk  normaal gezien wordt er geen woongebied bijgemaakt. Voor brussel op nul zetten.
"""
df_bebouwbaar_onbebouwbaar = pl.read_excel(
    "data/20260622 data vlaanderen 2 bebouwbaar en onbebouwbaar.xlsx", sheet_name="lden"
)

_KOL_NAAR_BEBOUWBAAR = "aantal percelen niet bebouwbaar naar bebouwbaar"
_KOL_NAAR_ONBEBOUWBAAR = "aantal percelen bebouwbaar naar niet bebouwbaar"

oppervlakte_per_db = (
    df.filter(pl.col("regio_nl") == "Vlaams Gewest")
    .group_by("db_lden")
    .agg(pl.col("oppervlakte_overlap_m2").sum().alias("totaal_overlap_m2_vla"))
)

df = (
    df.join(oppervlakte_per_db, on="db_lden", how="left")
    .join(df_bebouwbaar_onbebouwbaar, on="db_lden", how="left")
    .with_columns(
        pl.when(pl.col("regio_nl") == "Vlaams Gewest")
        .then(
            pl.col(_KOL_NAAR_BEBOUWBAAR).fill_null(0)
            / pl.col("totaal_overlap_m2_vla")
            * pl.col("oppervlakte_overlap_m2")
        )
        .otherwise(0.0)
        .alias("onbebouwbaar_naar_bebouwbaar"),
        pl.when(pl.col("regio_nl") == "Vlaams Gewest")
        .then(
            pl.col(_KOL_NAAR_ONBEBOUWBAAR).fill_null(0)
            / pl.col("totaal_overlap_m2_vla")
            * pl.col("oppervlakte_overlap_m2")
        )
        .otherwise(0.0)
        .alias("bebouwbaar_naar_onbebouwbaar"),
    )
    .drop(_KOL_NAAR_BEBOUWBAAR, _KOL_NAAR_ONBEBOUWBAAR)
)

toon_staafdiagram_per_gewest(
    df,
    kolom="onbebouwbaar_naar_bebouwbaar",
    titel="Onbebouwbaar naar bebouwbaar",
    y_label="Aantal percelen",
)
"""
### Aantal bebouwbaar naar onbebouwbaar per db contour
Jaarlijks worden er ook percelen die bebouwbaar zijn,  onbebouwbaar gemaakt. Dzelfde methode als hierboven wordt toegepast om dit te berekenen.

Er is geen data van Brussel hierover te vinden.
"""
toon_staafdiagram_per_gewest(
    df,
    kolom="bebouwbaar_naar_onbebouwbaar",
    titel="Bebouwbaar naar onbebouwbaar",
    y_label="Aantal percelen",
)

"""
### Totaal aantal transacties
Om te berekenen hoeveel woningen kunnen opgekocht worden door voorkooprecht of aankoopbeleid moeten we weten hoeveel er jaarlijks verkocht worden.
"""
df_huis_transacties = pl.read_csv(
    "data/transacties_vastgoed/transacties_woningen.csv",
    separator="\t",
    encoding="utf-8",
    infer_schema_length=10000,
    null_values=[""],
).filter(pl.col("avg_PriceP50").is_not_null())

df_appartement_transacties = pl.read_csv(
    "data/transacties_vastgoed/transacties_appartementen.csv",
    separator="\t",
    encoding="utf-8",
    infer_schema_length=10000,
    null_values=[""],
).filter(pl.col("avg_PriceP50").is_not_null())

# gewogen gemiddelde van avg_PriceP50, gewogen met sum_ParcelsNumber
df_woning_transacties = (
    df_huis_transacties.join(
        df_appartement_transacties,
        on="NISCode",
        how="inner",
        suffix="_app",
    )
    .rename(
        {col: f"{col}_huis" for col in df_huis_transacties.columns if col != "NISCode"}
    )
    .with_columns(
        w_huis=pl.col("sum_ParcelsNumber_huis"),
        w_app=pl.col("sum_ParcelsNumber_app"),
    )
    .with_columns(
        aantal_transacties_per_jaar=pl.col("w_huis") + pl.col("w_app"),
        gemiddelde_prijs_van_een_woning=(
            pl.col("avg_PriceP50_huis") * pl.col("w_huis")
            + pl.col("avg_PriceP50_app") * pl.col("w_app")
        )
        / (pl.col("w_huis") + pl.col("w_app")),
    )
    .drop("w_huis", "w_app")
)
df_woning_transacties = df_woning_transacties.select(
    pl.col("NISCode"),
    pl.col("aantal_transacties_per_jaar"),
    pl.col("gemiddelde_prijs_van_een_woning"),
).rename({"NISCode": "nis_sector"})
st.write(df_woning_transacties)
df = df.join(df_woning_transacties, on="nis_sector", how="left").with_columns(
    pl.when(pl.col("regio_nl") == "Vlaams Gewest")
    .then(
        pl.col("aantal_transacties_per_jaar")
        / pl.col("totaal_overlap_m2_vla")
        * pl.col("oppervlakte_overlap_m2")
    )
    .otherwise(0.0)
    .alias("aantal_transacties_per_jaar"),
    pl.when(pl.col("regio_nl") == "Vlaams Gewest")
    .then(pl.col("gemiddelde_prijs_van_een_woning"))
    .otherwise(0.0)
    .alias("gemiddelde_prijs_van_een_woning"),
)
st.write(df)

toon_staafdiagram_per_gewest(
    df,
    kolom="aantal_transacties_per_jaar",
    titel="Aantal transacties per jaar",
    y_label="Aantal transacties",
)
"""
### Gemiddelde prijs van een woning
Uit dezelfde transactiedata haalden we de gemiddelde prijs van een woning.
"""
toon_staafdiagram_per_gewest(
    df,
    kolom="gemiddelde_prijs_van_een_woning",
    titel="Gemiddelde prijs van een woning",
    y_label="Gemiddelde prijs (€)",
    aggregatie="gemiddelde",
    gewicht_kolom="aantal_transacties_per_jaar",
    waarde_format=",.0f",
)

"""
### Aantal transacties van bebouwbare percelen
Geen info. Al gevraagd aan Gaëlle.
"""

"""
### Aantal transacties van onbebouwbare percelen
Geen info, al gevraagd aan Gaëlle
"""

"""
### Gemiddelde prijs van bebouwbare percelen
Geen info
"""

"""
### Gemiddelde prijs van bebouwbare percelen
Geen info
"""

"""
### Aantal vergunningen nieuwbouw
Van het departement omgeving kregen we data over het aantal vergunningen per gemeente. We nemen een gemiddelde van de jaren 2021 tot en met 2025.

Het aantal vergunningen per jaar wordt dan toegevoegd aan de originele dataset, deze worden toegewezen op basis van het aantal bebouwbare percelen per statistische sector van een gemeente. Als er bijvoorbeeld 100 vergunningen gemiddeld per jaar zijn in gemeente x en gemeente x is verdeeld in 2 statistische sectoren, met
- sector 1: 30 bebouwbare percelen
- sector 2: 20 bebouwbare percelen

Dan wordt van sector 1 gezegd dat het gemiddeld jaarlijks aantal vergunningen 60 bedraagt en sector 2 is dan 40.
"""
df_vergunningen = pl.read_csv(
    "data/vergunningen_omgevingsloket_2026_lang.csv", separator=";"
)

df_vergunningen_nieuwbouw = (
    df_vergunningen.filter(
        (pl.col("handeling") == "Nieuwbouw")
        & pl.col("jaar_indiening").cast(pl.Int64, strict=False).is_between(2021, 2025)
        & (pl.col("gebouw_functie") == "Totalen")
        & (pl.col("metriek") == "Aantal wooneenheden")
        & (~pl.col("gemeente").is_in(["Totalen", "-", "(deels) Niet in Vlaanderen"]))
    )
    .group_by("gemeente")
    .agg((pl.col("waarde").sum() / 5).alias("gemiddeld_per_jaar"))
    .sort("gemeente")
)
st.dataframe(df_vergunningen_nieuwbouw, use_container_width=True)

totaal_percelen_woongebied_gemeente = df.group_by("naam_gemeente_nl").agg(
    pl.col("aantal_percelen_onbebouwd_woongebied")
    .fill_null(0)
    .sum()
    .alias("totaal_percelen_woongebied_gemeente")
)

df = (
    df.join(totaal_percelen_woongebied_gemeente, on="naam_gemeente_nl", how="left")
    .join(
        df_vergunningen_nieuwbouw,
        left_on="naam_gemeente_nl",
        right_on="gemeente",
        how="left",
    )
    .with_columns(
        pl.when(pl.col("totaal_percelen_woongebied_gemeente") > 0)
        .then(
            pl.col("gemiddeld_per_jaar").fill_null(0)
            * pl.col("aantal_percelen_onbebouwd_woongebied").fill_null(0)
            / pl.col("totaal_percelen_woongebied_gemeente")
        )
        .otherwise(0.0)
        .alias("aantal_vergunningen_nieuwbouw")
    )
    .drop("totaal_percelen_woongebied_gemeente", "gemiddeld_per_jaar")
)

toon_staafdiagram_per_gewest(
    df,
    kolom="aantal_vergunningen_nieuwbouw",
    titel="Vergunde wooneenheden nieuwbouw per zone",
    y_label="Wooneenheden per jaar (gem.)",
)

"""
### Vergunningen renovatie
Dezelfde dataset wordt gebruikt, maar deze keer wordt er gefilterd op "Verbouwen of hergebruik". Het aantal renovaties wordt toegewezen aan elke intersectie adhv het aantal woningen in elke intersectie, zoals in het voorbeeld hierboven, maar met woningen en geen percelen.
"""
df_vergunningen_renovatie = (
    df_vergunningen.filter(
        (pl.col("handeling") == "Verbouwen of hergebruik")
        & pl.col("jaar_indiening").cast(pl.Int64, strict=False).is_between(2021, 2025)
        & (pl.col("gebouw_functie") == "Totalen")
        & (pl.col("metriek") == "Aantal wooneenheden")
        & (~pl.col("gemeente").is_in(["Totalen", "-", "(deels) Niet in Vlaanderen"]))
    )
    .group_by("gemeente")
    .agg((pl.col("waarde").sum() / 5).alias("gemiddeld_per_jaar"))
    .sort("gemeente")
)
totaal_woningen_per_gemeente = df.group_by("naam_gemeente_nl").agg(
    pl.col("aantal_woningen")
    .fill_null(0)
    .sum()
    .alias("totaal_aantal_woningen_gemeente")
)

df = (
    df.join(totaal_woningen_per_gemeente, on="naam_gemeente_nl", how="left")
    .join(
        df_vergunningen_renovatie,
        left_on="naam_gemeente_nl",
        right_on="gemeente",
        how="left",
    )
    .with_columns(
        pl.when(pl.col("totaal_aantal_woningen_gemeente") > 0)
        .then(
            pl.col("gemiddeld_per_jaar").fill_null(0)
            * pl.col("aantal_woningen").fill_null(0)
            / pl.col("totaal_aantal_woningen_gemeente")
        )
        .otherwise(0.0)
        .alias("aantal_vergunningen_renovatie")
    )
    .drop("totaal_aantal_woningen_gemeente", "gemiddeld_per_jaar")
)
toon_staafdiagram_per_gewest(
    df,
    kolom="aantal_vergunningen_renovatie",
    titel="Vergunde renovaties per zone per jaar",
    y_label="Wooneenheden per jaar (gem.)",
)
"""
### Aantal vergunningen kwetsbare groepen
Hier wordt onderzocht hoeveel vergunde wooneenheden jaarlijks worden toegekend aan kwetsbare groepen. Deze worden toegewezen adhv de onbebouwde percelen per intersectie.
"""
df_vergunningen_kwetsbare_groepen = pl.read_csv(
    "data/vergunningen_kwetsbare_functies_2026_lang.csv", separator=";"
)

df_vergunningen_kwetsbare_groepen = (
    df_vergunningen_kwetsbare_groepen.filter(
        (pl.col("handeling") == "Totalen")
        & pl.col("jaar_indiening").cast(pl.Int64, strict=False).is_between(2021, 2025)
        # & (pl.col("gebouw_functie") == "Totalen")
        & (pl.col("metriek") == "Aantal projecten")
        & (~pl.col("gemeente").is_in(["Totalen", "-", "(deels) Niet in Vlaanderen"]))
    )
    .group_by("gemeente")
    .agg((pl.col("waarde").sum() / 5).alias("gemiddeld_per_jaar"))
    .sort("gemeente")
)
totaal_percelen_woongebied_gemeente = df.group_by("naam_gemeente_nl").agg(
    pl.col("aantal_percelen_onbebouwd_woongebied")
    .fill_null(0)
    .sum()
    .alias("totaal_percelen_woongebied_gemeente")
)

df = (
    df.join(totaal_percelen_woongebied_gemeente, on="naam_gemeente_nl", how="left")
    .join(
        df_vergunningen_kwetsbare_groepen,
        left_on="naam_gemeente_nl",
        right_on="gemeente",
        how="left",
    )
    .with_columns(
        pl.when(pl.col("totaal_percelen_woongebied_gemeente") > 0)
        .then(
            pl.col("gemiddeld_per_jaar").fill_null(0)
            * pl.col("aantal_percelen_onbebouwd_woongebied").fill_null(0)
            / pl.col("totaal_percelen_woongebied_gemeente")
        )
        .otherwise(0.0)
        .alias("aantal_vergunningen_nieuwbouw")
    )
    .drop("totaal_percelen_woongebied_gemeente", "gemiddeld_per_jaar")
)

toon_staafdiagram_per_gewest(
    df,
    kolom="aantal_vergunningen_nieuwbouw",
    titel="Vergunde wooneenheden nieuwbouw per zone",
    y_label="Wooneenheden per jaar (gem.)",
)


st.dataframe(df_vergunningen_kwetsbare_groepen)