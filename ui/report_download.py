"""Streamlit UI for downloading the Typst PDF report."""

from __future__ import annotations

import streamlit as st

from models.measure_selection_manager import MeasureSelectionManager
from models.scenario_manager import NONE_SCENARIO_ID, NONE_SCENARIO_LABEL
from models.stock_manager import StockManager
from reports.compile import compile_simulation_report
from ui.components import ERNSTIG_METHODE_KEY, SCENARIO_RADIO_KEY


def render_pdf_report_download(
    *,
    stock_manager: StockManager,
    measure_selection_manager: MeasureSelectionManager,
    kost_overheid: float,
    kost_prive: float,
    ernstig_gehinderden_methode: str | None = None,
) -> None:
    """Section at bottom of dashboard: generate and download PDF snapshot."""
    st.divider()
    st.subheader("Rapport")
    st.caption(
        "Download een PDF-snapshot van deze simulatie (maatregelen, KPI’s, "
        "kosten, grafieken en flow rates). Gegenereerd met Typst."
    )

    scenario_id = st.session_state.get(SCENARIO_RADIO_KEY, NONE_SCENARIO_ID)
    scenario_label = st.session_state.get("_scenario_radio_label", NONE_SCENARIO_LABEL)
    methode = ernstig_gehinderden_methode or st.session_state.get(
        ERNSTIG_METHODE_KEY, "A"
    )

    if st.button("Genereer PDF-rapport", type="primary", key="generate_pdf_report"):
        with st.spinner("Rapport genereren (grafieken + Typst)…"):
            try:
                pdf_bytes = compile_simulation_report(
                    stock_manager=stock_manager,
                    measure_selection_manager=measure_selection_manager,
                    kost_overheid=kost_overheid,
                    kost_prive=kost_prive,
                    scenario_id=str(scenario_id),
                    scenario_label=str(scenario_label),
                    ernstig_gehinderden_methode=str(methode),
                )
            except Exception as exc:  # noqa: BLE001 — show in UI
                st.error(f"PDF-generatie mislukt: {exc}")
                return
            st.session_state["_pdf_report_bytes"] = pdf_bytes
            st.success("Rapport klaar — download hieronder.")

    pdf_bytes = st.session_state.get("_pdf_report_bytes")
    if pdf_bytes:
        st.download_button(
            label="Download PDF-rapport",
            data=pdf_bytes,
            file_name="balanced_approach_simulatierapport.pdf",
            mime="application/pdf",
            key="download_pdf_report",
        )
