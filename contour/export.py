"""Export contour tables and flow rates to dashboard input files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from contour.paths import (
    FLOW_RULES_FILE,
    LDEN_CONTOUR_FILE,
    LDEN_CONTOUR_REGIONAL_FILE,
    LNIGHT_CONTOUR_FILE,
    LNIGHT_CONTOUR_REGIONAL_FILE,
)
from contour.schema import contour_voor_export, regional_voor_export


def export_lden_contour(df_lden: pd.DataFrame, pad: Path | None = None) -> Path:
    out = pad or LDEN_CONTOUR_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    contour_voor_export(df_lden).to_csv(out, index=False)
    return out


def export_lnight_contour(df_lnight: pd.DataFrame, pad: Path | None = None) -> Path:
    out = pad or LNIGHT_CONTOUR_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    contour_voor_export(df_lnight).to_csv(out, index=False)
    return out


def export_lden_contour_regional(df_regional: pd.DataFrame, pad: Path | None = None) -> Path:
    out = pad or LDEN_CONTOUR_REGIONAL_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    regional_voor_export(df_regional).to_csv(out, index=False)
    return out


def export_lnight_contour_regional(df_regional: pd.DataFrame, pad: Path | None = None) -> Path:
    out = pad or LNIGHT_CONTOUR_REGIONAL_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    regional_voor_export(df_regional).to_csv(out, index=False)
    return out


def update_flow_rules_rates(
    flow_rates: pd.DataFrame,
    pad: Path | None = None,
) -> pd.DataFrame:
    """Update only flow_rate_baseline and flow_rate_active in flow_rules.csv."""
    pad = pad or FLOW_RULES_FILE
    rules = pd.read_csv(pad)
    rates = flow_rates.set_index("measure_id")
    for idx, row in rules.iterrows():
        mid = row["measure_id"]
        if mid in rates.index:
            rules.at[idx, "flow_rate_baseline"] = rates.at[mid, "flow_rate_baseline"]
            rules.at[idx, "flow_rate_active"] = rates.at[mid, "flow_rate_active"]
    rules.to_csv(pad, index=False)
    return rules
