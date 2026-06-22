"""Staafdiagrammen per db_ondergrens voor contour-notebooks."""

from __future__ import annotations

import pandas as pd

try:
    import altair as alt
except ImportError:  # pragma: no cover
    alt = None


def _chart_dataframe(
    lden: pd.DataFrame,
    lnight: pd.DataFrame | None,
    kolom: str,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if kolom in lden.columns:
        frames.append(
            pd.DataFrame(
                {
                    "db_ondergrens": lden.index.astype(int).astype(str),
                    "waarde": pd.to_numeric(lden[kolom], errors="coerce").fillna(0),
                    "reeks": "lden",
                }
            )
        )
    if lnight is not None and kolom in lnight.columns:
        frames.append(
            pd.DataFrame(
                {
                    "db_ondergrens": lnight.index.astype(int).astype(str),
                    "waarde": pd.to_numeric(lnight[kolom], errors="coerce").fillna(0),
                    "reeks": "lnight",
                }
            )
        )
    if not frames:
        raise KeyError(f"Kolom '{kolom}' niet in lden/lnight")
    return pd.concat(frames, ignore_index=True)


def staafdiagram_per_contour(
    lden: pd.DataFrame,
    kolom: str,
    *,
    lnight: pd.DataFrame | None = None,
    titel: str | None = None,
) -> alt.Chart:
    """Gegroepeerde staafgrafiek: waarde per ``db_ondergrens`` (lden ± lnight)."""
    if alt is None:
        raise ImportError("altair is vereist voor notebook-grafieken")

    df = _chart_dataframe(lden, lnight, kolom)
    titel = titel or kolom
    dual = df["reeks"].nunique() > 1

    enc: dict = {
        "x": alt.X(
            "db_ondergrens:O",
            title="dB-ondergrens",
            sort=[str(i) for i in range(int(df["db_ondergrens"].astype(int).min()), int(df["db_ondergrens"].astype(int).max()) + 1)],
        ),
        "y": alt.Y("waarde:Q", title=kolom, scale=alt.Scale(zero=True)),
        "tooltip": [
            alt.Tooltip("db_ondergrens:O", title="dB"),
            alt.Tooltip("waarde:Q", title=kolom, format=",.4f"),
            alt.Tooltip("reeks:N", title="indicator"),
        ],
    }
    if dual:
        enc["color"] = alt.Color("reeks:N", title="Indicator")
        enc["xOffset"] = alt.XOffset("reeks:N")

    return alt.Chart(df).mark_bar(opacity=0.9).encode(**enc).properties(
        title=titel,
        width=780,
        height=260,
    )


def staafdiagram_reeks(
    reeks: pd.Series,
    *,
    titel: str,
    y_label: str = "waarde",
) -> alt.Chart:
    """Staafgrafiek uit één Series (index = db_ondergrens)."""
    if alt is None:
        raise ImportError("altair is vereist voor notebook-grafieken")

    df = pd.DataFrame(
        {
            "db_ondergrens": reeks.index.astype(int).astype(str),
            "waarde": pd.to_numeric(reeks, errors="coerce").fillna(0),
        }
    )
    return alt.Chart(df).mark_bar(color="#4C78A8").encode(
        x=alt.X(
            "db_ondergrens:O",
            title="dB-ondergrens",
            sort=[str(i) for i in range(int(df["db_ondergrens"].astype(int).min()), int(df["db_ondergrens"].astype(int).max()) + 1)],
        ),
        y=alt.Y("waarde:Q", title=y_label, scale=alt.Scale(zero=True)),
        tooltip=[
            alt.Tooltip("db_ondergrens:O", title="dB"),
            alt.Tooltip("waarde:Q", format=",.4f"),
        ],
    ).properties(title=titel, width=780, height=260)


def toon_staaf_per_contour(
    lden: pd.DataFrame,
    kolom: str,
    *,
    lnight: pd.DataFrame | None = None,
    titel: str | None = None,
) -> alt.Chart:
    """Notebook-helper: staafdiagram per band."""
    return staafdiagram_per_contour(lden, kolom, lnight=lnight, titel=titel)
