"""Flow rates for measure help tooltips (from flow_size.csv, same as simulation)."""

from __future__ import annotations

import pandas as pd

from models.lden_data_loader import MEASURE_ID_TO_FLOW_COLUMN

# Noemer-stock per maatregel (zelfde mapping als contour/flows_per_contour.py).
NOEMER_BY_MEASURE: dict[str, str] = {
    "woongebiedverbod": "onbebouwde_onbebouwbare_percelen",
    "aankoopbeleid_percelen": "onbebouwde_bebouwbare_percelen",
    "voorkooprecht_percelen": "onbebouwde_bebouwbare_percelen",
    "verbod_kleine_woning": "onbebouwde_bebouwbare_percelen",
    "verbod_grote_woning": "onbebouwde_bebouwbare_percelen",
    "verbod_kwetsbare_groep": "onbebouwde_bebouwbare_percelen",
    "woonverdichtingsverbod_niet_geïsoleerde_woningen": "bewoonde_niet_geïsoleerde_woning",
    "woonverdichtingsverbod_geïsoleerde_woningen": "bewoonde_geïsoleerde_woning",
    "aankoopbeleid_niet_geïsoleerde_woningen": "bewoonde_niet_geïsoleerde_woning",
    "aankoopbeleid_geïsoleerde_woningen": "bewoonde_geïsoleerde_woning",
    "voorkooprecht_niet_geïsoleerde_woningen": "bewoonde_niet_geïsoleerde_woning",
    "voorkooprecht_geïsoleerde_woningen": "bewoonde_geïsoleerde_woning",
    "isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning": "nieuwe_woning",
    "isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning": "nieuwe_woning",
    "renovatie_zonder_maatregel": "bewoonde_niet_geïsoleerde_woning",
    "verplicht_isoleren_renovatie": "bewoonde_niet_geïsoleerde_woning",
    "gesubsidieerd_isolatieprogramma": "bewoonde_niet_geïsoleerde_woning",
    "gestuurd_isolatieprogramma": "bewoonde_niet_geïsoleerde_woning",
    "aanleg_geluidsbuffers": "bewoonde_niet_geïsoleerde_woning",
}


def _flow_column_prefix(measure_id: str) -> str:
    return MEASURE_ID_TO_FLOW_COLUMN.get(measure_id, measure_id)


def _weighted_mean(rate: pd.Series, weight: pd.Series) -> float:
    w = weight.astype(float)
    total = float(w.sum())
    if total <= 0:
        return 0.0
    return float((rate.astype(float) * w).sum() / total)


def summarize_measure_rates(flow_size: pd.DataFrame, measure_id: str) -> tuple[float, float]:
    """Gewogen gemiddelde baseline/active over LDEN-bands (zelfde bron als simulatie)."""
    prefix = _flow_column_prefix(measure_id)
    bl_col = f"{prefix}_baseline"
    act_col = f"{prefix}_active"
    if bl_col not in flow_size.columns or act_col not in flow_size.columns:
        return 0.0, 0.0

    baseline_s = flow_size[bl_col]
    active_s = flow_size[act_col]
    noemer_col = NOEMER_BY_MEASURE.get(measure_id)
    if noemer_col and noemer_col in flow_size.columns:
        weight = flow_size[noemer_col]
        return (
            min(_weighted_mean(baseline_s, weight), 1.0),
            min(_weighted_mean(active_s, weight), 1.0),
        )
    return (
        min(float(baseline_s.mean()), 1.0),
        min(float(active_s.mean()), 1.0),
    )


def apply_flow_size_rates_to_rules(
    flow_rules: pd.DataFrame, flow_size: pd.DataFrame
) -> pd.DataFrame:
    """Vervang flow_rate_* in flow_rules door aggregaten uit flow_size.csv."""
    if flow_rules.empty:
        return flow_rules

    out = flow_rules.copy()
    for idx, row in out.iterrows():
        measure_id = str(row["measure_id"])
        baseline, active = summarize_measure_rates(flow_size, measure_id)
        out.at[idx, "flow_rate_baseline"] = baseline
        out.at[idx, "flow_rate_active"] = active
    return out
