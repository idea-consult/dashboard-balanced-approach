"""Export Altair charts used in the PDF report."""

from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd

from config import BEGINJAAR, EINDJAAR
from models.stock_manager import StockManager
from reports.brand import CHART_FONT, register_vl_convert_fonts
from ui.components import (
    _CHART_KLEUR_A,
    _CHART_KLEUR_B,
    _bar_value_labels,
    _integer_axis,
    _integer_tooltip,
    _jaar_categorieen,
    _legenda_labels_en_kleuren,
    _stock_plot_frame,
    _zone_color_encoding,
)


def _with_embeddable_fonts(chart: alt.Chart) -> alt.Chart:
    """Force Aptos on all text layers for headless PNG rendering."""
    return (
        chart.configure(font=CHART_FONT)
        .configure_title(font=CHART_FONT)
        .configure_axis(labelFont=CHART_FONT, titleFont=CHART_FONT)
        .configure_legend(labelFont=CHART_FONT, titleFont=CHART_FONT)
        .configure_text(font=CHART_FONT)
    )


def _save_png(chart: alt.Chart, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    register_vl_convert_fonts()
    _with_embeddable_fonts(chart).save(str(path), format="png", scale_factor=2)
    return path


def build_ernstig_gehinderden_chart(df_stock: pd.DataFrame) -> alt.Chart | None:
    regional_metrics = {
        "aantal_ernstig_gehinderden_vlaanderen": "Vlaanderen",
        "aantal_ernstig_gehinderden_brussel": "Brussel",
    }
    df_plot = df_stock[
        (df_stock["naam"].isin(regional_metrics.keys()))
        & (df_stock["zone"] != "Totaal")
        & (df_stock["jaar"].isin([BEGINJAAR, EINDJAAR]))
    ].copy()
    if df_plot.empty:
        return None

    jaar_begin, jaar_einde = _jaar_categorieen()
    regio_kleuren = {"Vlaanderen": _CHART_KLEUR_A, "Brussel": _CHART_KLEUR_B}
    df_plot["regio"] = df_plot["naam"].map(regional_metrics)
    df_plot["aantal_ernstig_gehinderden"] = df_plot["aantal"]
    df_plot["jaar_label"] = df_plot["jaar"].astype(int).astype(str)
    df_plot["jaar_label"] = pd.Categorical(
        df_plot["jaar_label"], categories=[jaar_begin, jaar_einde], ordered=True
    )
    df_plot["regio_volgorde"] = df_plot["regio"].map({"Vlaanderen": 0, "Brussel": 1})
    df_plot["legenda"] = df_plot.apply(
        lambda row: f"{row['regio']} ({int(row['jaar'])})", axis=1
    )
    legenda_domain, legenda_range = _legenda_labels_en_kleuren(
        ("Vlaanderen", "Brussel"), regio_kleuren
    )
    bars = (
        alt.Chart(df_plot)
        .mark_bar()
        .encode(
            x=alt.X("zone:N", title="Zone", axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("jaar_label:N", sort="ascending"),
            y=alt.Y(
                "aantal_ernstig_gehinderden:Q",
                title="Aantal ernstig gehinderden",
                axis=_integer_axis("Aantal ernstig gehinderden"),
            ),
            color=alt.Color(
                "legenda:N",
                scale=alt.Scale(domain=legenda_domain, range=legenda_range),
                legend=alt.Legend(orient="right", title=None, symbolStrokeWidth=0),
            ),
            order=alt.Order("regio_volgorde:O", sort="ascending"),
        )
    )
    labels = _bar_value_labels(
        df_plot,
        x="zone",
        y="aantal_ernstig_gehinderden",
        x_offset="jaar_label",
        label_totals=True,
    )
    return (
        (bars + labels)
        .properties(
            title=(
                f"Ernstig gehinderden per zone — Vlaanderen en Brussel "
                f"({BEGINJAAR} vs {EINDJAAR})"
            ),
            height=420,
            width=640,
        )
        .configure_view(stroke=None)
    )


def build_overlay_impact_chart(stock_manager: StockManager) -> alt.Chart | None:
    if "share_lnight45" not in stock_manager.df_contour.columns:
        return None
    rows: list[dict] = []
    for overlay_id, label in (("lnight45", "Lnight45"), ("na70", "NA70")):
        for jaar in (BEGINJAAR, EINDJAAR):
            for metric, regio in (
                ("aantal_ernstig_gehinderden_vlaanderen", "Vlaanderen"),
                ("aantal_ernstig_gehinderden_brussel", "Brussel"),
            ):
                waarde = stock_manager.sum_metric_weighted_by_overlay(
                    metric, jaar, overlay_id
                )
                rows.append(
                    {
                        "overlay": label,
                        "jaar": jaar,
                        "jaar_label": str(jaar),
                        "regio": regio,
                        "aantal": waarde,
                    }
                )
    df_plot = pd.DataFrame(rows)
    if df_plot.empty or df_plot["aantal"].sum() == 0:
        return None

    jaar_begin, jaar_einde = _jaar_categorieen()
    df_plot["jaar_label"] = pd.Categorical(
        df_plot["jaar_label"], categories=[jaar_begin, jaar_einde], ordered=True
    )
    df_plot["regio_volgorde"] = df_plot["regio"].map({"Vlaanderen": 0, "Brussel": 1})
    df_plot["legenda"] = df_plot.apply(
        lambda row: f"{row['regio']} ({int(row['jaar'])})", axis=1
    )
    regio_kleuren = {"Vlaanderen": _CHART_KLEUR_A, "Brussel": _CHART_KLEUR_B}
    legenda_domain, legenda_range = _legenda_labels_en_kleuren(
        ("Vlaanderen", "Brussel"), regio_kleuren
    )
    bars = (
        alt.Chart(df_plot)
        .mark_bar()
        .encode(
            x=alt.X("overlay:N", title="Overlappende contour", axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("jaar_label:N", sort="ascending"),
            y=alt.Y(
                "aantal:Q",
                title="Ernstig gehinderden (gewogen)",
                axis=_integer_axis("Ernstig gehinderden (gewogen)"),
            ),
            color=alt.Color(
                "legenda:N",
                scale=alt.Scale(domain=legenda_domain, range=legenda_range),
                legend=alt.Legend(orient="right", title=None, symbolStrokeWidth=0),
            ),
            order=alt.Order("regio_volgorde:O", sort="ascending"),
        )
    )
    labels = _bar_value_labels(
        df_plot, x="overlay", y="aantal", x_offset="jaar_label", label_totals=True
    )
    return (
        (bars + labels)
        .properties(
            title=f"Ernstig gehinderden in overlappende contouren ({BEGINJAAR} vs {EINDJAAR})",
            height=360,
            width=640,
        )
        .configure_view(stroke=None)
    )


def build_stock_line_chart(
    df_stock: pd.DataFrame, stock_name: str, title: str, y_label: str
) -> alt.Chart | None:
    df_plot = _stock_plot_frame(df_stock, stock_name)
    if df_plot.empty:
        return None
    return (
        alt.Chart(df_plot)
        .mark_line(point=True)
        .encode(
            x=alt.X("jaar:O", title="Jaar"),
            y=alt.Y("aantal:Q", title=y_label, axis=_integer_axis(y_label)),
            color=_zone_color_encoding(),
            tooltip=["zone", "jaar", _integer_tooltip("aantal:Q", y_label)],
        )
        .properties(title=title, height=280, width=480)
    )


def export_report_charts(stock_manager: StockManager, out_dir: Path) -> list[dict]:
    """Write PNG charts; return list of {path, caption} relative to out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    df_stock = stock_manager.get_dataframe().reset_index()
    figures: list[dict] = []

    builders: list[tuple[str, str, alt.Chart | None]] = [
        (
            "ernstig_gehinderden.png",
            "Ernstig gehinderden per zone (Vlaanderen / Brussel).",
            build_ernstig_gehinderden_chart(df_stock),
        ),
        (
            "overlay_impact.png",
            "Ernstig gehinderden gewogen naar dekking Lnight45 / NA70.",
            build_overlay_impact_chart(stock_manager),
        ),
    ]
    for filename, caption, chart in builders:
        if chart is None:
            continue
        _save_png(chart, out_dir / filename)
        figures.append({"file": filename, "caption": caption})

    stock_specs = [
        (
            "stock_bebouwbare_percelen.png",
            "onbebouwde_bebouwbare_percelen",
            "Onbebouwde bebouwbare percelen per zone",
            "Aantal percelen",
        ),
        (
            "stock_niet_geisoleerd.png",
            "bewoonde_niet_geïsoleerde_woning",
            "Niet-geïsoleerde woningen per zone",
            "Aantal woningen",
        ),
        (
            "stock_geisoleerd.png",
            "bewoonde_geïsoleerde_woning",
            "Geïsoleerde woningen per zone",
            "Aantal woningen",
        ),
    ]
    for filename, stock_name, title, y_label in stock_specs:
        chart = build_stock_line_chart(df_stock, stock_name, title, y_label)
        if chart is None:
            continue
        _save_png(chart, out_dir / filename)
        figures.append({"file": filename, "caption": title + "."})

    return figures
