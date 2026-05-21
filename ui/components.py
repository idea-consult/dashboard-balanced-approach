"""UI components for displaying metrics and charts."""

import streamlit as st
import altair as alt
import pandas as pd
import os
from typing import Dict

from models.stock_manager import StockManager
from models.measure_selection_manager import MeasureSelectionManager
from models.validation import validate_measure_combinations
from simulation.engine import SimulationEngine
from config import BEGINJAAR, EINDJAAR
from ui.formatting import (
    ALTAIR_INTEGER_FORMAT,
    format_euro,
    format_integer,
    format_number,
    format_percent,
)


def render_sidebar_controls(measure_selection_manager: MeasureSelectionManager, zones):
    """
    Render sidebar controls for measure selection.

    Args:
        measure_selection_manager: MeasureSelectionManager instance
    """
    df_beschrijving_maatregelen = measure_selection_manager.get_measure_descriptions()
    hidden_measures = measure_selection_manager.get_hidden_measures()
    grouped_measures = measure_selection_manager.get_measure_groups()

    with st.sidebar:
        for entry_kind, entry_key in measure_selection_manager.get_ui_sidebar_entries():
            if entry_kind == "group":
                group_id = entry_key
                measure_names = grouped_measures[group_id]
                if any(measure in hidden_measures for measure in measure_names):
                    continue
                if not all(
                    measure in df_beschrijving_maatregelen.index for measure in measure_names
                ):
                    continue
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
                combined_help = "\n\n".join(
                    str(df_beschrijving_maatregelen.at[measure, "help"])
                    for measure in measure_names
                )
                group_label = group_id.replace("_", " ").capitalize()
                selected_group = st.segmented_control(
                    label=group_label,
                    options=zones,
                    help=combined_help,
                    selection_mode="multi",
                    default=combined_selected,
                    key=f"seg_group_{group_id}",
                    width="stretch",
                )
                for measure in measure_names:
                    measure_selection_manager.set_selected_zones(measure, selected_group)
                continue

            maatregel = entry_key
            if maatregel in hidden_measures:
                continue
            selected = st.segmented_control(
                label=df_beschrijving_maatregelen.at[maatregel, "naam_mooi"],
                options=zones,
                help=df_beschrijving_maatregelen.at[maatregel, "help"],
                selection_mode="multi",
                default=measure_selection_manager.get_selected_zones(maatregel),
                key=f"seg_{maatregel}",
                width="stretch",
            )
            measure_selection_manager.set_selected_zones(maatregel, selected)

    # Valideer maatregel combinaties na alle selecties (buiten de sidebar)
    conflicts = validate_measure_combinations(measure_selection_manager, tuple(zones))
    return conflicts


def _delta_pct(begin: float, eind: float) -> int:
    if begin == 0:
        return 0
    return int(100 * (eind - begin) / begin)


def _integer_axis(title: str) -> alt.Axis:
    return alt.Axis(title=title, format=ALTAIR_INTEGER_FORMAT)


def _integer_tooltip(field: str, title: str) -> alt.Tooltip:
    return alt.Tooltip(field, title=title, format=ALTAIR_INTEGER_FORMAT)


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
    """KPI's bovenaan: gehinderden (totaal/Vlaanderen/Brussel) en kosten."""
    col_totaal, col_vl, col_br, col_overheid, col_prive = st.columns(5)

    with col_totaal:
        _render_traject_metric(
            stock_manager, "totaal_gehinderde_personen", "Totaal aantal gehinderde personen"
        )
    with col_vl:
        _render_traject_metric(
            stock_manager,
            "totaal_gehinderde_personen_vlaanderen",
            "Totaal aantal gehinderde Vlamingen",
        )
    with col_br:
        _render_traject_metric(
            stock_manager,
            "totaal_gehinderde_personen_brussel",
            "Totaal aantal gehinderde Brusselaars",
        )
    with col_overheid:
        st.metric("Totale kost overheid", format_euro(kost_overheid))
    with col_prive:
        st.metric("Totale kost privé", format_euro(kost_prive))


def render_leefbaarheidspunten_metrics(stock_manager: StockManager) -> None:
    """Leefbaarheidspunten-KPI's (einde traject) binnen de instellingen-expander."""
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
    with st.expander("Instelling leefbaarheidspunten per zone", expanded=False):
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
    st.altair_chart(chart, use_container_width=True)


def render_charts(stock_manager: StockManager) -> None:
    """Render charts for ernstig gehinderden, leefbaarheidspunten, and stock line charts."""
    df_stock = stock_manager.get_dataframe().reset_index()
    render_ernstig_gehinderden_chart(df_stock)
    render_leefbaarheidspunten_section(stock_manager)
    render_compact_line_charts(df_stock)


def render_ernstig_gehinderden_chart(df_stock: pd.DataFrame) -> None:
    """Staafgrafiek per zone: begin/einde traject, opgesplitst Vlaanderen vs Brussel."""
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

    moment_begin = "Begin traject"
    moment_einde = "Einde traject"
    year_label = {BEGINJAAR: moment_begin, EINDJAAR: moment_einde}
    df_plot["moment"] = df_plot["jaar"].map(year_label)
    df_plot["regio"] = df_plot["naam"].map(regional_metrics)
    df_plot["aantal_ernstig_gehinderden"] = df_plot["aantal"]

    regio_kleuren = {
        "Vlaanderen": {"normaal": "#4E2567", "licht": "#A68BB8"},
        "Brussel": {"normaal": "#DD5B61", "licht": "#F0A8AC"},
    }
    moment_kort = {moment_begin: "begin", moment_einde: "einde"}
    df_plot["moment"] = pd.Categorical(
        df_plot["moment"],
        categories=[moment_begin, moment_einde],
        ordered=True,
    )
    df_plot["regio_volgorde"] = df_plot["regio"].map({"Vlaanderen": 0, "Brussel": 1})
    df_plot["legenda"] = (
        df_plot["regio"]
        + " ("
        + df_plot["moment"].astype(str).map(moment_kort)
        + ")"
    )
    legenda_domain = [
        "Vlaanderen (begin)",
        "Brussel (begin)",
        "Vlaanderen (einde)",
        "Brussel (einde)",
    ]
    legenda_range = [
        regio_kleuren["Vlaanderen"]["licht"],
        regio_kleuren["Brussel"]["licht"],
        regio_kleuren["Vlaanderen"]["normaal"],
        regio_kleuren["Brussel"]["normaal"],
    ]

    chart = (
        alt.Chart(df_plot)
        .mark_bar()
        .encode(
            x=alt.X("zone:N", title="Zone", axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("moment:N", sort="ascending"),
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
                "moment",
                "regio",
                _integer_tooltip("aantal_ernstig_gehinderden:Q", "Aantal ernstig gehinderden"),
            ],
        )
        .properties(
            title="Ernstig gehinderden per zone — Vlaanderen en Brussel (begin vs einde traject)",
            height=560,
        )
        .configure_view(stroke=None)
    )
    st.altair_chart(chart, use_container_width=True)
    st.caption("Per zone: links begin traject, rechts einde traject.")


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
    st.subheader("Leefbaarheidspunten per zone")
    render_leefbaarheidspunten_chart(stock_manager.get_dataframe().reset_index())


def render_leefbaarheidspunten_chart(df_stock: pd.DataFrame) -> None:
    """Grouped bar chart: leefbaarheidspunten met/zonder isolatie, begin vs einde per zone."""
    year_label = {BEGINJAAR: "Begin traject", EINDJAAR: "Einde traject"}
    metric_labels = {
        "leefbaarheidspunten_zonder_isolatie": "Zonder isolatie",
        "leefbaarheidspunten_met_isolatie": "Met isolatie",
    }
    rows = []
    for metric_name, isolatie_label in metric_labels.items():
        subset = df_stock[
            (df_stock["naam"] == metric_name)
            & (df_stock["zone"] != "Totaal")
            & (df_stock["jaar"].isin([BEGINJAAR, EINDJAAR]))
        ]
        for _, row in subset.iterrows():
            moment = year_label[int(row["jaar"])]
            rows.append(
                {
                    "zone": row["zone"],
                    "moment": moment,
                    "isolatie": isolatie_label,
                    "categorie": f"{moment} – {isolatie_label}",
                    "leefbaarheidspunten": float(row["aantal"]),
                }
            )

    df_plot = pd.DataFrame(rows)
    if df_plot.empty:
        st.warning("Geen data beschikbaar voor leefbaarheidspunten.")
        return

    chart = (
        alt.Chart(df_plot)
        .mark_bar()
        .encode(
            x=alt.X("zone:N", title="Zone", axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("categorie:N"),
            y=alt.Y(
                "leefbaarheidspunten:Q",
                title="Leefbaarheidspunten",
                axis=_integer_axis("Leefbaarheidspunten"),
            ),
            color=alt.Color("isolatie:N", title="Isolatie"),
            tooltip=[
                "zone",
                "moment",
                "isolatie",
                _integer_tooltip("leefbaarheidspunten:Q", "Leefbaarheidspunten"),
            ],
        )
        .properties(
            title="Leefbaarheidspunten per zone (begin vs einde traject)",
            height=560,
        )
    )
    st.altair_chart(chart, width="stretch")


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
