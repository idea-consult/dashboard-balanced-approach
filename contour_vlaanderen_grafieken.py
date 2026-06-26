"""Staafdiagrammen per gewest voor de contour Vlaanderen Streamlit-app."""

from __future__ import annotations

import altair as alt
import polars as pl
import streamlit as st

from contour_vlaanderen_kaart import toon_waarde_kaart

_GEWEST_BRUSSEL = "Brussels Hoofdstedelijk Gewest"
_GEWEST_VLAANDEREN = "Vlaams Gewest"
_GEWEST_KLEUREN = alt.Scale(domain=["Brussel", "Vlaanderen"], range=["#DD5B61", "#4E2567"])
_FLOW_TOESTAND_KLEUREN = alt.Scale(domain=["Baseline", "Active"], range=["#4E2567", "#DD5B61"])
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


def _lden_skelet_enkel(db_kolom: str) -> pl.DataFrame:
    """Één rij per LDEN-band (zonder gewest-splitsing)."""
    return pl.DataFrame({db_kolom: list(range(_LDEN_MIN, _LDEN_MAX + 1))}).with_columns(
        pl.col(db_kolom).cast(pl.Utf8).alias("db_band")
    )


def _flow_kolommen(measure_id: str) -> tuple[str, str]:
    return f"{measure_id}_baseline", f"{measure_id}_active"


def _flow_rate_chart_data(
    df: pl.DataFrame,
    measure_id: str,
    *,
    db_kolom: str = "db_lden",
) -> pl.DataFrame:
    """Zet flow-rate kolommen om naar lang formaat voor het staafdiagram.

    Verwacht één rij per LDEN-band met ``{measure_id}_baseline`` en ``*_active``.
    Geen aggregatie — die gebeurt in ``contour_analyse_2.py`` vóór de flow-berekening.
    """
    baseline_kolom, active_kolom = _flow_kolommen(measure_id)
    for kolom in (baseline_kolom, active_kolom):
        if kolom not in df.columns:
            raise ValueError(f"Kolom '{kolom}' ontbreekt in df")

    lang = (
        df.select(
            db_kolom,
            pl.col(baseline_kolom).fill_nan(0.0).alias("baseline"),
            pl.col(active_kolom).fill_nan(0.0).alias("active"),
        )
        .unpivot(
            on=["baseline", "active"],
            index=db_kolom,
            variable_name="toestand",
            value_name="waarde",
        )
        .with_columns(
            pl.when(pl.col("toestand") == "baseline")
            .then(pl.lit("Baseline"))
            .otherwise(pl.lit("Active"))
            .alias("toestand"),
            pl.col(db_kolom).cast(pl.Utf8).alias("db_band"),
        )
    )

    skelet = _lden_skelet_enkel(db_kolom).join(
        pl.DataFrame({"toestand": ["Baseline", "Active"]}),
        how="cross",
    )

    return (
        skelet.join(lang.select(db_kolom, "toestand", "waarde"), on=[db_kolom, "toestand"], how="left")
        .with_columns(pl.col("waarde").fill_null(0.0))
        .sort(db_kolom, "toestand")
    )


def staafdiagram_flow_rate(
    df: pl.DataFrame,
    measure_id: str,
    *,
    titel: str,
    y_label: str = "Flow rate (%)",
    db_kolom: str = "db_lden",
    hoogte: int = 360,
    waarde_format: str = ".1%",
) -> alt.Chart:
    chart_data = _flow_rate_chart_data(
        df,
        measure_id,
        db_kolom=db_kolom,
    )
    return (
        alt.Chart(chart_data.to_pandas())
        .mark_bar()
        .encode(
            x=alt.X(
                "db_band:O",
                title="LDEN-geluidsband (dB)",
                sort=_LDEN_BANDEN,
            ),
            xOffset="toestand:N",
            y=alt.Y(
                "waarde:Q",
                title=y_label,
                stack=None,
                axis=alt.Axis(format=waarde_format),
            ),
            color=alt.Color(
                "toestand:N",
                title="Toestand",
                scale=_FLOW_TOESTAND_KLEUREN,
                legend=alt.Legend(orient="top-right"),
            ),
            tooltip=[
                alt.Tooltip("toestand:N", title="Toestand"),
                alt.Tooltip("db_band:O", title="dB"),
                alt.Tooltip("waarde:Q", title=y_label, format=waarde_format),
            ],
        )
        .properties(title=titel, height=hoogte)
    )


def toon_flow_rate_staafdiagram(
    df: pl.DataFrame,
    measure_id: str,
    *,
    titel: str | None = None,
    y_label: str = "Flow rate (%)",
    db_kolom: str = "db_lden",
    hoogte: int = 360,
    waarde_format: str = ".1%",
) -> None:
    """Staafdiagram per LDEN-band: baseline vs. active (geen gewest-split).

    ``df`` moet één rij per band bevatten met ``{measure_id}_baseline`` en ``*_active``.
    Waarden zijn fracties (0–1); as en tooltip tonen percentages.
    Aggregatie gebeurt buiten deze functie (``contour_analyse_2.py``).
    """
    chart_titel = titel or measure_id.replace("_", " ").capitalize()
    chart = staafdiagram_flow_rate(
        df,
        measure_id,
        titel=chart_titel,
        y_label=y_label,
        db_kolom=db_kolom,
        hoogte=hoogte,
        waarde_format=waarde_format,
    )
    st.altair_chart(chart, use_container_width=True)
    if df[measure_id + "_baseline"].sum() == 0:
        st.warning("**Baseline** is 0 voor alle db contouren.")
    if df[measure_id + "_active"].sum() == 0:
        st.warning("**Active** is 0 voor alle db contouren.")


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
        "color": alt.Color(
            "gewest:N",
            title="Gewest",
            scale=_GEWEST_KLEUREN,
            legend=alt.Legend(orient="top-right"),
        ),
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
