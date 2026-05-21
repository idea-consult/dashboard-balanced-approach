"""Idea Consult Altair/Vega-Lite chart theme."""

from __future__ import annotations

import altair as alt

DUTCH_NUMBER_FORMAT_LOCALE = {
    "decimal": ",",
    "thousands": ".",
    "grouping": [3],
    "currency": ["€ ", ""],
}

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
            "font": "Segoe UI",
            "fontSize": 23,
            "fontWeight": "bold",
            "color": "black",
        },
        "axis": {
            "domainColor": "black",
            "domainWidth": 1,
            "grid": False,
            "labelFont": "Segoe UI",
            "labelFontSize": 13,
            "labelColor": "black",
            "titleFont": "Segoe UI",
            "titleFontSize": 17,
            "titleColor": "black",
        },
        "legend": {
            "labelFont": "Segoe UI",
            "labelFontSize": 17,
            "titleFont": "Segoe UI",
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
        "font": "Segoe UI",
        "text": {"font": "Segoe UI", "fontSize": 17, "color": "black"},
    }
}

CATEGORY_COLORS = IDEA_CONSULT_ALTAIR_THEME["config"]["range"]["category"]


@alt.theme.register("idea_consult", enable=True)
def idea_consult_theme() -> alt.theme.ThemeConfig:
    return alt.theme.ThemeConfig(IDEA_CONSULT_ALTAIR_THEME)
