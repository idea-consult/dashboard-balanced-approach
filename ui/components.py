"""UI components for displaying metrics and charts."""

import streamlit as st
import altair as alt
import pandas as pd
import os
from typing import Dict

from config import FLOW_SIZE_FILE, SCENARIOS_FILE
from models.flow_help_rates import apply_flow_size_rates_to_rules
from models.stock_manager import StockManager
from models.measure_selection_manager import MeasureSelectionManager
from models.scenario_manager import (
    NONE_SCENARIO_ID,
    NONE_SCENARIO_LABEL,
    ScenarioManager,
)
from models.validation import validate_measure_combinations
from simulation.engine import SimulationEngine
from config import BEGINJAAR, EINDJAAR
from ui.formatting import (
    ALTAIR_INTEGER_FORMAT,
    format_euro_miljoen,
    format_integer,
    format_number,
    format_percent,
)
from ui.measure_help import combine_measure_help

# Idea Consult-kleuren: paars (serie A) en roze (serie B), licht = beginjaar, normaal = eindjaar
_CHART_KLEUR_A = {"normaal": "#4E2567", "licht": "#A68BB8"}
_CHART_KLEUR_B = {"normaal": "#DD5B61", "licht": "#F0A8AC"}

SCENARIO_RADIO_KEY = "scenario_preset"


def _jaar_categorieen() -> tuple[str, str]:
    return str(BEGINJAAR), str(EINDJAAR)


def _legenda_kleur(serie: str, jaar: int, kleuren: dict[str, dict[str, str]]) -> str:
    tint = "licht" if jaar == BEGINJAAR else "normaal"
    return kleuren[serie][tint]


def _legenda_labels_en_kleuren(
    series: tuple[str, str], kleuren: dict[str, dict[str, str]]
) -> tuple[list[str], list[str]]:
    """Vier legendaitems: serie A/B × beginjaar/eindjaar."""
    domain: list[str] = []
    range_kleuren: list[str] = []
    for serie in series:
        for jaar in (BEGINJAAR, EINDJAAR):
            domain.append(f"{serie} ({jaar})")
            range_kleuren.append(_legenda_kleur(serie, jaar, kleuren))
    return domain, range_kleuren


def _measure_help(
    measure_selection_manager: MeasureSelectionManager,
    measure_id: str,
    flow_size: pd.DataFrame | None = None,
) -> str:
    descriptions = measure_selection_manager.get_measure_descriptions()
    base_help = str(descriptions.at[measure_id, "help"])
    flow_rules = measure_selection_manager.get_flow_rules_for_measure(measure_id)
    if flow_size is not None:
        flow_rules = apply_flow_size_rates_to_rules(flow_rules, flow_size)
    return combine_measure_help(base_help, flow_rules)


def _overlay_widget_key(prefix: str, measure_or_group: str) -> str:
    return f"ov_{prefix}_{measure_or_group}"


def _clear_scenario_preset() -> None:
    st.session_state[SCENARIO_RADIO_KEY] = NONE_SCENARIO_ID
    st.session_state["_scenario_radio_label"] = NONE_SCENARIO_LABEL
    st.session_state["_scenario_prev_id"] = NONE_SCENARIO_ID


def _clear_zones_on_overlay(zone_key: str, other_overlay_key: str):
    """Callback: selecting an overlay clears A–F and the other overlay."""

    def _cb() -> None:
        _clear_scenario_preset()
        st.session_state[zone_key] = []
        st.session_state[other_overlay_key] = False

    return _cb


def _clear_overlays_on_zones(lnight_key: str, na70_key: str):
    """Callback: selecting A–F clears both overlays."""

    def _cb() -> None:
        _clear_scenario_preset()
        st.session_state[lnight_key] = False
        st.session_state[na70_key] = False

    return _cb


def _widget_keys_for_sidebar(
    measure_selection_manager: MeasureSelectionManager,
) -> list[tuple[str, str, str, tuple[str, ...]]]:
    """List (zone_key, lnight_key, na70_key, measure_names) for visible sidebar entries."""
    hidden = measure_selection_manager.get_hidden_measures()
    grouped = measure_selection_manager.get_measure_groups()
    keys: list[tuple[str, str, str, tuple[str, ...]]] = []
    for entry_kind, entry_key in measure_selection_manager.get_ui_sidebar_entries():
        if entry_kind == "group":
            measure_names = grouped[entry_key]
            if any(m in hidden for m in measure_names):
                continue
            zone_key = f"seg_group_{entry_key}"
            lnight_key = _overlay_widget_key("lnight45", f"group_{entry_key}")
            na70_key = _overlay_widget_key("na70", f"group_{entry_key}")
            keys.append((zone_key, lnight_key, na70_key, measure_names))
            continue
        if entry_key in hidden:
            continue
        zone_key = f"seg_{entry_key}"
        lnight_key = _overlay_widget_key("lnight45", entry_key)
        na70_key = _overlay_widget_key("na70", entry_key)
        keys.append((zone_key, lnight_key, na70_key, (entry_key,)))
    return keys


def _apply_scenario_to_session(
    scenario_manager: ScenarioManager,
    measure_selection_manager: MeasureSelectionManager,
    scenario_id: str,
) -> None:
    """Clear all measure widgets, then apply CSV selections for the scenario."""
    widget_entries = _widget_keys_for_sidebar(measure_selection_manager)
    for zone_key, lnight_key, na70_key, measure_names in widget_entries:
        st.session_state[zone_key] = []
        st.session_state[lnight_key] = False
        st.session_state[na70_key] = False
        for measure in measure_names:
            measure_selection_manager.set_selected_overlay(measure, None)
            measure_selection_manager.set_selected_zones(measure, ())

    if not scenario_id:
        return

    selections = scenario_manager.get_selections(scenario_id)
    # Per measure_id from CSV
    for measure_id, selection in selections.items():
        if selection.overlay:
            measure_selection_manager.set_selected_overlay(measure_id, selection.overlay)
        else:
            measure_selection_manager.set_selected_overlay(measure_id, None)
            measure_selection_manager.set_selected_zones(measure_id, selection.zones)

    # Sync group/standalone widget keys from manager state
    for zone_key, lnight_key, na70_key, measure_names in widget_entries:
        overlays = {
            measure_selection_manager.get_selected_overlay(m) for m in measure_names
        }
        overlays.discard(None)
        if len(overlays) > 1:
            # Conflicting overlays in one group: prefer first measure's overlay
            overlay = measure_selection_manager.get_selected_overlay(measure_names[0])
        else:
            overlay = next(iter(overlays), None)

        if overlay == "lnight45":
            st.session_state[lnight_key] = True
            st.session_state[na70_key] = False
            st.session_state[zone_key] = []
        elif overlay == "na70":
            st.session_state[lnight_key] = False
            st.session_state[na70_key] = True
            st.session_state[zone_key] = []
        else:
            st.session_state[lnight_key] = False
            st.session_state[na70_key] = False
            zones = tuple(
                sorted(
                    set().union(
                        *(
                            set(measure_selection_manager.get_selected_zones(m))
                            for m in measure_names
                        )
                    )
                )
            )
            st.session_state[zone_key] = list(zones)


def _apply_measure_selection(
    measure_selection_manager: MeasureSelectionManager,
    measure_names: tuple[str, ...] | list[str],
    *,
    lnight_key: str,
    na70_key: str,
    zone_key: str,
) -> None:
    lnight = bool(st.session_state.get(lnight_key, False))
    na70 = bool(st.session_state.get(na70_key, False))
    if lnight and na70:
        na70 = False
        st.session_state[na70_key] = False
    overlay: str | None = "lnight45" if lnight else ("na70" if na70 else None)
    zones_selected = st.session_state.get(zone_key) or ()
    if isinstance(zones_selected, str):
        zones_selected = (zones_selected,)
    if overlay is not None:
        zones_selected = ()
    for measure in measure_names:
        if overlay is not None:
            measure_selection_manager.set_selected_overlay(measure, overlay)
        else:
            measure_selection_manager.set_selected_overlay(measure, None)
            measure_selection_manager.set_selected_zones(measure, tuple(zones_selected))


def render_sidebar_controls(
    measure_selection_manager: MeasureSelectionManager,
    zones,
    stock_manager: StockManager | None = None,
):
    """
    Render sidebar controls for measure selection.

    Args:
        measure_selection_manager: MeasureSelectionManager instance
    """
    df_beschrijving_maatregelen = measure_selection_manager.get_measure_descriptions()
    hidden_measures = measure_selection_manager.get_hidden_measures()
    grouped_measures = measure_selection_manager.get_measure_groups()

    known_ids = set(df_beschrijving_maatregelen.index.astype(str))
    scenario_manager = ScenarioManager(SCENARIOS_FILE, known_measure_ids=known_ids)
    scenario_options = scenario_manager.radio_options()
    scenario_labels = [label for _, label in scenario_options]
    label_to_id = {label: sid for sid, label in scenario_options}

    flow_size = None
    if stock_manager is not None and stock_manager._lden_band_mode:
        flow_size = pd.read_csv(FLOW_SIZE_FILE)

    with st.sidebar:
        if SCENARIO_RADIO_KEY not in st.session_state:
            st.session_state[SCENARIO_RADIO_KEY] = NONE_SCENARIO_ID

        current_id = st.session_state.get(SCENARIO_RADIO_KEY, NONE_SCENARIO_ID)
        current_label = next(
            (label for sid, label in scenario_options if sid == current_id),
            NONE_SCENARIO_LABEL,
        )

        st.markdown("**Scenario**")
        if "_scenario_radio_label" not in st.session_state:
            st.session_state["_scenario_radio_label"] = current_label
        chosen_label = st.radio(
            "Scenario",
            options=scenario_labels,
            key="_scenario_radio_label",
            label_visibility="collapsed",
        )
        # Map label widget → scenario_id and apply when changed
        new_id = label_to_id.get(chosen_label, NONE_SCENARIO_ID)
        prev_id = st.session_state.get("_scenario_prev_id", NONE_SCENARIO_ID)
        if new_id != prev_id:
            st.session_state[SCENARIO_RADIO_KEY] = new_id
            _apply_scenario_to_session(
                scenario_manager, measure_selection_manager, new_id
            )
            st.session_state["_scenario_prev_id"] = new_id
        else:
            st.session_state[SCENARIO_RADIO_KEY] = new_id
            st.session_state["_scenario_prev_id"] = new_id

        st.caption(
            "Eén scenario tegelijk. Kiest automatisch zones/overlays uit "
            "`input/scenarios.csv`. Handmatig wijzigen zet het scenario op Geen."
        )
        st.divider()
        st.caption(
            "Zones A–F zijn mutueel exclusief. Lnight45 / NA70 overlappen met A–F: "
            "kies ofwel A–F, ofwel één overlay."
        )
        section_starts = measure_selection_manager.get_sidebar_section_starts()
        section_ends = measure_selection_manager.get_sidebar_section_ends()
        for entry_kind, entry_key in measure_selection_manager.get_ui_sidebar_entries():
            section_title = section_starts.get((entry_kind, entry_key))
            if section_title:
                st.markdown("---")
                st.markdown(f"**{section_title}**")

            if entry_kind == "group":
                group_id = entry_key
                measure_names = grouped_measures[group_id]
                if any(measure in hidden_measures for measure in measure_names):
                    continue
                if not all(
                    measure in df_beschrijving_maatregelen.index for measure in measure_names
                ):
                    continue
                zone_key = f"seg_group_{group_id}"
                lnight_key = _overlay_widget_key("lnight45", f"group_{group_id}")
                na70_key = _overlay_widget_key("na70", f"group_{group_id}")
                for key, default in (
                    (lnight_key, False),
                    (na70_key, False),
                ):
                    if key not in st.session_state:
                        st.session_state[key] = default

                overlay_active = bool(
                    st.session_state.get(lnight_key) or st.session_state.get(na70_key)
                )
                zones_active = bool(st.session_state.get(zone_key))
                combined_selected = tuple(
                    sorted(
                        set().union(
                            *(
                                set(measure_selection_manager.get_selected_zones(measure))
                                for measure in measure_names
                            )
                        )
                    )
                )
                if overlay_active:
                    combined_selected = ()
                combined_help = "\n\n---\n\n".join(
                    _measure_help(measure_selection_manager, measure, flow_size)
                    for measure in measure_names
                )
                group_label = (
                    measure_selection_manager.get_sidebar_short_label("group", group_id)
                    or group_id.replace("_", " ").capitalize()
                )
                st.segmented_control(
                    label=group_label,
                    options=zones,
                    help=combined_help,
                    selection_mode="multi",
                    default=combined_selected,
                    key=zone_key,
                    width="stretch",
                    disabled=overlay_active,
                    on_change=_clear_overlays_on_zones(lnight_key, na70_key),
                )
                col_l, col_n = st.columns(2)
                with col_l:
                    st.checkbox(
                        "Lnight45",
                        key=lnight_key,
                        disabled=zones_active or bool(st.session_state.get(na70_key)),
                        help="Overlappende nachtcontour (≥45 dB). Niet combineerbaar met A–F of NA70.",
                        on_change=_clear_zones_on_overlay(zone_key, na70_key),
                    )
                with col_n:
                    st.checkbox(
                        "NA70",
                        key=na70_key,
                        disabled=zones_active or bool(st.session_state.get(lnight_key)),
                        help="Overlappende NA70-contour. Niet combineerbaar met A–F of Lnight45.",
                        on_change=_clear_zones_on_overlay(zone_key, lnight_key),
                    )
                _apply_measure_selection(
                    measure_selection_manager,
                    measure_names,
                    lnight_key=lnight_key,
                    na70_key=na70_key,
                    zone_key=zone_key,
                )
                if (entry_kind, entry_key) in section_ends:
                    st.markdown("---")
                continue

            maatregel = entry_key
            if maatregel in hidden_measures:
                continue
            zone_key = f"seg_{maatregel}"
            lnight_key = _overlay_widget_key("lnight45", maatregel)
            na70_key = _overlay_widget_key("na70", maatregel)
            for key, default in ((lnight_key, False), (na70_key, False)):
                if key not in st.session_state:
                    st.session_state[key] = default
            overlay_active = bool(
                st.session_state.get(lnight_key) or st.session_state.get(na70_key)
            )
            zones_active = bool(st.session_state.get(zone_key))
            default_zones = (
                ()
                if overlay_active
                else measure_selection_manager.get_selected_zones(maatregel)
            )
            measure_label = (
                measure_selection_manager.get_sidebar_short_label("measure", maatregel)
                or df_beschrijving_maatregelen.at[maatregel, "naam_mooi"]
            )
            st.segmented_control(
                label=measure_label,
                options=zones,
                help=_measure_help(measure_selection_manager, maatregel, flow_size),
                selection_mode="multi",
                default=default_zones,
                key=zone_key,
                width="stretch",
                disabled=overlay_active,
                on_change=_clear_overlays_on_zones(lnight_key, na70_key),
            )
            col_l, col_n = st.columns(2)
            with col_l:
                st.checkbox(
                    "Lnight45",
                    key=lnight_key,
                    disabled=zones_active or bool(st.session_state.get(na70_key)),
                    help="Overlappende nachtcontour (≥45 dB). Niet combineerbaar met A–F of NA70.",
                    on_change=_clear_zones_on_overlay(zone_key, na70_key),
                )
            with col_n:
                st.checkbox(
                    "NA70",
                    key=na70_key,
                    disabled=zones_active or bool(st.session_state.get(lnight_key)),
                    help="Overlappende NA70-contour. Niet combineerbaar met A–F of Lnight45.",
                    on_change=_clear_zones_on_overlay(zone_key, lnight_key),
                )
            _apply_measure_selection(
                measure_selection_manager,
                (maatregel,),
                lnight_key=lnight_key,
                na70_key=na70_key,
                zone_key=zone_key,
            )
            if (entry_kind, entry_key) in section_ends:
                st.markdown("---")

    # Valideer maatregel combinaties na alle selecties (buiten de sidebar)
    conflicts = validate_measure_combinations(
        measure_selection_manager, tuple(zones), stock_manager=stock_manager
    )
    return conflicts


def _delta_pct(begin: float, eind: float) -> int:
    if begin == 0:
        return 0
    return int(100 * (eind - begin) / begin)


def _integer_axis(title: str) -> alt.Axis:
    return alt.Axis(title=title, format=ALTAIR_INTEGER_FORMAT)


def _integer_tooltip(field: str, title: str) -> alt.Tooltip:
    return alt.Tooltip(field, title=title, format=ALTAIR_INTEGER_FORMAT)


def _bar_value_labels(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    waarde_format: str = ALTAIR_INTEGER_FORMAT,
    x_offset: str | None = None,
    stack: str | None = None,
    label_grootte: int = 10,
    label_totals: bool = False,
) -> alt.Chart:
    """Tekstlabels boven (positief) of onder (negatief) elk niet-nul staafje.

    Bij ``label_totals=True`` (gestapelde balken) wordt per x/(xOffset)-groep
    de som getoond — één label bovenop de hele stapel, niet per segment.
    """
    label_df = df.copy()
    label_stack = stack
    if label_totals:
        group_cols = [x] if x_offset is None else [x, x_offset]
        label_df = label_df.groupby(group_cols, as_index=False, observed=True)[y].sum()
        label_stack = None

    label_df = label_df[label_df[y] != 0]
    if label_df.empty:
        return alt.Chart(pd.DataFrame()).mark_point(opacity=0)

    def _text_layer(subset: pd.DataFrame, dy: int, baseline: str) -> alt.Chart:
        encode: dict = {
            "x": alt.X(f"{x}:N"),
            "y": alt.Y(f"{y}:Q", stack=label_stack),
            "text": alt.Text(f"{y}:Q", format=waarde_format),
            "color": alt.value("#333333"),
        }
        if x_offset is not None:
            encode["xOffset"] = alt.XOffset(f"{x_offset}:N")
        return (
            alt.Chart(subset)
            .mark_text(align="center", size=label_grootte, dy=dy, baseline=baseline)
            .encode(**encode)
        )

    positief = label_df[label_df[y] >= 0]
    negatief = label_df[label_df[y] < 0]
    layers: list[alt.Chart] = []
    if not positief.empty:
        layers.append(_text_layer(positief, -6, "bottom"))
    if not negatief.empty:
        layers.append(_text_layer(negatief, 6, "top"))

    chart = layers[0]
    for layer in layers[1:]:
        chart = chart + layer
    return chart


def _render_traject_metric(stock_manager: StockManager, metric_name: str, label: str) -> None:
    begin = stock_manager.get_aantal(metric_name, BEGINJAAR, "Totaal")
    eind = stock_manager.get_aantal(metric_name, EINDJAAR, "Totaal")
    delta_pct = _delta_pct(begin, eind)
    st.metric(
        label,
        format_integer(eind),
        format_percent(delta_pct),
        delta_color="inverse",
    )


def render_metrics(
    stock_manager: StockManager,
    kost_overheid: float,
    kost_prive: float,
) -> None:
    """KPI's bovenaan: ernstig gehinderden (totaal/Vlaanderen/Brussel) en kosten."""
    col_totaal, col_vl, col_br, col_overheid, col_prive = st.columns(5)

    with col_totaal:
        _render_traject_metric(
            stock_manager,
            "aantal_ernstig_gehinderden",
            "# ernstig gehinderde personen",
        )
    with col_vl:
        _render_traject_metric(
            stock_manager,
            "aantal_ernstig_gehinderden_vlaanderen",
            "# ernstig gehinderde vlamingen",
        )
    with col_br:
        _render_traject_metric(
            stock_manager,
            "aantal_ernstig_gehinderden_brussel",
            "# ernstig gehinderde brusselaars",
        )
    with col_overheid:
        st.metric("Totale kost overheid", format_euro_miljoen(kost_overheid))
    with col_prive:
        st.metric("Totale kost privé", format_euro_miljoen(kost_prive))


def render_leefbaarheidspunten_metrics(stock_manager: StockManager) -> None:
    """Leefbaarheidspunten-KPI's (eindjaar) binnen de instellingen-expander."""
    col_hp_totaal, col_hp_iso, col_hp_niet = st.columns(3)
    with col_hp_totaal:
        _render_traject_metric(
            stock_manager, "leefbaarheidspunten", "Totaal aantal leefbaarheidspunten"
        )
    with col_hp_iso:
        _render_traject_metric(
            stock_manager, "leefbaarheidspunten_met_isolatie", "Leefbaarheidspunten geïsoleerd"
        )
    with col_hp_niet:
        _render_traject_metric(
            stock_manager,
            "leefbaarheidspunten_zonder_isolatie",
            "Leefbaarheidspunten niet-geïsoleerd",
        )


def render_leefbaarheidspunten_panel(
    stock_manager: StockManager,
    contour_type: str,
    simulation_engine: SimulationEngine,
) -> None:
    """Expander: gewichten per zone, berekening en leefbaarheidspunten-KPI's."""
    panel = st.expander(
        "Instelling leefbaarheidspunten per zone",
        expanded=False,
        key="leefbaarheidspunten_panel",
        on_change="rerun",
    )
    if not panel.open:
        return

    with panel:
        leefbaarheidspunten_weights = render_leefbaarheidspunten_weight_controls(
            stock_manager, contour_type
        )
        simulation_engine.calculate_leefbaarheidspunten(
            BEGINJAAR, EINDJAAR, leefbaarheidspunten_weights
        )
        st.divider()
        render_leefbaarheidspunten_metrics(stock_manager)


def _stock_plot_frame(df_stock: pd.DataFrame, base_stock_name: str) -> pd.DataFrame:
    """Plotdata: totaal per zone/jaar (Vlaanderen + Brussel samen)."""
    zone_mask = df_stock["zone"] != "Totaal"
    direct = df_stock[(df_stock["naam"] == base_stock_name) & zone_mask]
    if not direct.empty:
        return direct.copy()

    regional_names = [f"{base_stock_name}_{regio}" for regio in StockManager.REGIONS]
    regional = df_stock[df_stock["naam"].isin(regional_names) & zone_mask]
    if regional.empty:
        return pd.DataFrame()

    aggregated = regional.groupby(["jaar", "zone"], as_index=False)["aantal"].sum()
    aggregated["naam"] = base_stock_name
    return aggregated


def plot_metric(
    df_stock: pd.DataFrame, stock_name: str, title: str, y_label: str
) -> None:
    """
    Create and display a line chart for a specific stock metric.

    Args:
        df_stock: DataFrame with stock data
        stock_name: Name of the stock to plot
        title: Chart title
        y_label: Y-axis label
    """
    df_plot = _stock_plot_frame(df_stock, stock_name)
    chart = (
        alt.Chart(df_plot)
        .mark_line(point=True)
        .encode(
            x=alt.X("jaar:O", title="Jaar"),
            y=alt.Y("aantal:Q", title=y_label, axis=_integer_axis(y_label)),
            color=alt.Color("zone:N", title="Zone"),
            tooltip=[
                "zone",
                "jaar",
                _integer_tooltip("aantal:Q", y_label),
            ],
        )
        .properties(title=title, width=500, height=300)
    )
    st.altair_chart(chart, width="stretch")


def render_charts(stock_manager: StockManager) -> None:
    """Render charts for ernstig gehinderden, leefbaarheidspunten, and stock line charts."""
    df_stock = stock_manager.get_dataframe().reset_index()
    render_ernstig_gehinderden_chart(df_stock)
    render_overlay_section(stock_manager, df_stock)
    render_leefbaarheidspunten_section(stock_manager)
    render_compact_line_charts(df_stock)


def render_ernstig_gehinderden_chart(df_stock: pd.DataFrame) -> None:
    """Staafgrafiek per zone: beginjaar/eindjaar, gestapeld Vlaanderen vs Brussel."""
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
        st.warning("Geen data beschikbaar voor aantal ernstig gehinderden (Vlaanderen/Brussel).")
        return

    jaar_begin, jaar_einde = _jaar_categorieen()
    regio_kleuren = {"Vlaanderen": _CHART_KLEUR_A, "Brussel": _CHART_KLEUR_B}
    df_plot["regio"] = df_plot["naam"].map(regional_metrics)
    df_plot["aantal_ernstig_gehinderden"] = df_plot["aantal"]
    df_plot["jaar_label"] = df_plot["jaar"].astype(int).astype(str)
    df_plot["jaar_label"] = pd.Categorical(
        df_plot["jaar_label"],
        categories=[jaar_begin, jaar_einde],
        ordered=True,
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
                legend=alt.Legend(
                    orient="right",
                    title=None,
                    symbolStrokeWidth=0,
                    labelFontSize=12,
                ),
            ),
            order=alt.Order("regio_volgorde:O", sort="ascending"),
            tooltip=[
                "zone",
                alt.Tooltip("jaar_label:N", title="Jaar"),
                "regio",
                _integer_tooltip("aantal_ernstig_gehinderden:Q", "Aantal ernstig gehinderden"),
            ],
        )
    )
    labels = _bar_value_labels(
        df_plot,
        x="zone",
        y="aantal_ernstig_gehinderden",
        x_offset="jaar_label",
        label_totals=True,
    )
    chart = (
        (bars + labels)
        .properties(
            title=(
                f"Ernstig gehinderden per zone — Vlaanderen en Brussel "
                f"({BEGINJAAR} vs {EINDJAAR})"
            ),
            height=560,
        )
        .configure_view(stroke=None)
    )
    st.altair_chart(chart, width="stretch")
    st.caption(
        f"Per zone: links {BEGINJAAR}, rechts {EINDJAAR}. "
        "Zones A–F zijn mutueel exclusief; de som over A–F is het totaal."
    )


def render_overlay_section(stock_manager: StockManager, df_stock: pd.DataFrame) -> None:
    """Apart blok voor overlappende contouren Lnight45 / NA70 (niet optellen bij A–F)."""
    if "share_lnight45" not in stock_manager.df_contour.columns:
        return

    st.subheader("Overlappende contouren (Lnight45 en NA70)")
    st.warning(
        "Lnight45 en NA70 overlappen met zones A–F (en deels met elkaar). "
        "Tel deze cijfers **niet** op bij de A–F-grafiek hierboven, en ook niet bij elkaar."
    )

    render_overlay_impact_chart(stock_manager)
    coverage_panel = st.expander(
        "Dekking: welk % van elke zone A–F ligt in Lnight45 / NA70?",
        expanded=False,
        key="overlay_coverage_panel",
        on_change="rerun",
    )
    if not coverage_panel.open:
        return

    with coverage_panel:
        render_overlay_coverage_chart(stock_manager)


def render_overlay_impact_chart(stock_manager: StockManager) -> None:
    """Ernstig gehinderden gewogen naar overlay-dekking — aparte x-as (niet A–F)."""
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
        st.info("Geen overlay-impact beschikbaar (shares ontbreken of zijn nul).")
        return

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
                title="Ernstig gehinderden (gewogen naar dekking)",
                axis=_integer_axis("Ernstig gehinderden (gewogen)"),
            ),
            color=alt.Color(
                "legenda:N",
                scale=alt.Scale(domain=legenda_domain, range=legenda_range),
                legend=alt.Legend(orient="right", title=None, symbolStrokeWidth=0),
            ),
            order=alt.Order("regio_volgorde:O", sort="ascending"),
            tooltip=[
                "overlay",
                alt.Tooltip("jaar_label:N", title="Jaar"),
                "regio",
                _integer_tooltip("aantal:Q", "Aantal"),
            ],
        )
    )
    labels = _bar_value_labels(
        df_plot,
        x="overlay",
        y="aantal",
        x_offset="jaar_label",
        label_totals=True,
    )
    chart = (
        (bars + labels)
        .properties(
            title=(
                f"Ernstig gehinderden in overlappende contouren "
                f"({BEGINJAAR} vs {EINDJAAR})"
            ),
            height=420,
        )
        .configure_view(stroke=None)
    )
    st.altair_chart(chart, width="stretch")
    st.caption(
        "Apart van A–F: waarden zijn zone-totalen gewogen met het inwonersaandeel in de overlay. "
        "Niet optellen bij de A–F-grafiek."
    )


def render_overlay_coverage_chart(stock_manager: StockManager) -> None:
    """Statische dekking: % bevolking per zone A–F dat in elke overlay ligt."""
    coverage = stock_manager.get_overlay_coverage_by_zone()
    if coverage.empty:
        return
    long = coverage.melt(
        id_vars=["zone"],
        value_vars=["share_lnight45", "share_na70"],
        var_name="overlay_col",
        value_name="share",
    )
    long["overlay"] = long["overlay_col"].map(
        {"share_lnight45": "Lnight45", "share_na70": "NA70"}
    )
    long["pct"] = long["share"] * 100.0

    bars = (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X("zone:N", title="Zone (Lden A–F)", axis=alt.Axis(labelAngle=0)),
            xOffset="overlay:N",
            y=alt.Y("pct:Q", title="% van zone-inwoners in overlay", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color(
                "overlay:N",
                scale=alt.Scale(
                    domain=["Lnight45", "NA70"],
                    range=[_CHART_KLEUR_A["normaal"], _CHART_KLEUR_B["normaal"]],
                ),
                legend=alt.Legend(title=None),
            ),
            tooltip=[
                "zone",
                "overlay",
                alt.Tooltip("pct:Q", title="% inwoners", format=".1f"),
            ],
        )
    )
    labels = _bar_value_labels(
        long,
        x="zone",
        y="pct",
        waarde_format=".1f",
        x_offset="overlay",
    )
    chart = (
        (bars + labels)
        .properties(title="Overlappende dekking per Lden-zone", height=480)
        .configure_view(stroke=None)
    )
    st.altair_chart(chart, width="stretch")
    st.caption(
        "Toont welk deel van de bevolking in elke exclusieve Lden-zone ook in Lnight45 of NA70 valt. "
        "A–D liggen grotendeels in Lnight45; NA70 vooral in A–C."
    )


def render_leefbaarheidspunten_weight_controls(
    stock_manager: StockManager, contour_type: str
) -> Dict[str, Dict[str, float]]:
    """Number inputs per zone voor leefbaarheidspunten-gewichten (defaults uit zones-CSV)."""
    st.caption(
        "Punten per inwoner per zone. Leefbaarheidspunten = inwoners zonder isolatie × punten "
        "niet-geïsoleerd + inwoners met isolatie × punten geïsoleerd."
    )
    return _collect_leefbaarheidspunten_weights(stock_manager, contour_type)


def _collect_leefbaarheidspunten_weights(
    stock_manager: StockManager, contour_type: str
) -> Dict[str, Dict[str, float]]:
    defaults = stock_manager.get_default_leefbaarheidspunten_weights()
    weights: Dict[str, Dict[str, float]] = {}
    zones = stock_manager.get_zones()
    columns = st.columns(len(zones))
    for column, zone in zip(columns, zones):
        zone_defaults = defaults[zone]
        with column:
            st.caption(f"Zone {zone}")
            weights[zone] = {
                "niet_geïsoleerd": st.number_input(
                    "Niet-geïsoleerd",
                    min_value=0.0,
                    value=float(zone_defaults["niet_geïsoleerd"]),
                    step=1.0,
                    key=f"leefbaarheidspunten_niet_{contour_type}_{zone}",
                ),
                "geïsoleerd": st.number_input(
                    "Geïsoleerd",
                    min_value=0.0,
                    value=float(zone_defaults["geïsoleerd"]),
                    step=1.0,
                    key=f"leefbaarheidspunten_iso_{contour_type}_{zone}",
                ),
            }
    return weights


def render_leefbaarheidspunten_section(stock_manager: StockManager) -> None:
    """Render grouped bar chart for leefbaarheidspunten (weights/KPI's staan hoger op de pagina)."""
    render_leefbaarheidspunten_chart(stock_manager.get_dataframe().reset_index())


def render_leefbaarheidspunten_chart(df_stock: pd.DataFrame) -> None:
    """Staafgrafiek per zone: beginjaar/eindjaar, gestapeld niet-geïsoleerd vs geïsoleerd."""
    metric_labels = {
        "leefbaarheidspunten_zonder_isolatie": "Niet-geïsoleerd",
        "leefbaarheidspunten_met_isolatie": "Geïsoleerd",
    }
    isolatie_kleuren = {
        "Niet-geïsoleerd": _CHART_KLEUR_A,
        "Geïsoleerd": _CHART_KLEUR_B,
    }
    rows = []
    for metric_name, isolatie_label in metric_labels.items():
        subset = df_stock[
            (df_stock["naam"] == metric_name)
            & (df_stock["zone"] != "Totaal")
            & (df_stock["jaar"].isin([BEGINJAAR, EINDJAAR]))
        ]
        for _, row in subset.iterrows():
            jaar = int(row["jaar"])
            rows.append(
                {
                    "zone": row["zone"],
                    "jaar": jaar,
                    "isolatie": isolatie_label,
                    "leefbaarheidspunten": float(row["aantal"]),
                }
            )

    df_plot = pd.DataFrame(rows)
    if df_plot.empty:
        st.warning("Geen data beschikbaar voor leefbaarheidspunten.")
        return

    jaar_begin, jaar_einde = _jaar_categorieen()
    df_plot["jaar_label"] = df_plot["jaar"].astype(str)
    df_plot["jaar_label"] = pd.Categorical(
        df_plot["jaar_label"],
        categories=[jaar_begin, jaar_einde],
        ordered=True,
    )
    df_plot["isolatie_volgorde"] = df_plot["isolatie"].map({"Niet-geïsoleerd": 0, "Geïsoleerd": 1})
    df_plot["legenda"] = df_plot.apply(
        lambda row: f"{row['isolatie']} ({row['jaar']})", axis=1
    )
    legenda_domain, legenda_range = _legenda_labels_en_kleuren(
        ("Niet-geïsoleerd", "Geïsoleerd"), isolatie_kleuren
    )

    bars = (
        alt.Chart(df_plot)
        .mark_bar()
        .encode(
            x=alt.X("zone:N", title="Zone", axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("jaar_label:N", sort="ascending"),
            y=alt.Y(
                "leefbaarheidspunten:Q",
                title="Leefbaarheidspunten",
                axis=_integer_axis("Leefbaarheidspunten"),
            ),
            color=alt.Color(
                "legenda:N",
                scale=alt.Scale(domain=legenda_domain, range=legenda_range),
                legend=alt.Legend(
                    orient="right",
                    title=None,
                    symbolStrokeWidth=0,
                    labelFontSize=12,
                ),
            ),
            order=alt.Order("isolatie_volgorde:O", sort="ascending"),
            tooltip=[
                "zone",
                alt.Tooltip("jaar_label:N", title="Jaar"),
                "isolatie",
                _integer_tooltip("leefbaarheidspunten:Q", "Leefbaarheidspunten"),
            ],
        )
    )
    labels = _bar_value_labels(
        df_plot,
        x="zone",
        y="leefbaarheidspunten",
        x_offset="jaar_label",
        label_totals=True,
    )
    chart = (
        (bars + labels)
        .properties(
            title=f"Leefbaarheidspunten per zone ({BEGINJAAR} vs {EINDJAAR})",
            height=560,
        )
        .configure_view(stroke=None)
    )
    st.altair_chart(chart, width="stretch")
    st.caption(f"Per zone: links {BEGINJAAR}, rechts {EINDJAAR}.")


def plot_metric_compact(
    df_stock: pd.DataFrame,
    stock_name: str,
    title: str,
    y_label: str,
) -> None:
    """Compact line chart: totaal stock (Vlaanderen + Brussel) per zone."""
    df_plot = _stock_plot_frame(df_stock, stock_name)
    if df_plot.empty:
        st.info(f"Geen data voor: {title}")
        return

    chart = (
        alt.Chart(df_plot)
        .mark_line(point=True)
        .encode(
            x=alt.X("jaar:O", title="Jaar"),
            y=alt.Y("aantal:Q", title=y_label, axis=_integer_axis(y_label)),
            color=alt.Color("zone:N", title="Zone"),
            tooltip=[
                "zone",
                "jaar",
                _integer_tooltip("aantal:Q", y_label),
            ],
        )
        .properties(title=title, height=350)
    )
    st.altair_chart(chart, width="stretch")


def render_compact_line_charts(df_stock: pd.DataFrame) -> None:
    """Render compact line charts below the main bar chart."""
    col1, col2 = st.columns(2)
    with col1:
        plot_metric_compact(
            df_stock,
            "onbebouwde_bebouwbare_percelen",
            "Onbebouwde bebouwbare percelen per zone",
            "Aantal percelen",
        )
        plot_metric_compact(
            df_stock,
            "bewoonde_niet_geïsoleerde_woning",
            "Niet-geïsoleerde woningen per zone",
            "Aantal woningen",
        )
        plot_metric_compact(
            df_stock,
            "perceel_eigendom_overheid",
            "Percelen in eigendom overheid per zone",
            "Aantal percelen",
        )

    with col2:
        plot_metric_compact(
            df_stock,
            "onbebouwde_onbebouwbare_percelen",
            "Onbebouwde onbebouwbare percelen per zone",
            "Aantal percelen",
        )
        plot_metric_compact(
            df_stock,
            "bewoonde_geïsoleerde_woning",
            "Geïsoleerde woningen per zone",
            "Aantal woningen",
        )
        plot_metric_compact(
            df_stock,
            "woning_eigendom_overheid",
            "Woningen in eigendom overheid per zone",
            "Aantal woningen",
        )


def render_flow_log_zone_table(flow_log_zone_file: str) -> None:
    """Render geselecteerde kolommen van flow_log_zone.csv."""
    if not os.path.exists(flow_log_zone_file):
        st.warning("Flow log zone-bestand niet gevonden.")
        return

    df = pd.read_csv(flow_log_zone_file, sep=";")
    selected_columns = [
        "zone",
        "jaar",
        "naam_flow",
        "maatregel_toegepast",
        "flow_mode",
        "flow_rate",
        "inflow_stock_name",
        "outflow_stock_name",
        "delta_inflow",
        "delta_outflow",
    ]
    missing_columns = [col for col in selected_columns if col not in df.columns]
    if missing_columns:
        st.warning(f"Flow log zone mist kolommen: {', '.join(missing_columns)}")
        return

    st.subheader("Flow log per zone")
    df_display = df[selected_columns].copy()
    if "flow_rate" in df_display.columns:
        df_display["flow_rate"] = df_display["flow_rate"].map(
            lambda v: format_number(v) if pd.notna(v) else ""
        )
    for col in ("delta_inflow", "delta_outflow"):
        if col in df_display.columns:
            df_display[col] = df_display[col].map(
                lambda v: format_integer(v) if pd.notna(v) else ""
            )
    st.dataframe(df_display, width="stretch")
