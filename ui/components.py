"""UI components for displaying metrics and charts."""

import streamlit as st
import altair as alt
import pandas as pd
from models.stock_manager import StockManager
from models.flow_manager import FlowManager
from models.validation import validate_measure_combinations, get_conflict_message
from config import ZONES, BEGINJAAR, EINDJAAR


def render_sidebar_controls(flow_manager: FlowManager):
    """
    Render sidebar controls for measure selection.
    
    Args:
        flow_manager: FlowManager instance
    """
    df_beschrijving_maatregelen = flow_manager.get_measure_descriptions()
    
    with st.sidebar:
        for maatregel in df_beschrijving_maatregelen.index.get_level_values("naam"):
            selected = st.segmented_control(
                label=df_beschrijving_maatregelen.at[maatregel, "naam_mooi"],
                options=ZONES,
                help=df_beschrijving_maatregelen.at[maatregel, "help"],
                selection_mode="multi",
                default=flow_manager.get_selected_zones(maatregel),
                key=f"seg_{maatregel}",
                width="stretch",
            )
            flow_manager.set_selected_zones(maatregel, selected)

    # Valideer maatregel combinaties na alle selecties (buiten de sidebar)
    conflicts = validate_measure_combinations(flow_manager)
    return conflicts


def render_metrics(stock_manager: StockManager) -> None:
    """
    Render key metrics in columns.
    
    Args:
        stock_manager: StockManager instance
    """
    links, midden, rechts = st.columns(3)
    
    with links:
        change_metric(stock_manager, "hinderpunten_isolatie", "Hinderpunten voor mensen met isolatie")
        change_metric(stock_manager, "gehinderde_personen_met_isolatie", "Gehinderde geïsoleerde personen")
    
    with midden:
        change_metric(stock_manager, "hinderpunten_zonder_isolatie", "Hinderpunten voor mensen zonder isolatie")
        change_metric(stock_manager, "gehinderde_personen_zonder_isolatie", "Gehinderde niet-geïsoleerde personen")
    
    with rechts:
        change_metric(stock_manager, "hinderpunten", "Hinderpunten")
        change_metric(stock_manager, "totaal_gehinderde_personen", "Totaal aantal gehinderde personen")


def change_metric(stock_manager: StockManager, metric: str, mooie_naam: str) -> None:
    """
    Display a metric with change from beginning to end.
    
    Args:
        stock_manager: StockManager instance
        metric: Metric name
        mooie_naam: Display name
    """
    begin = stock_manager.get_aantal(metric, BEGINJAAR, "Totaal")
    eind = stock_manager.get_aantal(metric, EINDJAAR, "Totaal")
    st.metric(
        mooie_naam,
        f"{int(eind)}",
        f"{int(100 * (eind - begin) / begin)} %",
        delta_color="inverse",
    )


def render_total_cost(flow_manager: FlowManager) -> None:
    """
    Render total cost metric.
    
    Args:
        flow_manager: FlowManager instance
    """
    st.metric(
        "Totale kost van de maatregels",
        flow_manager.get_total_cost(),
        format="euro",
    )


def plot_metric(df_stock: pd.DataFrame, stock_name: str, title: str, y_label: str) -> None:
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
    Render visualization charts.
    
    Args:
        stock_manager: StockManager instance
    """
    col1, col2 = st.columns(2)
    df_stock = stock_manager.get_dataframe().reset_index()
    
    with col1:
        plot_metric(
            df_stock,
            "onbebouwde_bebouwbare_percelen",
            "Evolutie van onbebouwde bebouwbare percelen per zone",
            "# onbebouwde bebouwbare perc",
        )
        plot_metric(
            df_stock,
            "onbebouwde_onbebouwbare_percelen",
            "Evolutie van onbebouwde onbebouwbare percelen per zone",
            "# onbebouwde onbebouwbare perc",
        )
    
    with col2:
        plot_metric(
            df_stock,
            "bewoonde_niet_geïsoleerde_woning",
            "Evolutie van niet geïsoleerde woningen per zone",
            "Aantal woningen",
        )
        plot_metric(
            df_stock,
            "bewoonde_geïsoleerde_woning",
            "Evolutie van geïsoleerde woningen per zone",
            "Aantal woningen",
        )
