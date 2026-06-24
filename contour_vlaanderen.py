import polars as pl
import streamlit as st

import contour_vlaanderen_grafieken as grafieken
from contour_vlaanderen_grafieken import toon_staafdiagram_per_gewest
from contour_vlaanderen_kaart import toon_overlap_kaart
from contour_vlaanderen_kolommen import KOLOM_HERNAMING, toon_kolomdocumentatie
from contour_vlaanderen_vergunningen import (
    vergunningen_gemiddeld_per_gemeente,
    wijs_proportioneel_toe,
)

# uv run streamlit run contour_vlaanderen.py
# uv run pytest tests/test_vergunningen_toewijzing.py -v

TOON_KAARTEN = False
grafieken.TOON_KAARTEN = TOON_KAARTEN

st.set_page_config(page_title="Data analyse contour Vlaanderen", layout="wide")
st.title("Data analyse contour Vlaanderen")
"""
Volgende termen zijn belangrijk voor de analyse:
|Term|Definitie|
|----|---------|
|Contour| Dit zijn de Decibelcontouren die verkregen werden van Brussels airport company. Deze zijn op een schaal van 1Db en omringen de luchthaven. één zone betekent dat hetzelfde geluidsniveau wordt geregistreerd daar.|
|Statistische sector| Dit zijn statistische regios waarop informatie normaal gesproken wordt geregistreerd.|
|Intersectie| Dit is de term die wij geven aan de overlap van een contour en een statistische sector. Deze zijn dus steeds kleinere zones dan een statistische sector en ook steeds kleiner dan de contouren.|
"""
st.caption("Sector–contour-overlappen rond de luchthaven (LDEN, Vlaanderen + Brussel)")

with st.expander("Kolomoverzicht & uitleg", expanded=False):
    toon_kolomdocumentatie()

st.subheader("Kaart")
df = pl.read_excel("data/20260623 data vlaanderen 1.xlsx").rename(KOLOM_HERNAMING)
if TOON_KAARTEN:
    toon_overlap_kaart(df)

st.subheader("Data")
st.caption(f"{df.height:,} rijen · {df.width} kolommen")

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
Deze informatie kregen we op het precieze adresniveau, hiermee berekenden we het aantal percelen per intersectie.
"""
df = df.with_columns(
    onbebouwde_bebouwbare_percelen=pl.col("aantal_percelen_onbebouwd_woongebied")
)
toon_staafdiagram_per_gewest(
    df,
    "onbebouwde_bebouwbare_percelen",
    titel="Onbebouwde bebouwbare percelen",
    y_label="Aantal onbebouwde bebouwbare percelen",
)
"""
### Onbebouwde onbebouwbare percelen
Momenteel geen data over onbebouwde onbebouwbare percelen, dus we nemen als placeholder 3 maal zoveel onbebouwde onbebouwbare percelen.
"""
df = df.with_columns(
    onbebouwde_onbebouwbare_percelen=pl.col("aantal_percelen_onbebouwd_woongebied")
    * pl.lit(3)
)

"""
### Bewoonde_niet_geïsoleerde_woning
Er is geen gedetailleerde isolatiedata per woning beschikbaar. We gebruiken daarom vaste aannames per gewest:
- **Vlaanderen:** 80% van de bewoonde woningen is niet-geïsoleerd
- **Brussel:** 95% van de bewoonde woningen is niet-geïsoleerd (expert opinion)

De input kan op adresniveau precies zijn, maar voor het dashboard aggregeren we naar contour–sector-overlappen. Voor deze verdeling maakt die aggregatie weinig verschil.
"""
df = df.with_columns(
    bewoonde_niet_geïsoleerde_woning=pl.when(
        pl.col("regio_nl") == "Brussels Hoofdstedelijk Gewest"
    )
    .then(pl.col("aantal_woningen") * 0.95)
    .when(pl.col("regio_nl") == "Vlaams Gewest")
    .then(pl.col("aantal_woningen") * 0.80)
    .otherwise(pl.col("aantal_woningen") * 0.80)
)
toon_staafdiagram_per_gewest(
    df,
    "bewoonde_niet_geïsoleerde_woning",
    titel="Bewoonde niet-geïsoleerde woningen per gewest",
    y_label="Bewoonde niet-geïsoleerde woningen",
)
"""
### Bewoonde_geïsoleerde_woning
Aanvullend op de verdeling hierboven:
- **Vlaanderen:** 20% geïsoleerd
- **Brussel:** 5% geïsoleerd
"""
df = df.with_columns(
    bewoonde_geïsoleerde_woning=pl.when(
        pl.col("regio_nl") == "Brussels Hoofdstedelijk Gewest"
    )
    .then(pl.col("aantal_woningen") * 0.05)
    .when(pl.col("regio_nl") == "Vlaams Gewest")
    .then(pl.col("aantal_woningen") * 0.20)
    .otherwise(pl.col("aantal_woningen") * 0.20)
)
toon_staafdiagram_per_gewest(
    df,
    "bewoonde_geïsoleerde_woning",
    titel="Bewoonde geïsoleerde woningen per gewest",
    y_label="Bewoonde geïsoleerde woningen",
)
"""
### Nieuwe woning
Interne dashboardvariabele (tussenstock nieuwbouw in de simulator). Geen brondata in deze
analyse — de waarde blijft steeds 0. Nieuwbouw per gewest wordt berekend onder
**Aantal vergunningen nieuwbouw**.
"""
df = df.with_columns(nieuwe_woning=pl.lit(0.0))
"""
### Perceel eigendom overheid
Interne dashboardvariabele; geen brondata beschikbaar, dus steeds 0.
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

Het gewestelijk bestemmingsplan van Brussel ligt hoofdzakelijk vast, behalve bij demografisch gewestelijk plan. Normaal gezien wordt er geen woongebied bijgemaakt. Dit betekent dat er geen extra gebieden bebouwbaar gemaakt worden in Brussel.
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

Het totaal aantal transacties wordt in Brussel en in vlaanderen als volgt berekend: we hebben data op het niveau van de statistische sectoren, dit betekent dat deze moeten toegewezen worden met de intersecties van stat sectoren en db contouren. Deze worden toegewezen door het aantal woningen die proportioneel in die intersectie zitten:
Als er één statistische sector A is met twee delen: "deel 1" en "deel 2" en er zijn 100 transacties voor die sector, dan:
- sector A, deel 1: heeft 20 woningen, dan krijgt het 40 transacties per jaar toegewezen
- sector A, deel 2: heeft 30 woningen, dan krijgt het 60 transacties per jaar toegewezen
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

# Per rij: som transacties (woning + appartement) en gewogen gemiddelde prijs
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
        w_huis=pl.col("sum_ParcelsNumber_huis").fill_null(0),
        w_app=pl.col("sum_ParcelsNumber_app").fill_null(0),
    )
    .with_columns(
        aantal_transacties_per_jaar=pl.col("w_huis") + pl.col("w_app"),
        gemiddelde_prijs_van_een_woning=(
            pl.col("avg_PriceP50_huis") * pl.col("w_huis")
            + pl.col("avg_PriceP50_app") * pl.col("w_app")
        )
        / (pl.col("w_huis") + pl.col("w_app")),
    )
)

# Aggregeer naar statistische sector (NISCode zonder trailing "-")
df_transacties_sector = (
    df_woning_transacties.with_columns(
        nis_sector=pl.col("NISCode").str.strip_chars_end("-"),
    )
    .group_by("nis_sector")
    .agg(
        pl.col("aantal_transacties_per_jaar").sum(),
        (
            (
                pl.col("gemiddelde_prijs_van_een_woning")
                * pl.col("aantal_transacties_per_jaar")
            ).sum()
            / pl.col("aantal_transacties_per_jaar").sum()
        ).alias("gemiddelde_prijs_van_een_woning"),
    )
)

# Toewijzen aan intersecties: gewicht = aantal_woningen binnen dezelfde sector
df = df.with_columns(pl.col("nis_sector").str.strip_chars_end("-"))
df = wijs_proportioneel_toe(
    df,
    df_transacties_sector,
    groep_kolom="nis_sector",
    bron_waarde_kolom="aantal_transacties_per_jaar",
    gewicht_kolom="aantal_woningen",
    uitvoer_kolom="aantal_transacties_per_jaar",
    doorgeef_kolommen=("gemiddelde_prijs_van_een_woning",),
)

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

**Vlaanderen:** vergunde nieuwbouwooneenheden uit het omgevingsloket (Departement Omgeving).
Gemiddelde over 2021–2025 per gemeente; toegewezen aan intersecties proportioneel naar
`onbebouwde_bebouwbare_percelen`. Voorbeeld: 100 vergunningen in gemeente x, sector 1
heeft 30 onbebouwde woongebied-percelen en sector 2 heeft 20 → 60 + 40 vergunningen.

**Brussel:** geen omgevingsloket-data beschikbaar. We gebruiken het geregistreerd woningbestand
per gemeente (2021–2025) als proxy voor nieuwbouw. Gemiddelde jaarlijkse groei = telkens het
verschil tussen twee opeenvolgende jaren, gemiddeld over vier stappen:
2022 − 2021, 2023 − 2022, 2024 − 2023, 2025 − 2024. Die groei wijzen we toe aan intersecties
proportioneel naar `aantal_woningen` binnen dezelfde gemeente.

Op gewestniveau komen er zo gemiddeld **~4.050 geregistreerde wooneenheden per jaar** bij in
heel het Brussels Hoofdstedelijk Gewest (19 gemeenten). In onze contour vallen **17 Brusselse
gemeenten**; daar is de gemiddelde groei **~3.360 wooneenheden per jaar** (Elsene en Ukkel
zitten niet in de overlap-dataset).

**Conservatie (Vlaanderen):** als je alle toegewezen vergunningen per intersectie optelt, kom je per gemeente (met minstens één onbebouwd woongebied-perceel in de contour) opnieuw uit bij het oorspronkelijke gemeentegemiddelde. Dit wordt gecontroleerd in `tests/test_vergunningen_toewijzing.py`.

**Uitzondering — gemeenten zonder woongebied-percelen in de contour:** drie gemeenten staan wel in de vergunningendata, maar hebben 0 onbebouwde woongebied-percelen in onze overlap-dataset. Daar kan niet proportioneel naar verdeeld worden; zij krijgen 0 toegewezen vergunningen op intersectieniveau, hoewel het gemeentegemiddelde in de brondata > 0 is:
- Hoeilaart (0,4 wooneenheden/jaar gem.)
- Tielt-Winge (0,4 wooneenheden/jaar gem.)
- Kapelle-op-den-Bos (6,4 wooneenheden/jaar gem.)

Dit is geen fout in de toewijzingslogica, maar een ontbrekende gewichtenkolom (`onbebouwde_bebouwbare_percelen`) voor die gemeenten binnen de contour.

"""
df = df.with_columns(aantal_vergunningen_nieuwbouw=pl.lit(0.0))

# --- Vlaanderen: omgevingsloket ---
df_vergunningen = pl.read_csv(
    "data/vergunningen_omgevingsloket_2026_lang.csv", separator=";"
)

df_vergunningen_nieuwbouw = vergunningen_gemiddeld_per_gemeente(
    df_vergunningen,
    handeling="Nieuwbouw",
)

df_vla = wijs_proportioneel_toe(
    df.filter(pl.col("regio_nl") == "Vlaams Gewest"),
    df_vergunningen_nieuwbouw,
    groep_kolom="naam_gemeente_nl",
    bron_groep_kolom="gemeente",
    bron_waarde_kolom="gemiddeld_per_jaar",
    gewicht_kolom="onbebouwde_bebouwbare_percelen",
    uitvoer_kolom="aantal_vergunningen_nieuwbouw",
)

# --- Brussel: gemiddelde groei geregistreerd woningbestand ---
df_woningen_brussel = pl.read_excel(
    "data/20260624 data brussel aantal woningen.xlsx",
    sheet_name="evolutie woningbestand",
).select("Gemeente", "2021", "2022", "2023", "2024", "2025")

df_groei_brussel = (
    df_woningen_brussel.with_columns(
        (pl.col("2022") - pl.col("2021")).alias("groei_2021_2022"),
        (pl.col("2023") - pl.col("2022")).alias("groei_2022_2023"),
        (pl.col("2024") - pl.col("2023")).alias("groei_2023_2024"),
        (pl.col("2025") - pl.col("2024")).alias("groei_2024_2025"),
    )
    .with_columns(
        (
            (
                pl.col("groei_2021_2022")
                + pl.col("groei_2022_2023")
                + pl.col("groei_2023_2024")
                + pl.col("groei_2024_2025")
            )
            / 4
        ).alias("gemiddelde_jaarlijkse_groei")
    )
    .select(
        pl.col("Gemeente").alias("naam_gemeente_nl"),
        "gemiddelde_jaarlijkse_groei",
    )
)

totaal_groei_brussel_gewest = df_groei_brussel["gemiddelde_jaarlijkse_groei"].sum()
gemeenten_brussel_contour = (
    df.filter(pl.col("regio_nl") == "Brussels Hoofdstedelijk Gewest")
    .select("naam_gemeente_nl")
    .unique()["naam_gemeente_nl"]
)
totaal_groei_brussel_contour = df_groei_brussel.filter(
    pl.col("naam_gemeente_nl").is_in(gemeenten_brussel_contour)
)["gemiddelde_jaarlijkse_groei"].sum()
st.write(
    f"Gemiddeld aantal bijkomende geregistreerde wooneenheden per jaar in Brussel: "
    f"**{totaal_groei_brussel_gewest:,.0f}** (heel gewest, 19 gemeenten) · "
    f"**{totaal_groei_brussel_contour:,.0f}** (17 gemeenten in onze contour)"
)

df_br = wijs_proportioneel_toe(
    df.filter(pl.col("regio_nl") == "Brussels Hoofdstedelijk Gewest"),
    df_groei_brussel,
    groep_kolom="naam_gemeente_nl",
    bron_waarde_kolom="gemiddelde_jaarlijkse_groei",
    gewicht_kolom="aantal_woningen",
    uitvoer_kolom="aantal_vergunningen_nieuwbouw",
)

df = pl.concat(
    [
        df_vla,
        df_br,
        df.filter(
            ~pl.col("regio_nl").is_in(
                ["Vlaams Gewest", "Brussels Hoofdstedelijk Gewest"]
            )
        ).with_columns(aantal_vergunningen_nieuwbouw=pl.lit(0.0)),
    ]
)

toon_staafdiagram_per_gewest(
    df,
    kolom="aantal_vergunningen_nieuwbouw",
    titel="Vergunde wooneenheden nieuwbouw per zone",
    y_label="Wooneenheden per jaar (gem.)",
)

"""
### Jaarlijks aantal vergunningen voor renovatie
Dezelfde dataset wordt gebruikt, maar deze keer wordt er gefilterd op "Verbouwen of hergebruik".

**Vlaanderen:** toewijzing aan intersecties proportioneel naar `aantal_woningen` (zelfde logica
als bij nieuwbouw, maar met woningen als gewicht).

**Brussel:** geen renovatievergunningen beschikbaar op gemeenteniveau. We schatten renovaties
via het Vlaamse gemiddelde:

    renovaties per woning per jaar = (som toegewezen renovaties Vlaanderen)
                                   / (som woningen Vlaanderen in contour)

Elke Brusselse intersectie krijgt: `aantal_woningen × dat gemiddelde`.
"""
df = df.with_columns(aantal_vergunningen_renovatie=pl.lit(0.0))

df_vergunningen_renovatie = vergunningen_gemiddeld_per_gemeente(
    df_vergunningen,
    handeling="Verbouwen of hergebruik",
)

df_vla = wijs_proportioneel_toe(
    df.filter(pl.col("regio_nl") == "Vlaams Gewest"),
    df_vergunningen_renovatie,
    groep_kolom="naam_gemeente_nl",
    bron_groep_kolom="gemeente",
    bron_waarde_kolom="gemiddeld_per_jaar",
    gewicht_kolom="aantal_woningen",
    uitvoer_kolom="aantal_vergunningen_renovatie",
)

totaal_renovaties_vlaanderen = df_vla["aantal_vergunningen_renovatie"].sum()
totaal_woningen_vlaanderen = df_vla["aantal_woningen"].sum()
renovaties_per_woning_vlaanderen = (
    totaal_renovaties_vlaanderen / totaal_woningen_vlaanderen
)
st.write(
    "Gemiddeld aantal vergunde renovaties per woning per jaar in Vlaanderen (contour): "
    f"**{renovaties_per_woning_vlaanderen:.4f}** "
    f"({totaal_renovaties_vlaanderen:,.1f} renovaties / {totaal_woningen_vlaanderen:,.0f} woningen)"
)

df_br = df.filter(pl.col("regio_nl") == "Brussels Hoofdstedelijk Gewest").with_columns(
    aantal_vergunningen_renovatie=pl.col("aantal_woningen")
    * renovaties_per_woning_vlaanderen
)

df = pl.concat(
    [
        df_vla,
        df_br,
        df.filter(
            ~pl.col("regio_nl").is_in(
                ["Vlaams Gewest", "Brussels Hoofdstedelijk Gewest"]
            )
        ).with_columns(aantal_vergunningen_renovatie=pl.lit(0.0)),
    ]
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

Voor brussel is er geen informatie beschikbaar voor het aantal vergunningen met kwetsbare groepen, hierdoor nemen we het gemiddeld aantal vergunningen voor kwetsbare groepen tov nieuwbouwvergunningen van vlaanderen om dan dit aantal te vermenigvuldigen met het aantal nieuwbouwvergunningen in brussel.
"""
df_vergunningen_kwetsbare_groepen = pl.read_csv(
    "data/vergunningen_kwetsbare_functies_2026_lang.csv", separator=";"
)

df_vergunningen_kwetsbare_groepen = vergunningen_gemiddeld_per_gemeente(
    df_vergunningen_kwetsbare_groepen,
    handeling="Totalen",
    metriek="Aantal projecten",
    gebouw_functie=None,
)

df = wijs_proportioneel_toe(
    df,
    df_vergunningen_kwetsbare_groepen,
    groep_kolom="naam_gemeente_nl",
    bron_groep_kolom="gemeente",
    bron_waarde_kolom="gemiddeld_per_jaar",
    gewicht_kolom="aantal_percelen_onbebouwd_woongebied",
    uitvoer_kolom="aantal_vergunningen_kwetsbare_groepen",
)
totaal_vergunningen_nieuwbouw_vlaanderen = float(
    df.filter(pl.col("regio_nl") == "Vlaams Gewest")[
        "aantal_vergunningen_nieuwbouw"
    ].sum()
)
totaal_vergunningen_kwetsbare_groepen_vlaanderen = float(
    df.filter(pl.col("regio_nl") == "Vlaams Gewest")[
        "aantal_vergunningen_kwetsbare_groepen"
    ].sum()
)
ratio_kwetsbare_groepen_per_nieuwbouw_vlaanderen = (
    totaal_vergunningen_kwetsbare_groepen_vlaanderen
    / totaal_vergunningen_nieuwbouw_vlaanderen
)

st.write(
    f"Het totaal aantal nieuwbouwvergunningen per jaar in het Vlaams Gewest bedraagt {totaal_vergunningen_nieuwbouw_vlaanderen:,.0f}."
    f"Het totaal aantal vergunningen voor kwetsbare groepen per jaar in het Vlaams Gewest bedraagt {totaal_vergunningen_kwetsbare_groepen_vlaanderen:,.0f}."
    f"De ratio kwetsbare groepen / nieuwbouw in Vlaanderen bedraagt "
    f"**{ratio_kwetsbare_groepen_per_nieuwbouw_vlaanderen:.4f}**."
)
df = df.with_columns(
    aantal_vergunningen_kwetsbare_groepen=pl.when(pl.col("regio_nl") == "Vlaams Gewest")
    .then(pl.col("aantal_vergunningen_kwetsbare_groepen"))
    .when(pl.col("regio_nl") == "Brussels Hoofdstedelijk Gewest")
    .then(
        pl.col("aantal_vergunningen_nieuwbouw")
        * pl.lit(ratio_kwetsbare_groepen_per_nieuwbouw_vlaanderen)
    )
)
toon_staafdiagram_per_gewest(
    df,
    kolom="aantal_vergunningen_kwetsbare_groepen",
    titel="Vergunde projecten kwetsbare groepen per zone",
    y_label="Wooneenheden per jaar (gem.)",
)

"""
### Jaarlijks aantal renovaties met akoestische isolatie
We schatten in dat 20% van de renovaties die jaarlijks gebeuren zijn om akoestisch te isoleren.
"""
df = df.with_columns(
    jaarlijks_aantal_vergunningen_met_isolatie=pl.col("aantal_vergunningen_renovatie")
    * pl.lit(0.2)
)
toon_staafdiagram_per_gewest(
    df,
    kolom="jaarlijks_aantal_vergunningen_met_isolatie",
    titel="jaarlijks_aantal_vergunningen_met_isolatie",
    y_label="Renovaties met akoestische isolatie per jaar (gem.)",
)
"""
### Jaarlijks aantal renovaties zonder akoestische isolatie
We schatten in dat 20% van de renovaties die jaarlijks gebeuren zijn om akoestisch te isoleren.
"""
df = df.with_columns(
    jaarlijks_aantal_vergunningen_zonder_isolatie=pl.col(
        "aantal_vergunningen_renovatie"
    )
    * pl.lit(0.8)
)
toon_staafdiagram_per_gewest(
    df,
    kolom="jaarlijks_aantal_vergunningen_zonder_isolatie",
    titel="jaarlijks_aantal_vergunningen_zonder_isolatie",
    y_label="Renovaties zonder akoestische isolatie per jaar (gem.)",
)

"""
# Vragen
- Voor kwetsbare groepen weten we hoeveel projecten er zijn, maar weten we eigenlijk niet hoeveel wooneenheden of mensen hierin zitten. Hoe berekenen we dit?
- Voor onbebouwde onbebouwbare percelen hebben we momenteel nog geen data, dus er is een placeholder in de plaats waarbij we driemaal het aantal onbebouwde bebouwbare percelen nemen.
- Momenteel vertrekken we vanuit onbebouwde bebouwbare percelen om bij de flow te zeggen dat meer wooneenheden enkel hieruit ontstaan, dat is misschien zo in vlaanderen, maar in brussel zijn er weinig lege percelen. In brussel is het naar mijn aanname couranter dat 
"""
