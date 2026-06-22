import struct

import polars as pl
import pydeck as pdk
import streamlit as st
from pyproj import Transformer

from contour.paths import POPULATION_SECTOR, POPULATION_SECTOR_SHEETS

_LAMBERT_NAAR_WGS84 = Transformer.from_crs("EPSG:31370", "EPSG:4326", always_xy=True)


def ewkb_hex_naar_wgs84(hex_geom: str) -> tuple[float, float]:
    """Zet PostGIS EWKB-hex (punt, EPSG:31370) om naar (lat, lon)."""
    x, y = struct.unpack("<dd", bytes.fromhex(hex_geom)[9:25])
    lon, lat = _LAMBERT_NAAR_WGS84.transform(x, y)
    return lat, lon


@st.cache_data
def laad_inwoners_met_coords(pad: str, sheet: str) -> pl.DataFrame:
    df = pl.read_excel(pad, sheet_name=sheet)
    coords = [ewkb_hex_naar_wgs84(g) for g in df["geom"].to_list()]
    return df.with_columns(
        lat=pl.Series([c[0] for c in coords], dtype=pl.Float64),
        lon=pl.Series([c[1] for c in coords], dtype=pl.Float64),
    )

# Vlaanderen contour
st.set_page_config(layout="wide")
st.title("Vlaanderen contour")
"""
- `onbebouwde_bebouwbare_percelen` — onbebouwde **bebouwbare** percelen per contour (stock; nog geen echte bron → placeholder 0)
- `onbebouwde_onbebouwbare_percelen` — onbebouwde **onbebouwbare** percelen per contour (stock; placeholder 0)
- `bewoonde_niet_geïsoleerde_woning` — bewoonde niet-geïsoleerde woningen (placeholder: 80% van woningen)
- `bewoonde_geïsoleerde_woning` — bewoonde geïsoleerde woningen (placeholder: 20% van woningen)
- `nieuwe_woning` — tussenstock nieuwbouw (start 0; gevuld door bouwflows)
- `perceel_eigendom_overheid` — percelen in publiek bezit (start 0)
- `woning_eigendom_overheid` — woningen in publiek bezit (start 0)

- `bebouwbare_percelen_woongebied(5jr)` — cumulatief aantal bebouwbare percelen door woongebied-aanduiding (laatste 5 jaar); jaarlijks $= \text{waarde} / 5$
- `niet_bebouwbare_percelen_woongebied_schrapping(5jr)` — cumulatief door schrapping woongebied (laatste 5 jaar); flow-teller, geen stock
- `alle_transacties_percelen` — totaal aantal perceeltransacties (`sum_ParcelsNumber`, segment o.a. `industrie_terrein`)
- `alle_verkopen_onbebouwde_bebouwbare_percelen` — perceelverkopen gefilterd op onbebouwde bebouwbare percelen (nog te koppelen CaPaKey → contour)
- `alle_transacties_woningen` — totaal woningtransacties (`woningen` + `appartementen`, `sum_ParcelsNumber`)
- `alle_verkopen_woningen` — alle woningverkopen (zelfde bron; geen iso-split)
- `vergunde_wooneenheden_nieuwbouw` — vergunde wooneenheden, handeling `Nieuwbouw` (omgevingsloket)
- `gem_wooneenheden_per_vergunning` — `Aantal wooneenheden` / `Aantal projecten` (afgeleid)
- `vergunningen_kwetsbare_groep` — vergunningen kwetsbare functies (`Aantal projecten` of wooneenheden)
- `renovatie_totaal` — vergunningen `Verbouwen of hergebruik` (`Aantal projecten`)
- $R^{+}$ — renovaties **met** isolatie (jaarlijks; nog geen iso-split in data)
- $R^{-}$ — renovaties **zonder** isolatie (jaarlijks; idem)
- `nieuwbouw_geïsoleerd` / `nieuwbouw_niet_geïsoleerd` — nieuwbouw per iso-type (af te leiden; geen directe kolom)
- `potentieel_isoleerbare_woningen` — woningen akoestisch isoleerbaar via geluidsbuffers (nog niet gemodelleerd)
- `inwoners_per_contour` — inwoners Vlaanderen + Brussel per band (KPI’s, geen flow-noemer)
"""
df_inwoners_contour_stat = pl.read_excel(
    POPULATION_SECTOR,
    sheet_name=POPULATION_SECTOR_SHEETS["lden"],
)

"""
We willen graag de data op het niveau krijgen van een 1 db contour gekruisd met de statistische sectoren:
Daarom gaan we eerst een lijst maken van alle kruisingen tussen contouren en sectoren.
Daarnaast gaan we ook de volgende kolommen meedoen:

- T_REGIO_NL - regio: vlaamse gewest of brussels gewest
- T_MUN_NL - gemeente: de naam van de gemeente
- T_SEC_NL - sector: de naam van de statistische sector
- dB - de dB waarde van het contour
- fid - het id van de overlap tussen contour en sector

Deze halen we gewoon uit df_inwoners_contour_stat

inwoners_per_contour
Vanuit het departement omgeving kregen we data over de precieze woonplaats van vlaamse inwoners rond de luchthaven. Deze werd via GIS toegewezen aan een overlap tussen 1db contouren en statistische sectoren.
Voor Brussel werd geen data bekomen op het niveau van de woning, hierdoor werd de data opgevraagd op het niveau van de statistische sectoren.
"""
df_lden = df_inwoners_contour_stat.select(
    "fid",
    "dB",
    pl.col("T_REGIO_NL").alias("gewest"),
    pl.col("T_MUN_NL").alias("gemeente"),
    pl.col("T_SEC_NL").alias("sector"),
    pl.col("Population dans le contour").alias("inwoners"),
)

vergunningen_omgevingsloket = pl.read_csv(
    "data/vergunningen_omgevingsloket_2026_lang.csv",
    separator=";",
)

"""
In het dataframe niet_geaggregeerde_inwoners staan de niet geaggregeerde inwoners van Vlaanderen. Om de inwoners per overlap van statistische sector en contour te berekenen, moet de data gesommeerd worden over id_inter_ss_lden.

Om te weten hoeveel woningen er zijn per overlap van statistische sector en contour, moet het aantal rijen per id_inter_ss_lden worden geteld.
"""
niet_geaggregeerde_inwoners = laad_inwoners_met_coords(
    "data/niet geaggregeerde inwoners vlaanderen.xlsx",
    "inhabitants_centroids_lden",
)

st.subheader("Kaart inwoners per woning (Vlaanderen)")
min_inwoners = st.slider("Minimum inwoners op kaart", 0, 10, 1)
kaart_data = niet_geaggregeerde_inwoners.filter(pl.col("inwoners") >= min_inwoners)
st.caption(
    f"{kaart_data.height:,} punten getoond (van {niet_geaggregeerde_inwoners.height:,} woningen)."
)

if kaart_data.is_empty():
    st.info("Geen punten om te tonen met dit filter.")
else:
    kaart_pandas = kaart_data.select(
        "id",
        "inwoners",
        "id_db_lden",
        "lat",
        "lon",
    ).with_columns(
        (pl.col("inwoners").clip(lower_bound=1) * 25).alias("radius"),
    ).to_pandas()

    midden_lat = kaart_pandas["lat"].mean()
    midden_lon = kaart_pandas["lon"].mean()

    st.pydeck_chart(
        pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=pdk.ViewState(
                latitude=midden_lat,
                longitude=midden_lon,
                zoom=10,
                pitch=0,
            ),
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=kaart_pandas,
                    get_position=["lon", "lat"],
                    get_radius="radius",
                    get_fill_color=[220, 60, 30, 160],
                    pickable=True,
                ),
            ],
            tooltip={
                "html": "<b>Inwoners:</b> {inwoners}<br/><b>dB:</b> {id_db_lden}<br/><b>ID:</b> {id}",
                "style": {"backgroundColor": "steelblue", "color": "white"},
            },
        )
    )

inwoners_per_overlap = (
    niet_geaggregeerde_inwoners.with_columns(
        pl.col("id_inter_ss_lden").cast(pl.Int64),
    )
    .group_by("id_inter_ss_lden")
    .agg(
        pl.col("inwoners").sum().alias("inwoners_vla"),
        pl.col("id").count().alias("woningen"),
    )
    .rename({"id_inter_ss_lden": "fid"})
)
st.dataframe(inwoners_per_overlap)

df_lden = (
    df_lden.join(inwoners_per_overlap, on="fid", how="left")
    .with_columns(
        pl.when(pl.col("gewest") == "Vlaams Gewest")
        .then(pl.col("inwoners_vla"))
        .otherwise(pl.col("inwoners"))
        .alias("inwoners")
    )
    .drop("inwoners_vla")
)

st.dataframe(df_lden)

# Vergunningen
st.subheader("Vergunningen")
st.dataframe(vergunningen_omgevingsloket)
st.write(vergunningen_omgevingsloket["handeling"].unique())
st.write(vergunningen_omgevingsloket["gebouw_functie"].unique())
st.write(vergunningen_omgevingsloket["metriek"].unique())
