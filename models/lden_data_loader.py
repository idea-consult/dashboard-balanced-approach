"""Load real Lden analysis outputs for the dashboard simulator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd

INDEX_NAME = "db_ondergrens"

REGIO_NL_TO_KEY = {
    "Vlaams Gewest": "vlaanderen",
    "Brussels Hoofdstedelijk Gewest": "brussel",
}

STOCK_COLUMNS = (
    "onbebouwde_bebouwbare_percelen",
    "onbebouwde_onbebouwbare_percelen",
    "bewoonde_niet_geïsoleerde_woning",
    "bewoonde_geïsoleerde_woning",
    "nieuwe_woning",
    "perceel_eigendom_overheid",
    "woning_eigendom_overheid",
)

# flow_size.csv uses verkavelings_verbod; measures.csv uses verkavelingsverbod
MEASURE_ID_TO_FLOW_COLUMN: Dict[str, str] = {
    "verkavelingsverbod": "verkavelings_verbod",
}

PRICE_COLUMNS = (
    "bewoonde_geïsoleerde_woning_prijs",
    "bewoonde_niet_geïsoleerde_woning_prijs",
    "onbebouwde_bebouwbare_percelen_prijs",
)

PRICE_COLUMN_ALIASES = {
    "prijs_bewoonde_geïsoleerde_woning": "bewoonde_geïsoleerde_woning_prijs",
    "prijs_bewoonde_niet_geïsoleerde_woning": "bewoonde_niet_geïsoleerde_woning_prijs",
    "prijs_onbebouwde_bebouwbare_percelen": "onbebouwde_bebouwbare_percelen_prijs",
    "prijs_onbebouwde_onbebouwbare_percelen": "onbebouwde_bebouwbare_percelen_prijs",
}


@dataclass(frozen=True)
class LdenLoadedData:
    """Contour frame + per-band flow rates from analysis CSV exports."""

    df_contour: pd.DataFrame
    flow_rates_by_band: Dict[int, Dict[str, Tuple[float, float]]]
    bands: Tuple[int, ...]
    band_to_zone: Dict[int, str]


def _flow_column_prefix(measure_id: str) -> str:
    return MEASURE_ID_TO_FLOW_COLUMN.get(measure_id, measure_id)


def _map_midden_to_zone(midden: float, df_zones: pd.DataFrame) -> str:
    for _, zone_row in df_zones.iterrows():
        if zone_row["min dBel"] <= midden < zone_row["max dBel"]:
            return str(zone_row["zone"])
    return "Onbekend"


def _aggregate_regional_stocks(stocks_file: str) -> pd.DataFrame:
    usecols = ["db_lden", "regio_nl", *STOCK_COLUMNS]
    raw = pd.read_csv(stocks_file, usecols=usecols)
    raw = raw[raw["regio_nl"].isin(REGIO_NL_TO_KEY)].copy()
    raw["regio"] = raw["regio_nl"].map(REGIO_NL_TO_KEY)

    grouped = (
        raw.groupby(["db_lden", "regio"], as_index=False)[list(STOCK_COLUMNS)]
        .sum()
        .astype({col: float for col in STOCK_COLUMNS})
    )

    wide: Dict[str, pd.Series] = {}
    for stock in STOCK_COLUMNS:
        for regio in ("vlaanderen", "brussel"):
            col_name = f"{stock}_{regio}"
            subset = grouped[grouped["regio"] == regio].set_index("db_lden")[stock]
            wide[col_name] = subset

    out = pd.DataFrame(wide).fillna(0.0)
    out.index = out.index.astype(int)
    out.index.name = INDEX_NAME
    return out.sort_index()


def _split_inwoners_by_region(
    regional_stocks: pd.DataFrame, flow_size: pd.DataFrame
) -> pd.DataFrame:
    flow = flow_size.set_index("db_lden")
    flow.index = flow.index.astype(int)

    woningen_vla = (
        regional_stocks["bewoonde_niet_geïsoleerde_woning_vlaanderen"]
        + regional_stocks["bewoonde_geïsoleerde_woning_vlaanderen"]
    )
    woningen_br = (
        regional_stocks["bewoonde_niet_geïsoleerde_woning_brussel"]
        + regional_stocks["bewoonde_geïsoleerde_woning_brussel"]
    )
    woningen_totaal = woningen_vla + woningen_br

    inwoners_overlap = flow["inwoners_overlap"].reindex(regional_stocks.index).fillna(0.0)
    share_vla = woningen_vla / woningen_totaal.replace(0, np.nan)
    share_vla = share_vla.fillna(0.5)

    inwoners_vla = inwoners_overlap * share_vla
    inwoners_br = inwoners_overlap - inwoners_vla

    gem_vla = inwoners_vla / woningen_vla.replace(0, np.nan)
    gem_br = inwoners_br / woningen_br.replace(0, np.nan)
    gem_totaal = inwoners_overlap / woningen_totaal.replace(0, np.nan)

    return pd.DataFrame(
        {
            "inwoners_vlaanderen": inwoners_vla.fillna(0.0),
            "inwoners_brussel": inwoners_br.fillna(0.0),
            "inwoners_per_contour": inwoners_overlap.fillna(0.0),
            "gemiddeld_aantal_inwoners_per_huis_vlaanderen": gem_vla.fillna(2.5),
            "gemiddeld_aantal_inwoners_per_huis_brussel": gem_br.fillna(2.5),
            "gemiddeld_aantal_inwoners_per_huis": gem_totaal.fillna(2.5),
        },
        index=regional_stocks.index,
    )


def _dosis_effect_series(index: pd.Index) -> pd.Series:
    db = index.astype(float) + 0.5
    return pd.Series(0.01 * np.exp(0.08 * (db - 45)), index=index, dtype=float)


def _parse_flow_rates(
    flow_size_file: str, measure_ids: Tuple[str, ...]
) -> Dict[int, Dict[str, Tuple[float, float]]]:
    flow_df = pd.read_csv(flow_size_file)
    flow_df["db_lden"] = flow_df["db_lden"].astype(int)
    rates: Dict[int, Dict[str, Tuple[float, float]]] = {}

    for _, row in flow_df.iterrows():
        db = int(row["db_lden"])
        band_rates: Dict[str, Tuple[float, float]] = {}
        for measure_id in measure_ids:
            prefix = _flow_column_prefix(measure_id)
            bl_col = f"{prefix}_baseline"
            act_col = f"{prefix}_active"
            baseline = float(row[bl_col]) if bl_col in flow_df.columns else 0.0
            active = float(row[act_col]) if act_col in flow_df.columns else 0.0
            band_rates[measure_id] = (min(baseline, 1.0), min(active, 1.0))
        rates[db] = band_rates
    return rates


def load_lden_data(
    *,
    stocks_file: str,
    flow_size_file: str,
    stock_prices_file: str,
    zones_file: str,
    measure_ids: Tuple[str, ...],
) -> LdenLoadedData:
    """Build band-level contour frame and per-band flow rates."""
    df_zones = pd.read_csv(zones_file)
    df_zones = df_zones.dropna(subset=["zone"]).reset_index(drop=True)
    df_zones = df_zones.sort_values("min dBel", ascending=False).reset_index(drop=True)

    regional = _aggregate_regional_stocks(stocks_file)
    flow_size = pd.read_csv(flow_size_file)
    prices = pd.read_csv(stock_prices_file)
    prices["db_lden"] = prices["db_lden"].astype(int)
    prices = prices.set_index("db_lden")

    inwoners = _split_inwoners_by_region(regional, flow_size)

    df_contour = regional.join(inwoners, how="left")
    for price_col in PRICE_COLUMNS:
        if price_col in prices.columns:
            df_contour[price_col] = prices[price_col].reindex(df_contour.index).fillna(0.0)
    for alias, source in PRICE_COLUMN_ALIASES.items():
        if source in df_contour.columns:
            df_contour[alias] = df_contour[source]

    if "onbebouwde_bebouwbare_percelen_prijs" in df_contour.columns:
        df_contour["prijs_onbebouwde_onbebouwbare_percelen"] = df_contour[
            "onbebouwde_bebouwbare_percelen_prijs"
        ]

    df_contour["dosis_effect_relatie"] = _dosis_effect_series(df_contour.index)
    db_midden = df_contour.index.astype(float) + 0.5
    df_contour["zone"] = db_midden.map(lambda m: _map_midden_to_zone(m, df_zones))
    df_contour = df_contour[df_contour["zone"] != "Onbekend"]

    bands = tuple(int(b) for b in sorted(df_contour.index.tolist()))
    band_to_zone = {band: str(df_contour.loc[band, "zone"]) for band in bands}
    flow_rates_by_band = {
        db: rates for db, rates in _parse_flow_rates(flow_size_file, measure_ids).items()
        if db in band_to_zone
    }

    return LdenLoadedData(
        df_contour=df_contour,
        flow_rates_by_band=flow_rates_by_band,
        bands=bands,
        band_to_zone=band_to_zone,
    )
