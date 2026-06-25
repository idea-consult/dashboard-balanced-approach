"""Kaartweergave voor sector–contour-overlappen (geometrie_inter_ss_lden)."""

from __future__ import annotations

import struct
from functools import lru_cache

import polars as pl
import pydeck as pdk
import streamlit as st
from pyproj import Transformer

_LAMBERT_NAAR_WGS84 = Transformer.from_crs("EPSG:31370", "EPSG:4326", always_xy=True)

# Duidelijk contrast laag ↔ hoog op kaarten (lichtblauw → koraalrood, cf. Brussel in grafieken)
_KLEUR_LAAG = (158, 202, 225, 175)
_KLEUR_HOOG = (221, 91, 97, 210)
_KLEUR_RAND = [60, 60, 60, 100]


def _interpoleer_kleur(t: float) -> list[int]:
    """Lineair tussen twee contrasterende kleuren (t ∈ [0, 1])."""
    t = max(0.0, min(1.0, t))
    return [int(_KLEUR_LAAG[i] + (_KLEUR_HOOG[i] - _KLEUR_LAAG[i]) * t) for i in range(4)]


def _parse_ring(data: bytes, offset: int, endian: str, has_z: bool) -> tuple[list[list[float]], int]:
    npts = struct.unpack(endian + "I", data[offset : offset + 4])[0]
    offset += 4
    ring: list[list[float]] = []
    for _ in range(npts):
        x, y = struct.unpack(endian + "dd", data[offset : offset + 16])
        offset += 16
        if has_z:
            offset += 8
        lon, lat = _LAMBERT_NAAR_WGS84.transform(x, y)
        ring.append([lon, lat])
    return ring, offset


def _parse_polygon(data: bytes, offset: int, has_z: bool) -> tuple[list[list[list[float]]], int]:
    endian = "<" if data[offset] == 1 else ">"
    offset += 1
    offset += 4  # subtype
    nrings = struct.unpack(endian + "I", data[offset : offset + 4])[0]
    offset += 4
    rings: list[list[list[float]]] = []
    for _ in range(nrings):
        ring, offset = _parse_ring(data, offset, endian, has_z)
        rings.append(ring)
    return rings, offset


def ewkb_hex_naar_polygonen(hex_geom: str) -> list[list[list[list[float]]]]:
    """Zet PostGIS EWKB-hex (MultiPolygon Z, EPSG:31370) om naar WGS84-polygonen."""
    if not hex_geom or len(hex_geom) % 2:
        return []

    try:
        data = bytes.fromhex(hex_geom)
    except ValueError:
        return []

    endian = "<" if data[0] == 1 else ">"
    offset = 1
    geom_type = struct.unpack(endian + "I", data[offset : offset + 4])[0]
    offset += 4
    has_z = bool(geom_type & 0x80000000)
    if geom_type & 0x20000000:
        offset += 4

    base_type = geom_type & 0xFF
    if base_type == 6:
        npoly = struct.unpack(endian + "I", data[offset : offset + 4])[0]
        offset += 4
        polygonen: list[list[list[list[float]]]] = []
        for _ in range(npoly):
            poly, offset = _parse_polygon(data, offset, has_z)
            polygonen.append(poly)
        return polygonen

    if base_type == 3:
        poly, _ = _parse_polygon(data, 1, has_z)
        return [poly]

    return []


def _db_naar_kleur(db: int) -> list[int]:
    """Kleurverloop: lage dB = lichtblauw, hoge dB = koraalrood."""
    t = max(0.0, min(1.0, (db - 45) / 30))
    return _interpoleer_kleur(t)


@lru_cache(maxsize=4096)
def _polygonen_voor_geometrie(hex_geom: str) -> tuple[tuple[tuple[tuple[float, float], ...], ...], ...]:
    """Cache per unieke geometrie-string."""
    polygonen = ewkb_hex_naar_polygonen(hex_geom)
    return tuple(
        tuple(tuple((pt[0], pt[1]) for pt in ring) for ring in poly)
        for poly in polygonen
    )


def _kaart_features(df: pl.DataFrame) -> tuple[list[dict], int]:
    features: list[dict] = []
    overgeslagen = 0
    for row in df.iter_rows(named=True):
        polygonen = _polygonen_voor_geometrie(row["geometrie_inter_ss_lden"])
        if not polygonen:
            overgeslagen += 1
            continue
        for poly in polygonen:
            ring = poly[0]
            if len(ring) < 3:
                continue
            features.append(
                {
                    "polygon": [list(pt) for pt in ring],
                    "db_lden": row["db_lden"],
                    "gemeente": row["naam_gemeente_nl"],
                    "sector": row["naam_sector_nl"],
                    "regio": row["regio_nl"],
                    "inwoners_overlap": row["inwoners_overlap"],
                    "kleur": _db_naar_kleur(int(row["db_lden"])),
                }
            )
    return features, overgeslagen


def _waarde_naar_kleur(waarde: float, min_val: float, max_val: float) -> list[int]:
    """Kleurverloop: lage waarde = lichtblauw, hoge waarde = koraalrood."""
    if max_val <= min_val:
        t = 0.5 if waarde > 0 else 0.0
    else:
        t = max(0.0, min(1.0, (waarde - min_val) / (max_val - min_val)))
    return _interpoleer_kleur(t)


def _kaart_features_voor_kolom(
    df: pl.DataFrame,
    kolom: str,
    *,
    geometrie_kolom: str = "geometrie_inter_ss_lden",
) -> tuple[list[dict], int, float, float]:
    waarden = df.select(pl.col(kolom).fill_null(0).cast(pl.Float64)).to_series().to_list()
    min_val = min(waarden) if waarden else 0.0
    max_val = max(waarden) if waarden else 0.0

    features: list[dict] = []
    overgeslagen = 0
    for row in df.iter_rows(named=True):
        polygonen = _polygonen_voor_geometrie(row[geometrie_kolom])
        if not polygonen:
            overgeslagen += 1
            continue
        waarde = float(row[kolom] or 0)
        kleur = _waarde_naar_kleur(waarde, min_val, max_val)
        for poly in polygonen:
            ring = poly[0]
            if len(ring) < 3:
                continue
            features.append(
                {
                    "polygon": [list(pt) for pt in ring],
                    "db_lden": row["db_lden"],
                    "gemeente": row["naam_gemeente_nl"],
                    "sector": row["naam_sector_nl"],
                    "regio": row["regio_nl"],
                    "waarde": waarde,
                    "kleur": kleur,
                }
            )
    return features, overgeslagen, min_val, max_val


def tel_overgeslagen_overlaps(
    df: pl.DataFrame,
    *,
    geometrie_kolom: str = "geometrie_inter_ss_lden",
) -> int:
    """Tel intersecties waarvan de geometrie niet op de kaart getoond kan worden."""
    if geometrie_kolom not in df.columns:
        return 0
    overgeslagen = 0
    for geom in df[geometrie_kolom].to_list():
        if not _polygonen_voor_geometrie(geom or ""):
            overgeslagen += 1
    return overgeslagen


def toon_geometrie_waarschuwing(
    df: pl.DataFrame,
    *,
    geometrie_kolom: str = "geometrie_inter_ss_lden",
) -> None:
    """Toon waarschuwing over ontbrekende/afgekapte geometrie één keer bovenaan de pagina."""
    overgeslagen = tel_overgeslagen_overlaps(df, geometrie_kolom=geometrie_kolom)
    if overgeslagen:
        st.warning(
            f"{overgeslagen} overlap(s) niet getoond op kaarten: geometrie ontbreekt of is "
            "afgekapt (bv. Excel-limiet 32.765 tekens per cel)."
        )


def toon_waarde_kaart(
    df: pl.DataFrame,
    kolom: str,
    *,
    y_label: str = "Waarde",
    geometrie_kolom: str = "geometrie_inter_ss_lden",
    waarde_format: str = ",.0f",
    hoogte: int = 500,
) -> None:
    """Toon overlap-polygonen met een kleurschaal op basis van ``kolom``."""
    if kolom not in df.columns:
        st.warning(f"Kolom '{kolom}' niet gevonden voor kaartweergave.")
        return
    if geometrie_kolom not in df.columns:
        st.warning("Geometrie ontbreekt; kaart kan niet getoond worden.")
        return

    features, _, min_val, max_val = _kaart_features_voor_kolom(
        df, kolom, geometrie_kolom=geometrie_kolom
    )

    if not features:
        st.info("Geen polygonen om te tonen.")
        return

    midden_lat = sum(pt[1] for f in features for pt in f["polygon"]) / sum(
        len(f["polygon"]) for f in features
    )
    midden_lon = sum(pt[0] for f in features for pt in f["polygon"]) / sum(
        len(f["polygon"]) for f in features
    )

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
                    "PolygonLayer",
                    data=features,
                    get_polygon="polygon",
                    get_fill_color="kleur",
                    get_line_color=_KLEUR_RAND,
                    line_width_min_pixels=1,
                    pickable=True,
                    stroked=True,
                    filled=True,
                ),
            ],
            tooltip={
                "html": (
                    "<b>{gemeente}</b> — {sector}<br/>"
                    "<b>dB:</b> {db_lden}<br/>"
                    f"<b>{y_label}:</b> {{waarde}}<br/>"
                    "<b>Regio:</b> {regio}"
                ),
                "style": {"backgroundColor": "#4E2567", "color": "white"},
            },
        ),
        height=hoogte,
    )

    st.caption(
        f"{len(features):,} polygonen · {y_label}: "
        f"{min_val:{waarde_format}} (blauw, laag) → {max_val:{waarde_format}} (rood, hoog)"
    )


def toon_overlap_kaart(df: pl.DataFrame) -> None:
    db_waarden = sorted(df["db_lden"].unique().to_list())
    geselecteerde_db = st.multiselect(
        "LDEN-geluidsband (dB)",
        options=db_waarden,
        default=db_waarden,
        format_func=lambda db: f"{db} dB",
    )

    gefilterd = df.filter(pl.col("db_lden").is_in(geselecteerde_db))
    features, _ = _kaart_features(gefilterd)

    if not features:
        st.info("Geen polygonen om te tonen met dit filter.")
        return

    midden_lat = sum(pt[1] for f in features for pt in f["polygon"]) / sum(
        len(f["polygon"]) for f in features
    )
    midden_lon = sum(pt[0] for f in features for pt in f["polygon"]) / sum(
        len(f["polygon"]) for f in features
    )

    st.caption(
        f"{len(features):,} polygonen getoond "
        f"(van {df.height:,} overlaps · filter: {len(geselecteerde_db)} dB-banden) · "
        "kleur: laag dB = blauw, hoog dB = rood"
    )

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
                    "PolygonLayer",
                    data=features,
                    get_polygon="polygon",
                    get_fill_color="kleur",
                    get_line_color=_KLEUR_RAND,
                    line_width_min_pixels=1,
                    pickable=True,
                    stroked=True,
                    filled=True,
                ),
            ],
            tooltip={
                "html": (
                    "<b>{gemeente}</b> — {sector}<br/>"
                    "<b>dB:</b> {db_lden}<br/>"
                    "<b>Inwoners overlap:</b> {inwoners_overlap}<br/>"
                    "<b>Regio:</b> {regio}"
                ),
                "style": {"backgroundColor": "#4E2567", "color": "white"},
            },
        )
    )
