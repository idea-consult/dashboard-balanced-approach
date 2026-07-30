"""Showcase: flow rates & prijzen — presentatie uit contour_analyse_2.py.

Leest vooraf berekende CSV's; markdown, maatregel-help en grafiekvolgorde komen
rechtstreeks uit ``contour_analyse_2.py`` zodat deze pagina niet kan verouderen.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl
import streamlit as st

from contour_vlaanderen_grafieken import (
    toon_flow_rate_staafdiagram,
    toon_staafdiagram_per_gewest,
)

_FLOW_SIZE_PATH = Path("input/flow_size.csv")
_DATA_2_PATH = Path("data_2/data_2.csv")
_MEASURES_PATH = Path("input/measures.csv")
_ANALYSE_2_PATH = Path("contour_analyse_2.py")


@st.cache_data
def load_flow_size() -> pl.DataFrame:
    if not _FLOW_SIZE_PATH.is_file():
        raise FileNotFoundError(_FLOW_SIZE_PATH)
    return pl.read_csv(_FLOW_SIZE_PATH)


@st.cache_data
def load_intersecties() -> pl.DataFrame:
    if not _DATA_2_PATH.is_file():
        raise FileNotFoundError(_DATA_2_PATH)
    return pl.read_csv(_DATA_2_PATH)


@st.cache_data
def load_maatregel_help() -> dict[str, str]:
    if not _MEASURES_PATH.is_file():
        return {}
    df = pl.read_csv(_MEASURES_PATH)
    return {
        str(row["measure_id"]): str(row["help"])
        for row in df.select("measure_id", "help").iter_rows(named=True)
    }


@dataclass
class ShowcaseSection:
    markdown_parts: list[str] = field(default_factory=list)
    help_measure_ids: list[str] = field(default_factory=list)
    flow_measure_ids: list[str] = field(default_factory=list)
    render_prijzen: bool = False

    @property
    def markdown(self) -> str:
        return "\n\n".join(part for part in self.markdown_parts if part.strip())


def _call_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _const_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _starts_section_heading(text: str) -> bool:
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first.startswith("#")


def _parse_analyse_2_sections(source: str) -> list[ShowcaseSection]:
    """Haal presentatie-secties uit contour_analyse_2.py (markdown + chart-calls)."""
    tree = ast.parse(source)
    sections: list[ShowcaseSection] = []
    current = ShowcaseSection()

    def flush_if_needed() -> None:
        nonlocal current
        if (
            current.markdown_parts
            or current.help_measure_ids
            or current.flow_measure_ids
            or current.render_prijzen
        ):
            sections.append(current)
            current = ShowcaseSection()

    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            text = node.value.value
            if not isinstance(text, str) or not text.strip():
                continue
            if _starts_section_heading(text) and (
                current.markdown_parts
                or current.help_measure_ids
                or current.flow_measure_ids
                or current.render_prijzen
            ):
                flush_if_needed()
            current.markdown_parts.append(text)
            continue

        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
            continue

        call = node.value
        name = _call_name(call)
        if name == "toon_maatregel_info":
            for arg in call.args:
                measure_id = _const_str(arg)
                if measure_id:
                    current.help_measure_ids.append(measure_id)
        elif name == "toon_flow_rate_staafdiagram" and len(call.args) >= 2:
            measure_id = _const_str(call.args[1])
            if measure_id:
                current.flow_measure_ids.append(measure_id)
        elif name == "toon_staafdiagram_per_gewest":
            current.render_prijzen = True

    flush_if_needed()
    return sections


@st.cache_data
def load_showcase_sections(_mtime: float) -> list[ShowcaseSection]:
    """``_mtime`` bust de cache wanneer ``contour_analyse_2.py`` wijzigt."""
    if not _ANALYSE_2_PATH.is_file():
        raise FileNotFoundError(_ANALYSE_2_PATH)
    return _parse_analyse_2_sections(_ANALYSE_2_PATH.read_text(encoding="utf-8"))


def _render_prijzen(df_intersecties: pl.DataFrame) -> None:
    toon_staafdiagram_per_gewest(
        df_intersecties,
        kolom="gemiddelde_prijs_van_een_woning",
        titel="Prijs bewoonde woning (geïsoleerd en niet-geïsoleerd)",
        y_label="Gemiddelde prijs (€)",
        aggregatie="gemiddelde",
        gewicht_kolom="aantal_woning_transacties_per_jaar",
        waarde_format=",.0f",
        toon_kaart=False,
    )
    toon_staafdiagram_per_gewest(
        df_intersecties,
        kolom="gemiddelde_prijs_bebouwbaar_perceel",
        titel="Prijs onbebouwd bebouwbare percelen",
        y_label="Gemiddelde prijs (€)",
        aggregatie="gemiddelde",
        gewicht_kolom="aantal_bebouwbare_perceel_transacties_per_jaar",
        waarde_format=",.0f",
        toon_kaart=False,
    )


def _toon_maatregel_info(
    measure_ids: list[str],
    help_by_id: dict[str, str],
    *,
    enabled: bool,
) -> None:
    if not enabled:
        return
    for measure_id in measure_ids:
        help_text = help_by_id.get(measure_id, "").strip()
        if help_text:
            st.info(help_text)


def render() -> None:
    st.title("Flow rates & prijzen per LDEN-band")
    st.caption("Presentatie synchroon met `contour_analyse_2.py` (geen herberekening)")
    st.info(
        "Resultaten uit vooraf berekende data; deze pagina voert geen herberekening uit. "
        "Tekst en grafiekvolgorde volgen `contour_analyse_2.py`."
    )

    with st.sidebar:
        toon_maatregel_help = st.toggle(
            "Toon maatregel-uitleg",
            value=False,
            help=(
                "Toont of verbergt de narratieve helptekst (uit measures.csv) "
                "onder elke maatregel-titel."
            ),
        )

    try:
        if not _ANALYSE_2_PATH.is_file():
            raise FileNotFoundError(_ANALYSE_2_PATH)
        df_flows = load_flow_size()
        df_intersecties = load_intersecties()
        sections = load_showcase_sections(_ANALYSE_2_PATH.stat().st_mtime)
    except FileNotFoundError as exc:
        missing = exc.args[0]
        if missing == _FLOW_SIZE_PATH:
            st.error(
                f"`{_FLOW_SIZE_PATH}` ontbreekt. Voer eerst `contour_analyse_2.py` uit."
            )
        elif missing == _ANALYSE_2_PATH:
            st.error(f"`{_ANALYSE_2_PATH}` ontbreekt.")
        else:
            st.error(
                f"`{_DATA_2_PATH}` ontbreekt. Voer eerst `contour_analyse_1.py` uit."
            )
        return

    help_by_id = load_maatregel_help()
    st.caption(
        f"{df_flows.height} LDEN-banden · {df_flows.width} kolommen in flow_size.csv"
    )

    prijzen_gerenderd = False
    for section in sections:
        if section.markdown:
            st.markdown(section.markdown)
        _toon_maatregel_info(
            section.help_measure_ids,
            help_by_id,
            enabled=toon_maatregel_help,
        )
        for measure_id in section.flow_measure_ids:
            toon_flow_rate_staafdiagram(df_flows, measure_id)
        if section.render_prijzen and not prijzen_gerenderd:
            _render_prijzen(df_intersecties)
            prijzen_gerenderd = True
