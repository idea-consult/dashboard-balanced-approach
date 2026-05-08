"""UI components for displaying metrics and charts."""

import streamlit as st
import altair as alt
import pandas as pd
import os
from models.stock_manager import StockManager
from models.measure_selection_manager import MeasureSelectionManager
from models.validation import validate_measure_combinations
from config import BEGINJAAR, EINDJAAR


def render_sidebar_controls(measure_selection_manager: MeasureSelectionManager, zones):
    """
    Render sidebar controls for measure selection.

    Args:
        measure_selection_manager: MeasureSelectionManager instance
    """
    df_beschrijving_maatregelen = measure_selection_manager.get_measure_descriptions()
    hidden_measures = measure_selection_manager.get_hidden_measures()
    grouped_measures = measure_selection_manager.get_measure_groups()
    grouped_measure_names = {
        measure for measures in grouped_measures.values() for measure in measures
    }

    with st.sidebar:
        for group_id, measure_names in grouped_measures.items():
            if any(measure in hidden_measures for measure in measure_names):
                continue
            if not all(
                measure in df_beschrijving_maatregelen.index for measure in measure_names
            ):
                continue
            combined_selected = tuple(
                sorted(
                    set().union(
                        *(set(measure_selection_manager.get_selected_zones(measure)) for measure in measure_names)
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

        for maatregel in df_beschrijving_maatregelen.index.get_level_values("naam"):
            if maatregel in hidden_measures:
                continue
            if maatregel in grouped_measure_names:
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


def render_metrics(
    stock_manager: StockManager,
    kost_overheid: float,
    kost_prive: float,
) -> None:
    """
    Render key metrics in columns.

    Args:
        stock_manager: StockManager instance
    """
    col_hinder, col_overheid, col_prive = st.columns(3)

    begin = stock_manager.get_aantal("totaal_gehinderde_personen", BEGINJAAR, "Totaal")
    eind = stock_manager.get_aantal("totaal_gehinderde_personen", EINDJAAR, "Totaal")
    delta_pct = 0 if begin == 0 else int(100 * (eind - begin) / begin)
    with col_hinder:
        st.metric(
            "Totaal aantal gehinderde personen",
            f"{int(eind)}",
            f"{delta_pct} %",
            delta_color="inverse",
        )

    with col_overheid:
        st.metric("Totale kost overheid", f"{kost_overheid:,.0f} euro")
    with col_prive:
        st.metric("Totale kost privé", f"{kost_prive:,.0f} euro")


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
    df_plot = df_stock[
        (df_stock["naam"] == stock_name) & (df_stock["zone"] != "Totaal")
    ]
    chart = (
        alt.Chart(df_plot)
        .mark_line(point=True)
        .encode(
            x=alt.X("jaar:O", title="Jaar"),
            y=alt.Y("aantal:Q", title=y_label),
            color=alt.Color("zone:N", title="Zone"),
            tooltip=["zone", "jaar", "aantal"],
        )
        .properties(title=title, width=500, height=300)
    )
    st.altair_chart(chart, use_container_width=True)


def render_charts(stock_manager: StockManager) -> None:
    """
    Render grouped bar chart for ernstig gehinderden (begin vs einde) per zone.

    Args:
        stock_manager: StockManager instance
    """
    df_stock = stock_manager.get_dataframe().reset_index()
    render_ernstig_gehinderden_chart(df_stock)
    render_compact_line_charts(df_stock)


def render_ernstig_gehinderden_chart(df_stock: pd.DataFrame) -> None:
    """Render grouped bar chart with begin and end year values per zone."""
    metric_name = "hinderpunten"
    df_plot = df_stock[
        (df_stock["naam"] == metric_name)
        & (df_stock["zone"] != "Totaal")
        & (df_stock["jaar"].isin([BEGINJAAR, EINDJAAR]))
    ].copy()
    if df_plot.empty:
        st.warning("Geen data beschikbaar voor aantal ernstig gehinderden.")
        return

    year_label = {BEGINJAAR: "Begin traject", EINDJAAR: "Einde traject"}
    df_plot["moment"] = df_plot["jaar"].map(year_label)
    df_plot["aantal_ernstig_gehinderden"] = df_plot["aantal"]

    chart = (
        alt.Chart(df_plot)
        .mark_bar()
        .encode(
            x=alt.X("zone:N", title="Zone", axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("moment:N"),
            y=alt.Y("aantal_ernstig_gehinderden:Q", title="Aantal ernstig gehinderden"),
            color=alt.Color("moment:N", title="Moment"),
            tooltip=["zone", "moment", "aantal_ernstig_gehinderden"],
        )
        .properties(
            title="Aantal ernstig gehinderden per zone (begin vs einde traject)",
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
    """Create and display a compact line chart for a specific stock metric."""
    df_plot = df_stock[
        (df_stock["naam"] == stock_name) & (df_stock["zone"] != "Totaal")
    ]
    if df_plot.empty:
        st.info(f"Geen data voor: {title}")
        return

    chart = (
        alt.Chart(df_plot)
        .mark_line(point=True)
        .encode(
            x=alt.X("jaar:O", title="Jaar"),
            y=alt.Y("aantal:Q", title=y_label),
            color=alt.Color("zone:N", title="Zone"),
            tooltip=["zone", "jaar", "aantal"],
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
    st.dataframe(df[selected_columns], width="stretch")
