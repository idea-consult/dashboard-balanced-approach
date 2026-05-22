"""Helpteksten voor maatregelen, incl. flow-regels uit flow_rules.csv."""

from __future__ import annotations

import pandas as pd

from ui.formatting import format_number

FLOW_MODE_TITLES = {
    "growth": "Growth",
    "transfer": "Transfer",
}


def _stock_label(stock_name: str) -> str:
    return str(stock_name).replace("_", " ")


def _format_flow_rate(rate: float) -> str:
    return f"{format_number(float(rate) * 100, decimals=1)} %"


def _rate_phrase(rate: float) -> str:
    pct = _format_flow_rate(rate)
    if float(rate) == 0.0:
        return f"{pct} (geen jaarlijkse flow)"
    return pct


def _effect_summary(mode: str, inflow: str, outflow: str) -> str:
    inflow_label = _stock_label(inflow)
    outflow_label = _stock_label(outflow)
    if mode == "growth":
        return "Deze maatregel zorgt ervoor dat de stock groeit."
    return (
        f"Deze maatregel zorgt ervoor dat de stock krimpt bij **{inflow_label}** en "
        f"overgedragen wordt naar **{outflow_label}**."
    )


def _inactive_scenario(mode: str, inflow: str, outflow: str, baseline: float) -> str:
    inflow_label = _stock_label(inflow)
    outflow_label = _stock_label(outflow)
    rate = _rate_phrase(baseline)
    if mode == "growth":
        stock = inflow_label if inflow == outflow else f"{inflow_label} (inflow-stock)"
        return (
            "Wanneer deze maatregel **niet geselecteerd** is in een zone, "
            f"groeit de stock **{stock}** jaarlijks met **{rate}**."
        )
    return (
        "Wanneer deze maatregel **niet geselecteerd** is in een zone, "
        f"wordt jaarlijks **{rate}** van de **{inflow_label}** overgedragen naar de "
        f"**{outflow_label}** (de **{inflow_label}** krimpt daarbij met hetzelfde bedrag)."
    )


def _active_scenario(mode: str, inflow: str, outflow: str, active: float) -> str:
    inflow_label = _stock_label(inflow)
    outflow_label = _stock_label(outflow)
    rate = _rate_phrase(active)
    if mode == "growth":
        stock = inflow_label if inflow == outflow else f"{inflow_label} (inflow-stock)"
        return (
            "Wanneer deze maatregel **wel geselecteerd** is in een zone, "
            f"groeit de stock **{stock}** jaarlijks met **{rate}**."
        )
    return (
        "Wanneer deze maatregel **wel geselecteerd** is in een zone, "
        f"wordt jaarlijks **{rate}** van de **{inflow_label}** overgedragen naar de "
        f"**{outflow_label}** (de **{inflow_label}** krimpt daarbij met hetzelfde bedrag)."
    )


def format_flow_rule_block(row: pd.Series, *, rule_index: int | None = None) -> str:
    """Eén flow-regel als markdown voor de Streamlit-help tooltip."""
    mode = str(row["flow_mode"]).strip().lower()
    inflow = str(row["inflow_stock"])
    outflow = str(row["outflow_stock"])
    baseline = float(row["flow_rate_baseline"])
    active = float(row["flow_rate_active"])
    mode_title = FLOW_MODE_TITLES.get(mode, str(row["flow_mode"]))

    header = "### Simulatieflow in het dashboard"
    if rule_index is not None:
        header = f"### Simulatieflow in het dashboard (regel {rule_index})"

    lines = [
        header,
        "",
        "#### Wat doet deze flow?",
        _effect_summary(mode, inflow, outflow),
        "",
        "#### Stocks in het model",
        f"- **Inflow-stock** (waar de flow op wordt berekend): {_stock_label(inflow)}",
        f"- **Outflow-stock** (bestemming bij transfer, of dezelfde stock bij growth): "
        f"{_stock_label(outflow)}",
        "",
        "#### Gedrag per zone-selectie",
        _inactive_scenario(mode, inflow, outflow, baseline),
        "",
        _active_scenario(mode, inflow, outflow, active),
        "",
        "#### Technische parameters",
        f"- **Flow-modus:** {mode_title}",
        f"- **Flow baseline** (maatregel uit): {_format_flow_rate(baseline)}",
        f"- **Flow actief** (maatregel aan): {_format_flow_rate(active)}",
    ]
    if baseline != active:
        lines.append(
            "- *Let op:* baseline en actief percentage verschillen — de simulatie schakelt "
            "automatisch wanneer u de maatregel in de sidebar aan- of uitzet per zone."
        )

    comments = row.get("comments", "")
    if isinstance(comments, str) and comments.strip():
        lines.extend(["", f"**Opmerking uit de configuratie:** {comments.strip()}"])
    return "\n".join(lines)


def format_flow_help_section(flow_rules: pd.DataFrame) -> str:
    """Alle flow-regels van één maatregel, gesorteerd op priority."""
    if flow_rules.empty:
        return ""

    sorted_rules = flow_rules.sort_values("priority", kind="stable")
    blocks = [
        format_flow_rule_block(row, rule_index=i if len(sorted_rules) > 1 else None)
        for i, (_, row) in enumerate(sorted_rules.iterrows(), start=1)
    ]
    intro = (
        "Onderstaande uitleg beschrijft hoe deze maatregel jaarlijks stocks aanpast in de "
        "simulatie. Selecteer zones in de sidebar om de maatregel actief te maken."
    )
    return intro + "\n\n" + "\n\n".join(blocks)


def combine_measure_help(base_help: str, flow_rules: pd.DataFrame) -> str:
    """Maatregel-uitleg + flow-details voor de hover-help."""
    base = str(base_help or "").strip()
    flow_section = format_flow_help_section(flow_rules).strip()
    if not flow_section:
        return base
    if not base:
        return flow_section
    return f"{base}\n\n---\n\n{flow_section}"
