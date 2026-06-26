
import polars as pl
import streamlit as st

import contour_vlaanderen_grafieken as grafieken
from contour_vlaanderen_grafieken import toon_staafdiagram_per_gewest
from contour_vlaanderen_kaart import toon_geometrie_waarschuwing, toon_overlap_kaart
from contour_vlaanderen_kolommen import KOLOM_HERNAMING, toon_kolomdocumentatie
from contour_vlaanderen_transacties import (
    APPARTEMENT_TRANSACTIE_HERNAMING,
    PERCEEL_TRANSACTIE_HERNAMING,
    PERCEEL_TRANSACTIE_SEGMENTEN,
    WONING_TRANSACTIE_HERNAMING,
    aggregeer_transacties_naar_sector,
    toon_perceel_transactie_kolomdocumentatie,
    toon_transactie_kolomdocumentatie,
)
from contour_vlaanderen_vergunningen import (
    vergunningen_gemiddeld_per_gemeente,
    wijs_proportioneel_toe,
)

# uv run streamlit run contour_analyse_1.py
# uv run pytest tests/test_vergunningen_toewijzing.py -v

TOON_KAARTEN = st.toggle("Toon kaarten", value=False)
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

Dit script bouwt variabele voor variabele een dataset op intersectieniveau op. Elke sectie
voegt kolommen toe aan `df`; het eindresultaat wordt weggeschreven naar `data_2/data_2.csv`
voor de flow-analyse in `contour_analyse_2.py`.
"""
st.caption("Sector–contour-overlappen rond de luchthaven (LDEN, Vlaanderen + Brussel)")

"""
## Inladen basisbestand

#### Bron
`data_1/20260624 data vlaanderen 1 lden.csv` — overlap-tabel sector × LDEN-contour.

#### Bewerkingen
1. **Inlezen** met Europese CSV-instellingen: `;` als scheidingsteken, `,` als decimaalteken.
2. **Hernoemen** van kolommen via `KOLOM_HERNAMING` (leesbare Python-namen).
3. Optioneel: kaart en kolomoverzicht tonen (toggle *Toon kaarten*).

#### Output
`df` met één rij per intersectie; geometry en administratieve sleutels blijven behouden.
"""
# Europese CSV: puntkomma als scheidingsteken, komma als decimaalteken
df = pl.read_csv(
    "data_1/20260624 data vlaanderen 1 lden.csv",
    separator=";",
    encoding="utf-8",
    decimal_comma=True,
    infer_schema_length=10000,
).rename(KOLOM_HERNAMING)

if TOON_KAARTEN:
    toon_geometrie_waarschuwing(df)

with st.expander("Kolomoverzicht & uitleg", expanded=False):
    toon_kolomdocumentatie()

st.subheader("Kaart")

if TOON_KAARTEN:
    toon_overlap_kaart(df)

st.subheader("Data")
st.caption(f"{df.height:,} rijen · {df.width} kolommen")

"""
## Basisdata

### Inwoners

#### Bron
- **Vlaanderen:** `inwoners_client` — adresniveau, toegekend aan overlap (Departement Omgeving).
- **Brussel:** `inwoners_overlap` — sectorniveau, naar overlap gespreid op oppervlakte.
- **Overig (Waals Gewest):** `inwoners_overlap`.

#### Bewerkingen
1. Nieuwe kolom `inwoners` via `pl.when` op `regio_nl`.
2. Per gewest de meest geschikte bronkolom kiezen (geen herberekening, wel harmonisatie).

#### Visualisatie
Staafdiagram per LDEN-band, opgesplitst naar Vlaanderen vs. Brussel (som per band).
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

#### Doel
Eén referentiewaarde voor Brussel, waar geen woningtelling op adresniveau beschikbaar is.

#### Bewerkingen
1. Filter `df` op Vlaams Gewest.
2. **Totaal inwoners** en **totaal woningen** optellen over alle intersecties.
3. **Delen:** `gemiddelde_inwoners_per_woning = totaal_inwoners / totaal_woningen`.
4. Waarde tonen in de app (één getal voor heel Vlaanderen in de contour).

#### Gebruik
Dit gemiddelde wordt in de volgende stap gebruikt om Brusselse woningen te schatten.
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

#### Bron
- **Vlaanderen:** bestaande kolom `aantal_woningen` (adresniveau).
- **Brussel:** afgeleid uit inwoners.

#### Bewerkingen
1. Voor Brussel: `aantal_woningen = inwoners / gemiddelde_inwoners_per_woning`.
2. Voor overige gewesten: originele `aantal_woningen` behouden.

#### Visualisatie
Staafdiagram per LDEN-band en gewest.
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

#### Bron
`aantal_percelen_onbebouwd_woongebied` — gemeten op adresniveau (Vlaanderen).

#### Bewerkingen
1. Kolom kopiëren naar `onbebouwde_bebouwbare_percelen` (geen transformatie).

#### Visualisatie
Staafdiagram per LDEN-band en gewest.
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

#### Bron
Geen directe meting — **placeholder**.

#### Bewerkingen
1. `onbebouwde_onbebouwbare_percelen = aantal_percelen_onbebouwd_woongebied × 3`.

#### Opmerking
Factor 3 is een tijdelijke schatting tot echte stockdata beschikbaar is; beïnvloedt o.a.
woongebiedverbod-flows in analyse 2.
"""
df = df.with_columns(
    onbebouwde_onbebouwbare_percelen=pl.col("aantal_percelen_onbebouwd_woongebied")
    * pl.lit(3)
)
toon_staafdiagram_per_gewest(
    df,
    "onbebouwde_onbebouwbare_percelen",
    titel="Onbebouwde onbebouwbare percelen",
    y_label="Aantal onbebouwde onbebouwbare percelen",
)
"""
### Bewoonde_niet_geïsoleerde_woning

#### Bron
Geen isolatieregister per woning — **gewestaannames** (placeholder).

#### Bewerkingen
1. `bewoonde_niet_geïsoleerde_woning = aantal_woningen × aandeel` per `regio_nl`:
   - Vlaanderen: **80%**
   - Brussel: **95%** (expert opinion)
   - Overig: **80%**

#### Visualisatie
Staafdiagram per LDEN-band en gewest.
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

#### Bewerkingen
1. Complement van de verdeling hierboven op `aantal_woningen`:
   - Vlaanderen: **20%**
   - Brussel: **5%**
   - Overig: **20%**

#### Opmerking
Niet-geïsoleerd + geïsoleerd = totaal `aantal_woningen` per intersectie.
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

#### Bewerkingen
1. `nieuwe_woning = 0` voor alle intersecties.

#### Opmerking
Tussenstock voor de simulator; nieuwbouwvolume zit in `aantal_vergunningen_nieuwbouw`.
"""
df = df.with_columns(nieuwe_woning=pl.lit(0.0))
"""
### Perceel eigendom overheid

#### Bewerkingen
1. `perceel_eigendom_overheid = 0` — interne simulatorstock, nog niet gevuld vanuit data.
"""
df = df.with_columns(perceel_eigendom_overheid=pl.lit(0))
"""
### Woning eigendom overheid

#### Bewerkingen
1. `woning_eigendom_overheid = 0` — doelstock voor aankoop/voorkooprecht/onteigening flows.
"""
df = df.with_columns(woning_eigendom_overheid=pl.lit(0))

"""
### Woongebied-mutaties (onbebouwbaar ↔ bebouwbaar)

Jaarlijkse planologische verschuivingen tussen onbebouwbaar en bebouwbare percelen.

#### Bron
- Excel `data_1/20260622 data vlaanderen 2 bebouwbaar en onbebouwbaar.xlsx`, blad `lden`:
  jaarlijks gemiddelde 2021–2026 per LDEN-band.
- Oppervlakte-intersecties uit `df` (alleen Vlaanderen).

#### Bewerkingen
1. **Oppervlakte per band:** som `oppervlakte_overlap_m2` per `db_lden` (filter Vlaams Gewest)
   → `totaal_overlap_m2_vla`.
2. **Join** `oppervlakte_per_db` en mutatietabel op `db_lden` aan `df`.
3. **Proportionele verdeling** per intersectie (Vlaanderen):
   - `onbebouwbaar_naar_bebouwbaar = bandtotaal / totaal_overlap_m2_vla × oppervlakte_overlap_m2`
   - `bebouwbaar_naar_onbebouwbaar` idem met andere teller.
4. **Brussel en Waals Gewest:** beide kolommen = `0` (geen woongebied-creatie in bron).
5. Tijdelijke Excel-kolommen verwijderen uit `df`.

#### Visualisatie
Twee staafdiagrammen: onbebouwbaar→bebouwbaar en bebouwbaar→onbebouwbaar per gewest.
"""
df_bebouwbaar_onbebouwbaar = pl.read_excel(
    "data_1/20260622 data vlaanderen 2 bebouwbaar en onbebouwbaar.xlsx",
    sheet_name="lden",
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
### Bebouwbaar naar onbebouwbaar

Zelfde berekening als hierboven; kolom `bebouwbaar_naar_onbebouwbaar` is al aangemaakt.
Alleen visualisatie in deze stap.
"""
toon_staafdiagram_per_gewest(
    df,
    kolom="bebouwbaar_naar_onbebouwbaar",
    titel="Bebouwbaar naar onbebouwbaar",
    y_label="Aantal percelen",
)

"""
### Totaal aantal transacties van woningen

#### Doel
Jaarlijks transactievolume en prijs per intersectie — input voor aankoopbeleid, voorkooprecht
en prijsanalyses.

#### Brondata
`data_1/transacties_vastgoed/20260624 transacties_woningen.csv` en
`… transacties_appartementen.csv` (puntkomma; één rij = één CaPaKey).

#### Prijzen: gemeten vs. ingevuld
| Suffix | Betekenis |
|--------|-----------|
| `_gemeten` | Mediaan uit voldoende transacties (GDPR-publicatie) |
| `_ingevuld` | GIS-buren voor sectoren met te weinig transacties |

We gebruiken steeds **ingevulde P50** (`*_prijs_p50_ingevuld`); transactietelling blijft werkelijk volume.

#### Bewerkingen — CaPaKey-niveau
1. **Inlezen** beide CSV's; kolommen hernoemen.
2. **Full join** woningen + appartementen op `capakey` (geen verlies bij één segment).
3. **Transacties:** `aantal_woning_transacties_per_jaar = huis + appartement` (null → 0).
4. **Prijs per CaPaKey:**
   - Met transacties: transactiegewogen gemiddelde P50 huis/appartement.
   - Zonder transacties: `mean_horizontal` van beide P50 (voorkomt NaN in prijsgrafiek).

#### Bewerkingen — sectorniveau
5. `nis_sector` = `capakey` zonder trailing `-`.
6. **Aggregeren** per sector: som transacties; sectorprijs = transactiegewogen gemiddelde
   CaPaKey-prijzen (of gewoon gemiddelde bij 0 transacties).

#### Bewerkingen — intersectieniveau
7. `nis_sector` in `df` normaliseren (zelfde strip).
8. **`wijs_proportioneel_toe`:** sectorale transacties verdelen over intersecties
   proportioneel naar `aantal_woningen`; sectorprijs wordt doorgegeven (`doorgeef_kolommen`).

#### Visualisatie
Staafdiagram transacties per jaar per gewest en LDEN-band.
"""
df_huis_transacties = pl.read_csv(
    "data_1/transacties_vastgoed/20260624 transacties_woningen.csv",
    separator=";",
    encoding="utf-8",
    infer_schema_length=10000,
    null_values=[""],
).rename(WONING_TRANSACTIE_HERNAMING)
df_appartement_transacties = pl.read_csv(
    "data_1/transacties_vastgoed/20260624 transacties_appartementen.csv",
    separator=";",
    encoding="utf-8",
    infer_schema_length=10000,
    null_values=[""],
).rename(APPARTEMENT_TRANSACTIE_HERNAMING)

with st.expander("Transactiekolommen (woningen & appartementen)", expanded=False):
    toon_transactie_kolomdocumentatie()
    st.caption("Woningen — hernoemde kolommen")
    st.write(df_huis_transacties.columns)
    st.caption("Appartementen — hernoemde kolommen")
    st.write(df_appartement_transacties.columns)

# Per CaPaKey: som transacties (woning + appartement) en gewogen gemiddelde prijs
df_woning_transacties = (
    df_huis_transacties.join(
        df_appartement_transacties,
        on="capakey",
        how="full",
        coalesce=True,
    )
    .with_columns(
        w_huis=pl.col("huis_aantal_transacties").fill_null(0),
        w_app=pl.col("appartement_aantal_transacties").fill_null(0),
    )
    .with_columns(
        aantal_woning_transacties_per_jaar=pl.col("w_huis") + pl.col("w_app"),
    )
    .with_columns(
        gemiddelde_prijs_van_een_woning=pl.when(pl.col("w_huis") + pl.col("w_app") > 0)
        .then(
            (
                pl.col("huis_prijs_p50_ingevuld") * pl.col("w_huis")
                + pl.col("appartement_prijs_p50_ingevuld") * pl.col("w_app")
            )
            / (pl.col("w_huis") + pl.col("w_app"))
        )
        .otherwise(
            pl.mean_horizontal(
                "huis_prijs_p50_ingevuld",
                "appartement_prijs_p50_ingevuld",
            )
        ),
    )
)

# Aggregeer naar statistische sector (capakey zonder trailing "-")
df_transacties_sector = (
    df_woning_transacties.with_columns(
        nis_sector=pl.col("capakey").str.strip_chars_end("-"),
    )
    .group_by("nis_sector")
    .agg(
        pl.col("aantal_woning_transacties_per_jaar").sum(),
        pl.when(pl.col("aantal_woning_transacties_per_jaar").sum() > 0)
        .then(
            (
                pl.col("gemiddelde_prijs_van_een_woning")
                * pl.col("aantal_woning_transacties_per_jaar")
            ).sum()
            / pl.col("aantal_woning_transacties_per_jaar").sum()
        )
        .otherwise(pl.col("gemiddelde_prijs_van_een_woning").mean())
        .alias("gemiddelde_prijs_van_een_woning"),
    )
)

# Toewijzen aan intersecties: gewicht = aantal_woningen binnen dezelfde sector
df = df.with_columns(pl.col("nis_sector").str.strip_chars_end("-"))
df = wijs_proportioneel_toe(
    df,
    df_transacties_sector,
    groep_kolom="nis_sector",
    bron_waarde_kolom="aantal_woning_transacties_per_jaar",
    gewicht_kolom="aantal_woningen",
    uitvoer_kolom="aantal_woning_transacties_per_jaar",
    doorgeef_kolommen=("gemiddelde_prijs_van_een_woning",),
)

toon_staafdiagram_per_gewest(
    df,
    kolom="aantal_woning_transacties_per_jaar",
    titel="Aantal transacties per jaar",
    y_label="Aantal transacties",
)
"""
### Aantal transacties niet-geïsoleerde en geïsoleerde woningen

#### Bron
`aantal_woning_transacties_per_jaar` (vorige sectie) — geen isolatie per transactie.

#### Bewerkingen
1. Zelfde gewestaandelen als bewoonde stocks vermenigvuldigen met totaal transacties:
   - Vlaanderen: 80% / 20%
   - Brussel: 95% / 5%
2. Twee nieuwe kolommen:
   - `aantal_transacties_niet_geïsoleerde_woningen`
   - `aantal_transacties_geïsoleerde_woningen`
3. Som van beide = totaal transacties per intersectie.

#### Visualisatie
Twee staafdiagrammen (niet-geïsoleerd / geïsoleerd) per gewest.
"""
df = df.with_columns(
    aantal_transacties_niet_geïsoleerde_woningen=pl.when(
        pl.col("regio_nl") == "Brussels Hoofdstedelijk Gewest"
    )
    .then(pl.col("aantal_woning_transacties_per_jaar") * 0.95)
    .when(pl.col("regio_nl") == "Vlaams Gewest")
    .then(pl.col("aantal_woning_transacties_per_jaar") * 0.80)
    .otherwise(pl.col("aantal_woning_transacties_per_jaar") * 0.80),
    aantal_transacties_geïsoleerde_woningen=pl.when(
        pl.col("regio_nl") == "Brussels Hoofdstedelijk Gewest"
    )
    .then(pl.col("aantal_woning_transacties_per_jaar") * 0.05)
    .when(pl.col("regio_nl") == "Vlaams Gewest")
    .then(pl.col("aantal_woning_transacties_per_jaar") * 0.20)
    .otherwise(pl.col("aantal_woning_transacties_per_jaar") * 0.20),
)
toon_staafdiagram_per_gewest(
    df,
    kolom="aantal_transacties_niet_geïsoleerde_woningen",
    titel="Transacties niet-geïsoleerde woningen per jaar",
    y_label="Aantal transacties",
)
toon_staafdiagram_per_gewest(
    df,
    kolom="aantal_transacties_geïsoleerde_woningen",
    titel="Transacties geïsoleerde woningen per jaar",
    y_label="Aantal transacties",
)
"""
### Gemiddelde prijs van een woning

#### Bron
`gemiddelde_prijs_van_een_woning` — al toegekend per intersectie via sectoraggregatie
(transactiesectie).

#### Bewerkingen
Geen extra kolomberekening; alleen visualisatie.

#### Visualisatie
Per LDEN-band: transactiegewogen gemiddelde prijs per gewest
(`aggregatie="gemiddelde"`, gewicht = `aantal_woning_transacties_per_jaar`).
"""
toon_staafdiagram_per_gewest(
    df,
    kolom="gemiddelde_prijs_van_een_woning",
    titel="Gemiddelde prijs van een woning",
    y_label="Gemiddelde prijs (€)",
    aggregatie="gemiddelde",
    gewicht_kolom="aantal_woning_transacties_per_jaar",
    waarde_format=",.0f",
)

"""
### Totaal aantal transacties van percelen

#### Doel
Jaarlijks transactievolume en prijs per intersectie voor onbebouwde **bebouwbare** percelen —
input voor aankoopbeleid, voorkooprecht en prijsanalyses.

#### Brondata
`data_1/20260625 data vlaanderen 3 transacties percelen.csv` (tabs gescheiden; één rij per
CaPaKey). Enkel segment `terrain_batissable` wordt ingelezen.

#### Bewerkingen — CaPaKey-niveau
1. **Inlezen** met tab als scheidingsteken; enkel bebouwbare kolommen selecteren en hernoemen
   via `PERCEEL_TRANSACTIE_HERNAMING`.
2. Transactietelling en P50-prijs per CaPaKey.

#### Bewerkingen — sectorniveau
3. `nis_sector` = `capakey` zonder trailing `-`.
4. **Aggregeren** per sector: som transacties; sectorprijs = transactiegewogen gemiddelde
   CaPaKey-prijzen (of gewoon gemiddelde bij 0 transacties).

#### Bewerkingen — intersectieniveau
5. **`wijs_proportioneel_toe`:** gewicht `onbebouwde_bebouwbare_percelen`; sectorprijs wordt
   doorgegeven (`doorgeef_kolommen`).

#### Visualisatie
Twee staafdiagrammen: transacties en gemiddelde prijs per gewest en LDEN-band.
"""
df_perceel_transacties = (
    pl.read_csv(
        "data_1/20260625 data vlaanderen 3 transacties percelen.csv",
        separator="\t",
        encoding="utf-8",
        infer_schema_length=10000,
        null_values=[""],
    )
    .select(list(PERCEEL_TRANSACTIE_HERNAMING.keys()))
    .rename(PERCEEL_TRANSACTIE_HERNAMING)
)

with st.expander("Transactiekolommen (percelen)", expanded=False):
    toon_perceel_transactie_kolomdocumentatie()
    st.caption("Hernoemde kolommen")
    st.write(df_perceel_transacties.columns)

for segment in PERCEEL_TRANSACTIE_SEGMENTEN:
    df_transacties_sector = aggregeer_transacties_naar_sector(
        df_perceel_transacties,
        transactie_kolom=segment["aantal_kolom"],
        prijs_kolom=segment["prijs_kolom"],
        transacties_uitvoer=segment["transacties_uitvoer"],
        prijs_uitvoer=segment["prijs_uitvoer"],
    )
    df = wijs_proportioneel_toe(
        df,
        df_transacties_sector,
        groep_kolom="nis_sector",
        bron_waarde_kolom=segment["transacties_uitvoer"],
        gewicht_kolom=segment["gewicht_kolom"],
        uitvoer_kolom=segment["transacties_uitvoer"],
        doorgeef_kolommen=(segment["prijs_uitvoer"],),
    )
    toon_staafdiagram_per_gewest(
        df,
        kolom=segment["transacties_uitvoer"],
        titel=f"Aantal transacties — {segment['label']}",
        y_label="Aantal transacties",
    )
    toon_staafdiagram_per_gewest(
        df,
        kolom=segment["prijs_uitvoer"],
        titel=f"Gemiddelde prijs — {segment['label']}",
        y_label="Gemiddelde prijs (€)",
        aggregatie="gemiddelde",
        gewicht_kolom=segment["transacties_uitvoer"],
        waarde_format=",.0f",
    )

"""
### Aantal vergunningen nieuwbouw

#### Bron
- **Vlaanderen:** `vergunningen_omgevingsloket_2026_lang.csv`, handeling *Nieuwbouw*.
- **Brussel:** Excel evolutie geregistreerd woningbestand 2021–2025.

#### Bewerkingen — Vlaanderen
1. Kolom `aantal_vergunningen_nieuwbouw` initialiseren op 0.
2. **`vergunningen_gemiddeld_per_gemeente`:** gemiddeld aantal wooneenheden/jaar 2021–2025 per gemeente.
3. **`wijs_proportioneel_toe`** op Vlaamse intersecties:
   - groep: `naam_gemeente_nl`
   - gewicht: `onbebouwde_bebouwbare_percelen`
   - conservatie: som per gemeente = bronwaarde (getest in pytest).

#### Bewerkingen — Brussel
4. Per gemeente: jaarlijkse groei = gemiddelde van vier jaar-op-jaar verschillen (2021→2025).
5. Groei toewijzen via `wijs_proportioneel_toe` met gewicht `aantal_woningen`.
6. Totalen tonen: heel gewest (19 gem.) vs. contour (17 gem.).

#### Bewerkingen — afronding
7. **`pl.concat`:** Vlaanderen + Brussel + overige gewesten (0 vergunningen).

#### Uitzondering
Gemeenten met vergunningen in bron maar **0** onbebouwde woongebied-percelen in de contour
(Hoeilaart, Tielt-Winge, Kapelle-op-den-Bos) krijgen 0 toegewezen op intersectieniveau.

#### Visualisatie
Staafdiagram vergunde wooneenheden nieuwbouw per gewest.
"""
df = df.with_columns(aantal_vergunningen_nieuwbouw=pl.lit(0.0))

# --- Vlaanderen: omgevingsloket ---
df_vergunningen = pl.read_csv(
    "data_1/vergunningen_omgevingsloket_2026_lang.csv", separator=";"
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
    "data_1/20260624 data brussel aantal woningen.xlsx",
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

#### Bron
Zelfde omgevingsloket-CSV; handeling *Verbouwen of hergebruik*.

#### Bewerkingen — Vlaanderen
1. `aantal_vergunningen_renovatie` initialiseren op 0.
2. Gemeentegemiddelde berekenen (`vergunningen_gemiddeld_per_gemeente`).
3. **`wijs_proportioneel_toe`** met gewicht `aantal_woningen` (niet onbebouwde percelen).
4. **Ratio berekenen:** totaal renovaties VL / totaal woningen VL in contour.

#### Bewerkingen — Brussel
5. Geen renovatiebron → `aantal_vergunningen_renovatie = aantal_woningen × ratio_Vlaanderen`.

#### Bewerkingen — afronding
6. **`pl.concat`:** Vlaanderen + Brussel + overige (0).

#### Visualisatie
Staafdiagram vergunde renovaties per gewest.
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

#### Bron
- **Vlaanderen:** `vergunningen_kwetsbare_functies_2026_lang.csv` (aantal projecten/jaar).
- **Brussel:** geen directe data — proxy via Vlaamse ratio.

#### Bewerkingen — Vlaanderen
1. Gemeentegemiddelde projecten (`vergunningen_gemiddeld_per_gemeente`, metriek *Aantal projecten*).
2. **`wijs_proportioneel_toe`** met gewicht `aantal_percelen_onbebouwd_woongebied`.

#### Bewerkingen — Brussel
3. **Ratio VL:** som kwetsbare groepen / som nieuwbouw (Vlaanderen, contour).
4. Brusselse intersecties: `aantal_vergunningen_kwetsbare_groepen =
   aantal_vergunningen_nieuwbouw × ratio` (via `pl.when` op `regio_nl`).

#### Opmerking
We tellen **projecten**, niet wooneenheden per project.

#### Visualisatie
Staafdiagram per gewest.
"""
df_vergunningen_kwetsbare_groepen = pl.read_csv(
    "data_1/vergunningen_kwetsbare_functies_2026_lang.csv", separator=";"
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

#### Bewerkingen
1. `jaarlijks_aantal_vergunningen_met_isolatie = aantal_vergunningen_renovatie × 0,20`
   (**placeholder:** 20% van renovaties met akoestische isolatie).

#### Visualisatie
Staafdiagram per gewest.
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

#### Bewerkingen
1. `jaarlijks_aantal_vergunningen_zonder_isolatie = aantal_vergunningen_renovatie × 0,80`
   (complement van 20% met isolatie).

#### Visualisatie
Staafdiagram per gewest.
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

df.write_csv("data_2/data_2.csv")
"""
## Export

#### Bewerkingen
1. Volledige `df` wegschrijven naar `data_2/data_2.csv` — input voor `contour_analyse_2.py`.

# Openstaande vragen

- Kwetsbare groepen: aantal **projecten** bekend, wooneenheden per project niet.
- Onbebouwde onbebouwbare percelen = 3× placeholder.
- Nieuwbouw in Brussel via woningbestand-groei; in Vlaanderen via woongebied-percelen — asymmetrie
  met weinig lege percelen in Brussel.
- Perceeltransacties: enkel `terrain_batissable` (bebouwbaar); prijs = P50 zonder GIS-imputatie.
"""
