"""Build JSON context for the Typst simulation report."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import pandas as pd

from config import BEGINJAAR, EINDJAAR, FLOW_RULES_FILE, FLOW_SIZE_FILE, PERSONEN_PER_WOONUNIT
from models.flow_help_rates import summarize_measure_rates
from models.measure_selection_manager import MeasureSelectionManager
from models.scenario_manager import NONE_SCENARIO_ID, NONE_SCENARIO_LABEL
from models.stock_manager import StockManager
from reports.brand import OPDRACHTREGEL, REPORT_TITLE
from ui.components import _delta_pct
from ui.formatting import format_euro_miljoen, format_integer, format_percent


def _format_report_cost(value: float) -> str:
    """Format costs for the PDF; never leave the field blank."""
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "€ 0 mln"
    formatted = format_euro_miljoen(value)
    return formatted if formatted else "€ 0 mln"


def _kpi_row(stock_manager: StockManager, metric: str, label: str) -> dict[str, Any]:
    begin = stock_manager.get_aantal(metric, BEGINJAAR, "Totaal")
    eind = stock_manager.get_aantal(metric, EINDJAAR, "Totaal")
    return {
        "label": label,
        "begin": format_integer(begin),
        "eind": format_integer(eind),
        "delta_pct": format_percent(_delta_pct(begin, eind)),
    }


def _applied_measures(
    measure_selection_manager: MeasureSelectionManager,
) -> list[dict[str, Any]]:
    descriptions = measure_selection_manager.get_measure_descriptions()
    hidden = measure_selection_manager.get_hidden_measures()
    rows: list[dict[str, Any]] = []
    for measure_id in descriptions.index.astype(str):
        if measure_id in hidden:
            continue
        zones = measure_selection_manager.get_selected_zones(measure_id)
        overlay = measure_selection_manager.get_selected_overlay(measure_id)
        if not zones and overlay is None:
            continue
        naam = str(descriptions.at[measure_id, "naam_mooi"])
        help_text = str(descriptions.at[measure_id, "help"]).strip()
        # Shorten help: first non-empty paragraph after title
        lines = [
            ln.strip()
            for ln in help_text.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        short = " ".join(lines[:4])[:500]
        coverage = (
            f"Overlay {overlay}"
            if overlay
            else ("Zones " + ", ".join(zones) if zones else "—")
        )
        rows.append(
            {
                "measure_id": measure_id,
                "naam": naam,
                "coverage": coverage,
                "help_short": short,
            }
        )
    return rows


def _flow_rate_rows(
    measure_selection_manager: MeasureSelectionManager,
) -> list[dict[str, Any]]:
    flow_size = pd.read_csv(FLOW_SIZE_FILE)
    flow_rules = pd.read_csv(FLOW_RULES_FILE)
    descriptions = measure_selection_manager.get_measure_descriptions()
    rows: list[dict[str, Any]] = []
    for _, rule in flow_rules.iterrows():
        measure_id = str(rule["measure_id"])
        baseline, active = summarize_measure_rates(flow_size, measure_id)
        zones = measure_selection_manager.get_selected_zones(measure_id)
        overlay = measure_selection_manager.get_selected_overlay(measure_id)
        applied = bool(zones) or overlay is not None
        used = active if applied else baseline
        if measure_id in descriptions.index:
            naam = str(descriptions.at[measure_id, "naam_mooi"])
        else:
            naam = measure_id
        rows.append(
            {
                "measure_id": measure_id,
                "naam": naam,
                "mode": str(rule.get("flow_mode", "")),
                "baseline_pct": f"{baseline * 100:.2f}%",
                "active_pct": f"{active * 100:.2f}%",
                "used_pct": f"{used * 100:.2f}%",
                "applied": "Ja" if applied else "Nee",
            }
        )
    return rows


def _stock_rows(stock_manager: StockManager) -> list[dict[str, Any]]:
    stocks = [
        ("onbebouwde_bebouwbare_percelen", "Onbebouwde bebouwbare percelen"),
        ("onbebouwde_onbebouwbare_percelen", "Onbebouwde onbebouwbare percelen"),
        ("bewoonde_niet_geïsoleerde_woning", "Bewoonde niet-geïsoleerde woningen"),
        ("bewoonde_geïsoleerde_woning", "Bewoonde geïsoleerde woningen"),
        ("perceel_eigendom_overheid", "Percelen eigendom overheid"),
        ("woning_eigendom_overheid", "Woningen eigendom overheid"),
    ]
    rows = []
    for metric, label in stocks:
        begin = stock_manager.get_aantal(metric, BEGINJAAR, "Totaal")
        eind = stock_manager.get_aantal(metric, EINDJAAR, "Totaal")
        rows.append(
            {
                "label": label,
                "begin": format_integer(begin),
                "eind": format_integer(eind),
                "delta_pct": format_percent(_delta_pct(begin, eind)),
            }
        )
    return rows


def build_report_context(
    *,
    stock_manager: StockManager,
    measure_selection_manager: MeasureSelectionManager,
    kost_overheid: float,
    kost_prive: float,
    scenario_id: str | None,
    scenario_label: str | None,
    figures: list[dict],
) -> dict[str, Any]:
    sid = scenario_id or NONE_SCENARIO_ID
    slabel = scenario_label or NONE_SCENARIO_LABEL
    return {
        "title": REPORT_TITLE,
        "opdrachtregel": OPDRACHTREGEL,
        "exported_at": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "beginjaar": BEGINJAAR,
        "eindjaar": EINDJAAR,
        "contour": "Lden (1 dB)",
        "scenario_id": sid,
        "scenario_label": slabel,
        "personen_per_woonunit": PERSONEN_PER_WOONUNIT,
        "kpis": [
            _kpi_row(
                stock_manager,
                "aantal_ernstig_gehinderden",
                "Ernstig gehinderde personen (totaal)",
            ),
            _kpi_row(
                stock_manager,
                "aantal_ernstig_gehinderden_vlaanderen",
                "Ernstig gehinderde personen (Vlaanderen)",
            ),
            _kpi_row(
                stock_manager,
                "aantal_ernstig_gehinderden_brussel",
                "Ernstig gehinderde personen (Brussel)",
            ),
            _kpi_row(stock_manager, "leefbaarheidspunten", "Leefbaarheidspunten (totaal)"),
        ],
        "kosten": {
            "overheid": _format_report_cost(kost_overheid),
            "prive": _format_report_cost(kost_prive),
        },
        "applied_measures": _applied_measures(measure_selection_manager),
        "flow_rates": _flow_rate_rows(measure_selection_manager),
        "stocks": _stock_rows(stock_manager),
        "figures": figures,
    }
