"""Idea Consult Altair/Vega-Lite chart theme."""

from __future__ import annotations

import altair as alt

from reports.brand import CHART_FONT, register_vl_convert_fonts

DUTCH_NUMBER_FORMAT_LOCALE = {
    "decimal": ",",
    "thousands": ".",
    "grouping": [3],
    "currency": ["€ ", ""],
}

# Ensure PNG export (vl-convert) can embed Aptos on Linux/Render.
register_vl_convert_fonts()

IDEA_CONSULT_ALTAIR_THEME = {
    "config": {
        "numberFormatLocale": DUTCH_NUMBER_FORMAT_LOCALE,
        "background": "white",
        "view": {
            "fill": "white",
            "stroke": "transparent",
            "width": 700,
            "height": 400,
        },
        "title": {
            "font": CHART_FONT,
            "fontSize": 23,
            "fontWeight": "bold",
            "color": "black",
        },
        "axis": {
            "domainColor": "black",
            "domainWidth": 1,
            "grid": False,
            "labelFont": CHART_FONT,
            "labelFontSize": 13,
            "labelColor": "black",
            "titleFont": CHART_FONT,
            "titleFontSize": 17,
            "titleColor": "black",
        },
        "legend": {
            "labelFont": CHART_FONT,
            "labelFontSize": 17,
            "titleFont": CHART_FONT,
            "titleFontSize": 17,
            "orient": "right",
            "fillColor": "transparent",
            "strokeColor": "transparent",
            "padding": 17,
            "symbolSize": 100,
            "symbolType": "circle",
        },
        "bar": {"color": "#4E2567"},
        "line": {"stroke": "#4E2567", "strokeWidth": 2.5},
        "point": {"color": "#4E2567", "size": 64},
        "area": {"color": "#4E2567"},
        "tick": {"color": "#4E2567"},
        "rule": {"color": "#4E2567"},
        "trail": {"color": "#4E2567"},
        "circle": {"color": "#4E2567"},
        "square": {"color": "#4E2567"},
        "range": {
            "category": [
                "#4E2567",
                "#DD5B61",
                "#EB914D",
                "#36A3C9",
                "#00989A",
            ]
        },
        "font": CHART_FONT,
        "text": {"font": CHART_FONT, "fontSize": 17, "color": "black"},
    }
}

CATEGORY_COLORS = IDEA_CONSULT_ALTAIR_THEME["config"]["range"]["category"]


@alt.theme.register("idea_consult", enable=True)
def idea_consult_theme() -> alt.theme.ThemeConfig:
    return alt.theme.ThemeConfig(IDEA_CONSULT_ALTAIR_THEME)
