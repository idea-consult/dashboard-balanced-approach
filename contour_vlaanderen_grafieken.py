"""Staafdiagrammen per gewest voor de contour Vlaanderen Streamlit-app."""

from __future__ import annotations

import altair as alt
import polars as pl
import streamlit as st

from contour_vlaanderen_kaart import toon_waarde_kaart

_GEWEST_BRUSSEL = "Brussels Hoofdstedelijk Gewest"
_GEWEST_VLAANDEREN = "Vlaams Gewest"
_GEWEST_KLEUREN = alt.Scale(domain=["Brussel", "Vlaanderen"], range=["#DD5B61", "#4E2567"])
_LDEN_MIN = 45
_LDEN_MAX = 75
_LDEN_BANDEN = [str(db) for db in range(_LDEN_MIN, _LDEN_MAX + 1)]
_DUO_LAYOUT_HOOGTE = 500

# Overschrijf in contour_vlaanderen.py tijdens ontwikkeling.
TOON_KAARTEN = True


def _lden_skelet(db_kolom: str) -> pl.DataFrame:
    return (
        pl.DataFrame({db_kolom: list(range(_LDEN_MIN, _LDEN_MAX + 1))})
        .join(pl.DataFrame({"gewest": ["Brussel", "Vlaanderen"]}), how="cross")
        .with_columns(pl.col(db_kolom).cast(pl.Utf8).alias("db_band"))
    )


def _gewest_chart_data(
    df: pl.DataFrame,
    kolom: str,
    *,
    regio_kolom: str = "regio_nl",
    db_kolom: str = "db_lden",
    aggregatie: str = "som",
    gewicht_kolom: str | None = None,
) -> pl.DataFrame:
    gefilterd = df.filter(pl.col(regio_kolom).is_in([_GEWEST_BRUSSEL, _GEWEST_VLAANDEREN]))

    if aggregatie == "gemiddelde":
        if gewicht_kolom is None:
            raise ValueError("gewicht_kolom is verplicht bij aggregatie='gemiddelde'")
        agg = (
            gefilterd.group_by(regio_kolom, db_kolom)
            .agg(
                (pl.col(kolom) * pl.col(gewicht_kolom)).sum().alias("_gewogen"),
                pl.col(gewicht_kolom).sum().alias("_gewicht"),
            )
            .with_columns(
                pl.when(pl.col("_gewicht") > 0)
                .then(pl.col("_gewogen") / pl.col("_gewicht"))
                .otherwise(None)
                .alias("waarde")
            )
            .drop("_gewogen", "_gewicht")
        )
    else:
        agg = gefilterd.group_by(regio_kolom, db_kolom).agg(
            pl.col(kolom).sum().alias("waarde")
        )

    agg = agg.with_columns(
        pl.when(pl.col(regio_kolom) == _GEWEST_BRUSSEL)
        .then(pl.lit("Brussel"))
        .otherwise(pl.lit("Vlaanderen"))
        .alias("gewest"),
        pl.col(db_kolom).cast(pl.Utf8).alias("db_band"),
    )

    return (
        _lden_skelet(db_kolom)
        .join(agg.select(db_kolom, "gewest", "waarde"), on=[db_kolom, "gewest"], how="left")
        .with_columns(pl.col("waarde").fill_null(0.0))
        .sort(db_kolom, "gewest")
    )


def staafdiagram_per_gewest(
    df: pl.DataFrame,
    kolom: str,
    *,
    titel: str,
    y_label: str,
    regio_kolom: str = "regio_nl",
    db_kolom: str = "db_lden",
    hoogte: int = 360,
    aggregatie: str = "som",
    gewicht_kolom: str | None = None,
    waarde_format: str = ",.0f",
) -> alt.Chart:
    chart_data = _gewest_chart_data(
        df,
        kolom,
        regio_kolom=regio_kolom,
        db_kolom=db_kolom,
        aggregatie=aggregatie,
        gewicht_kolom=gewicht_kolom,
    )
    is_gemiddelde = aggregatie == "gemiddelde"
    encode_y = alt.Y("waarde:Q", title=y_label, stack=None if is_gemiddelde else "zero")
    encode_kwargs: dict = {
        "x": alt.X(
            "db_band:O",
            title="LDEN-geluidsband (dB)",
            sort=_LDEN_BANDEN,
        ),
        "y": encode_y,
        "color": alt.Color("gewest:N", title="Gewest", scale=_GEWEST_KLEUREN),
        "tooltip": [
            alt.Tooltip("gewest:N", title="Gewest"),
            alt.Tooltip("db_band:O", title="dB"),
            alt.Tooltip("waarde:Q", title=y_label, format=waarde_format),
        ],
    }
    if is_gemiddelde:
        encode_kwargs["xOffset"] = "gewest:N"
    else:
        encode_kwargs["order"] = alt.Order("gewest:N", sort="ascending")

    return (
        alt.Chart(chart_data.to_pandas())
        .mark_bar()
        .encode(**encode_kwargs)
        .properties(title=titel, height=hoogte)
    )


def toon_staafdiagram_per_gewest(
    df: pl.DataFrame,
    kolom: str,
    *,
    titel: str,
    y_label: str,
    regio_kolom: str = "regio_nl",
    db_kolom: str = "db_lden",
    hoogte: int = 360,
    aggregatie: str = "som",
    gewicht_kolom: str | None = None,
    waarde_format: str = ",.0f",
    toon_kaart: bool | None = None,
    geometrie_kolom: str = "geometrie_inter_ss_lden",
) -> None:
    if toon_kaart is None:
        toon_kaart = TOON_KAARTEN

    kaart_df = df.filter(
        pl.col(regio_kolom).is_in([_GEWEST_BRUSSEL, _GEWEST_VLAANDEREN])
    )
    kaart_mogelijk = (
        toon_kaart
        and kolom in df.columns
        and geometrie_kolom in df.columns
        and not kaart_df.is_empty()
    )
    layout_hoogte = max(hoogte, _DUO_LAYOUT_HOOGTE) if kaart_mogelijk else hoogte

    chart = staafdiagram_per_gewest(
        df,
        kolom,
        titel=titel,
        y_label=y_label,
        regio_kolom=regio_kolom,
        db_kolom=db_kolom,
        hoogte=layout_hoogte,
        aggregatie=aggregatie,
        gewicht_kolom=gewicht_kolom,
        waarde_format=waarde_format,
    )

    if kaart_mogelijk:
        col_chart, col_map = st.columns(2)
        with col_chart:
            st.altair_chart(chart, use_container_width=True)
        with col_map:
            toon_waarde_kaart(
                kaart_df,
                kolom,
                y_label=y_label,
                geometrie_kolom=geometrie_kolom,
                waarde_format=waarde_format,
                hoogte=layout_hoogte,
            )
    else:
        st.altair_chart(chart, use_container_width=True)
