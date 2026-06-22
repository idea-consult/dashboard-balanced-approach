"""Stock manager for handling stock data operations."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

from config import OUTPUT_STOCK_FILE

try:
    from contour.schema import (
        FLOW_KOLOMMEN,
        FLOW_STOCKS,
        INDEX_NAME,
        contour_uit_export,
        regional_stock_kolom,
        regional_uit_export,
    )
except ImportError:
    FLOW_KOLOMMEN = ()
    FLOW_STOCKS = ()
    INDEX_NAME = "db_ondergrens"

    def contour_uit_export(df: pd.DataFrame) -> pd.DataFrame:
        return df

    def regional_uit_export(df: pd.DataFrame) -> pd.DataFrame:
        return df

    def regional_stock_kolom(stock: str, regio: str) -> str:
        return f"{stock}_{regio}"


def resolve_regional_contour_path(contour_file: str) -> str | None:
    """Zoek bijbehorend `*_contour_regional.csv` naast het FLOW-contourbestand."""
    path = Path(contour_file)
    if path.name == "lden_contour.csv":
        regional = path.parent / "lden_contour_regional.csv"
    elif path.name == "lnight_contour.csv":
        regional = path.parent / "lnight_contour_regional.csv"
    else:
        regional = path.with_name(f"{path.stem}_regional{path.suffix}")
    return str(regional) if regional.is_file() else None


class StockManager:
    """Manages stock data with operations for getting and setting values."""

    REGIONS: Tuple[str, ...] = ("vlaanderen", "brussel")

    STOCK_TO_COLUMN_PREFIX = {
        "bewoonde_geïsoleerde_woning": "bewoonde_geïsoleerde_woning",
        "bewoonde_niet_geïsoleerde_woning": "bewoonde_niet_geïsoleerde_woning",
        "niet_bewoonde_geïsoleerde_woning": "niet_bewoonde_geïsoleerde_woning",
        "niet_bewoonde_niet_geïsoleerde_woning": "niet_bewoonde_niet_geïsoleerde_woning",
        "nieuwe_woning": "nieuwe_woning",
        "onbebouwde_bebouwbare_percelen": "onbebouwde_bebouwbare_percelen",
        "onbebouwde_onbebouwbare_percelen": "onbebouwde_onbebouwbare_percelen",
        "perceel_eigendom_overheid": "perceel_eigendom_overheid",
        "woning_eigendom_overheid": "woning_eigendom_overheid",
    }

    LEGACY_STOCK_TO_COLUMN_PREFIX = {
        "bewoonde_geïsoleerde_woning": "aantal_bewoonde_geïsoleerde_huizen",
        "bewoonde_niet_geïsoleerde_woning": "aantal_bewoonde_niet_geïsoleerde_huizen",
        "niet_bewoonde_geïsoleerde_woning": "niet_bewoonde_geïsoleerde_woning",
        "niet_bewoonde_niet_geïsoleerde_woning": "niet_bewoonde_niet_geïsoleerde_woning",
        "nieuwe_woning": "nieuwe_woning",
        "onbebouwde_bebouwbare_percelen": "aantal_onbebouwde_bebouwbare_percelen",
        "onbebouwde_onbebouwbare_percelen": "aantal_onbebouwde_onbebouwbare_percelen",
        "perceel_eigendom_overheid": "aantal_perceel_eigendom_overheid",
        "woning_eigendom_overheid": "aantal_woning_eigendom_overheid",
    }

    METRIC_COLUMN_PREFIXES = {
        "aantal_ernstig_gehinderden": "aantal_ernstig_gehinderden",
    }

    REQUIRED_STOCKS = (
        "bewoonde_geïsoleerde_woning",
        "bewoonde_niet_geïsoleerde_woning",
        "niet_bewoonde_geïsoleerde_woning",
        "niet_bewoonde_niet_geïsoleerde_woning",
        "nieuwe_woning",
        "onbebouwde_bebouwbare_percelen",
        "onbebouwde_onbebouwbare_percelen",
        "perceel_eigendom_overheid",
        "woning_eigendom_overheid",
    )

    @classmethod
    def regional_stock_names(cls) -> Tuple[str, ...]:
        """Legacy: regionale sim-stocks (alleen bij oud contour-schema)."""
        return tuple(
            f"{stock}_{regio}" for stock in cls.REQUIRED_STOCKS for regio in cls.REGIONS
        )

    @classmethod
    def simulation_stock_names(cls) -> Tuple[str, ...]:
        """Stocks zonder regional sidecar (alleen basenamen)."""
        return cls.REQUIRED_STOCKS

    def get_simulation_stock_names(self) -> Tuple[str, ...]:
        """Stocks voor de simulator: regionaal indien sidecar geladen."""
        if self._has_regional_layer:
            return self.regional_stock_names()
        return self.REQUIRED_STOCKS

    @classmethod
    def split_regional_stock_name(cls, stock_name: str) -> Tuple[str, str | None]:
        """Splits 'bewoonde_geïsoleerde_woning_vlaanderen' -> (basis, 'vlaanderen')."""
        for regio in cls.REGIONS:
            suffix = f"_{regio}"
            if stock_name.endswith(suffix):
                return stock_name[: -len(suffix)], regio
        return stock_name, None

    def __init__(
        self,
        contour_file: str,
        zones_file: str,
        beginjaar: int,
        regional_file: str | None = None,
    ):
        self.beginjaar = beginjaar
        self._has_regional_layer = False
        self.df_zones = pd.read_csv(zones_file)
        self.df_zones = self.df_zones.dropna(subset=["zone"]).reset_index(drop=True)
        self.df_zones = self.df_zones.sort_values("min dBel", ascending=False).reset_index(
            drop=True
        )

        raw = pd.read_csv(contour_file)
        if "Unnamed: 0" in raw.columns:
            raw = raw.drop(columns=["Unnamed: 0"])
        if "" in raw.columns:
            raw = raw.drop(columns=[""])

        self._flow_schema = bool(FLOW_KOLOMMEN) and set(FLOW_KOLOMMEN).issubset(set(raw.columns))
        if self._flow_schema:
            self.df_contour = contour_uit_export(raw)
        else:
            self.df_contour = raw
            if INDEX_NAME in self.df_contour.columns:
                self.df_contour = self.df_contour.set_index(INDEX_NAME)
                self.df_contour.index = self.df_contour.index.astype(int)
                self.df_contour.index.name = INDEX_NAME

        self._assign_zones()
        if self._flow_schema:
            reg_path = regional_file or resolve_regional_contour_path(contour_file)
            if reg_path:
                self._merge_regional_sidecar(reg_path)
                self._has_regional_layer = True
        self.stock_columns: Dict[str, Dict[int, str]] = {}
        self._bases_with_regional_columns: set[str] = set()
        self._pending_contour_columns: Dict[str, pd.Series] = {}
        self._register_initial_stock_columns()
        self.df_stock = self._build_aggregated_stock_table()

    def _assign_zones(self) -> None:
        if self._flow_schema or self.df_contour.index.name == INDEX_NAME:
            db_midden = self.df_contour.index.astype(float) + 0.5
            self.df_contour["zone"] = db_midden.map(self._map_midden_to_zone)
            return

        midden_col = "db_midden" if "db_midden" in self.df_contour.columns else "midden"
        if midden_col in self.df_contour.columns:
            self.df_contour["zone"] = self.df_contour[midden_col].map(self._map_midden_to_zone)
        else:
            self.df_contour["zone"] = "Onbekend"

    def _map_midden_to_zone(self, midden: float) -> str:
        for _, zone_row in self.df_zones.iterrows():
            if zone_row["min dBel"] <= midden < zone_row["max dBel"]:
                return str(zone_row["zone"])
        return "Onbekend"

    def _merge_regional_sidecar(self, regional_file: str) -> None:
        """Voeg regionale kolommen toe (niet in FLOW-export)."""
        raw = pd.read_csv(regional_file)
        regional = regional_uit_export(raw)
        regional = regional.reindex(self.df_contour.index).fillna(0)
        for kolom in regional.columns:
            self.df_contour[kolom] = regional[kolom].astype(float)

    def _dosis_effect_series(self, mask: pd.Series) -> pd.Series:
        if "dosis_effect_relatie" in self.df_contour.columns:
            return self.df_contour.loc[mask, "dosis_effect_relatie"].astype(float)
        db = self.df_contour.index[mask].astype(float) + 0.5
        return pd.Series(0.01 * np.exp(0.08 * (db - 45)), index=self.df_contour.index[mask])

    def _contour_column_name(self, stock_name: str, jaar: int) -> str:
        """Contour-CSV-kolom voor een stock of metric."""
        base, regio = self.split_regional_stock_name(stock_name)
        if self._flow_schema:
            if regio is not None:
                col = regional_stock_kolom(base, regio)
                if jaar == self.beginjaar and col in self.df_contour.columns:
                    return col
                return f"{col}_{jaar}"
            col = self.STOCK_TO_COLUMN_PREFIX.get(base, base)
            if jaar == self.beginjaar and col in self.df_contour.columns:
                return col
            return f"{col}_{jaar}"

        if regio is None:
            return f"{stock_name}_{jaar}"
        col_prefix = self.LEGACY_STOCK_TO_COLUMN_PREFIX.get(base, base)
        return f"{col_prefix}_{regio}_{jaar}"

    def _column_prefix_map(self) -> Dict[str, str]:
        return self.STOCK_TO_COLUMN_PREFIX if self._flow_schema else self.LEGACY_STOCK_TO_COLUMN_PREFIX

    def _parse_regional_column(self, raw_column: str) -> Tuple[str, str] | None:
        if self._flow_schema:
            return None
        if not raw_column.endswith(f"_{self.beginjaar}"):
            return None
        stem = raw_column[: -(len(str(self.beginjaar)) + 1)]
        for regio in self.REGIONS:
            suffix = f"_{regio}"
            if not stem.endswith(suffix):
                continue
            col_prefix = stem[: -len(suffix)]
            if col_prefix.endswith("_totaal"):
                return None
            for base_stock, expected_prefix in self._column_prefix_map().items():
                if col_prefix == expected_prefix:
                    return f"{base_stock}_{regio}", regio
            for metric_prefix, metric_stock in self.METRIC_COLUMN_PREFIXES.items():
                if col_prefix == metric_prefix:
                    return f"{metric_stock}_{regio}", regio
        return None

    def _parse_totaal_column(self, raw_column: str) -> str | None:
        if self._flow_schema:
            if raw_column in FLOW_STOCKS:
                return raw_column
            return None
        if not raw_column.endswith(f"_{self.beginjaar}"):
            return None
        stem = raw_column[: -(len(str(self.beginjaar)) + 1)]
        if not stem.endswith("_totaal"):
            return None
        col_prefix = stem[: -len("_totaal")]
        if col_prefix in self._bases_with_regional_columns:
            return None
        for base_stock, expected_prefix in self._column_prefix_map().items():
            if col_prefix == expected_prefix:
                return base_stock
        return None

    def _register_initial_stock_columns(self) -> None:
        if self._flow_schema:
            for stock in FLOW_STOCKS:
                if stock in self.df_contour.columns:
                    self.df_contour[stock] = self.df_contour[stock].astype(float)
            if self._has_regional_layer:
                for stock_name in self.regional_stock_names():
                    col = stock_name
                    if col not in self.df_contour.columns:
                        self._pending_contour_columns[col] = pd.Series(
                            0.0, index=self.df_contour.index, dtype=float
                        )
                    else:
                        self.df_contour[col] = self.df_contour[col].astype(float)
                    self.stock_columns[stock_name] = {self.beginjaar: col}
                self._flush_pending_contour_columns()
                return
            for stock in FLOW_STOCKS:
                if stock in self.df_contour.columns:
                    self.stock_columns[stock] = {self.beginjaar: stock}
            for stock_name in self.REQUIRED_STOCKS:
                if stock_name in self.stock_columns:
                    continue
                col = self.STOCK_TO_COLUMN_PREFIX.get(stock_name, stock_name)
                if col not in self.df_contour.columns:
                    self._pending_contour_columns[col] = pd.Series(
                        0.0, index=self.df_contour.index, dtype=float
                    )
                self.stock_columns[stock_name] = {self.beginjaar: col}
            self._flush_pending_contour_columns()
            return

        for raw_column in self.df_contour.columns:
            parsed = self._parse_regional_column(raw_column)
            if not parsed:
                continue
            stem = raw_column[: -(len(str(self.beginjaar)) + 1)]
            for regio in self.REGIONS:
                if stem.endswith(f"_{regio}"):
                    self._bases_with_regional_columns.add(stem[: -len(f"_{regio}")])
                    break

        for raw_column in self.df_contour.columns:
            parsed = self._parse_regional_column(raw_column)
            if parsed:
                stock_name, _ = parsed
                self.df_contour[raw_column] = self.df_contour[raw_column].astype(float)
                self.stock_columns.setdefault(stock_name, {})[self.beginjaar] = raw_column
                continue

            stock_name = self._parse_totaal_column(raw_column)
            if stock_name:
                self.df_contour[raw_column] = self.df_contour[raw_column].astype(float)
                self.stock_columns.setdefault(stock_name, {})[self.beginjaar] = raw_column
                for regio in self.REGIONS:
                    regional_name = f"{stock_name}_{regio}"
                    if regional_name not in self.stock_columns:
                        col = self._contour_column_name(regional_name, self.beginjaar)
                        if col not in self.df_contour.columns and col not in self._pending_contour_columns:
                            self._pending_contour_columns[col] = pd.Series(
                                0.0, index=self.df_contour.index, dtype=float
                            )
                        self.stock_columns.setdefault(regional_name, {})[
                            self.beginjaar
                        ] = col

        for stock_name in self.regional_stock_names():
            if stock_name not in self.stock_columns:
                col = self._contour_column_name(stock_name, self.beginjaar)
                if col not in self.df_contour.columns and col not in self._pending_contour_columns:
                    self._pending_contour_columns[col] = pd.Series(
                        0.0, index=self.df_contour.index, dtype=float
                    )
                self.stock_columns[stock_name] = {self.beginjaar: col}

        self._flush_pending_contour_columns()

    def _flush_pending_contour_columns(self) -> None:
        if not self._pending_contour_columns:
            return
        new_columns = pd.DataFrame(self._pending_contour_columns, index=self.df_contour.index)
        self.df_contour = pd.concat([self.df_contour, new_columns], axis=1)
        self._pending_contour_columns.clear()

    def _contour_column_series(
        self, col_name: str, pending: Dict[str, pd.Series] | None = None
    ) -> pd.Series:
        if pending and col_name in pending:
            return pending[col_name]
        return self.df_contour[col_name]

    def preload_contour_year_columns(self, eindjaar: int) -> None:
        pending: Dict[str, pd.Series] = {}
        for stock_name, year_columns in list(self.stock_columns.items()):
            if not year_columns:
                continue
            start_year = min(year_columns.keys())
            for jaar in range(start_year + 1, eindjaar + 1):
                if jaar in year_columns:
                    continue
                previous_year = jaar - 1
                if previous_year not in year_columns:
                    continue
                new_col = self._contour_column_name(stock_name, jaar)
                if new_col in self.df_contour.columns or new_col in pending:
                    year_columns[jaar] = new_col
                    continue
                previous_col = year_columns[previous_year]
                try:
                    pending[new_col] = self._contour_column_series(previous_col, pending).copy()
                except KeyError:
                    continue
                year_columns[jaar] = new_col
        if pending:
            self.df_contour = pd.concat(
                [self.df_contour, pd.DataFrame(pending, index=self.df_contour.index)],
                axis=1,
            )

    def _ensure_stock_year_column(self, naam: str, jaar: int) -> str:
        if naam not in self.stock_columns:
            self.stock_columns[naam] = {}
        if jaar in self.stock_columns[naam]:
            return self.stock_columns[naam][jaar]
        if not self.stock_columns[naam]:
            raise KeyError(f"No contour backing column for stock '{naam}'")

        previous_year = max(self.stock_columns[naam].keys())
        previous_col = self.stock_columns[naam][previous_year]
        new_col = self._contour_column_name(naam, jaar)
        if new_col not in self.df_contour.columns:
            if new_col not in self._pending_contour_columns:
                self._pending_contour_columns[new_col] = self._contour_column_series(
                    previous_col, self._pending_contour_columns
                ).copy()
            self._flush_pending_contour_columns()
        self.stock_columns[naam][jaar] = new_col
        return new_col

    def _build_aggregated_stock_table(self) -> pd.DataFrame:
        rows: List[Dict[str, object]] = []
        zones = self.get_zones()
        for stock_name, year_columns in self.stock_columns.items():
            for jaar, col in year_columns.items():
                for zone in zones:
                    zone_mask = self.df_contour["zone"] == zone
                    aantal = float(self.df_contour.loc[zone_mask, col].sum())
                    rows.append(
                        {"naam": stock_name, "jaar": int(jaar), "zone": zone, "aantal": aantal}
                    )
        df_stock = pd.DataFrame(rows)
        df_stock.set_index(["naam", "jaar", "zone"], inplace=True)
        df_stock.sort_index(inplace=True)
        return df_stock

    def get_zones(self) -> Tuple[str, ...]:
        return tuple(self.df_zones["zone"].astype(str).tolist())

    def get_default_leefbaarheidspunten_weights(self) -> Dict[str, Dict[str, float]]:
        required = {"leefbaarheidspunten_geïsoleerd", "leefbaarheidspunten_niet_geïsoleerd"}
        missing = sorted(required - set(self.df_zones.columns))
        if missing:
            raise ValueError(
                "Zones-bestand mist kolommen voor leefbaarheidspunten: " + ", ".join(missing)
            )
        weights: Dict[str, Dict[str, float]] = {}
        for _, row in self.df_zones.iterrows():
            zone = str(row["zone"])
            weights[zone] = {
                "niet_geïsoleerd": float(row["leefbaarheidspunten_niet_geïsoleerd"]),
                "geïsoleerd": float(row["leefbaarheidspunten_geïsoleerd"]),
            }
        return weights

    def get_zone_contour_frame(self, zone: str, jaar: int) -> pd.DataFrame:
        """Contourwaarden per zone/jaar voor afgeleide KPI's."""
        zone_mask = self.df_contour["zone"] == zone
        empty_cols = [
            "bewoonde_niet_geïsoleerde_woning",
            "bewoonde_geïsoleerde_woning",
            "gemiddeld_aantal_inwoners_per_huis",
            "dosis_effect_relatie",
        ]
        if not zone_mask.any():
            return pd.DataFrame(columns=empty_cols)

        if self._flow_schema and self._has_regional_layer:
            col_niet_vl = self._ensure_stock_year_column(
                "bewoonde_niet_geïsoleerde_woning_vlaanderen", jaar
            )
            col_niet_br = self._ensure_stock_year_column(
                "bewoonde_niet_geïsoleerde_woning_brussel", jaar
            )
            col_iso_vl = self._ensure_stock_year_column(
                "bewoonde_geïsoleerde_woning_vlaanderen", jaar
            )
            col_iso_br = self._ensure_stock_year_column(
                "bewoonde_geïsoleerde_woning_brussel", jaar
            )
            self._flush_pending_contour_columns()
            niet_vl = self.df_contour.loc[zone_mask, col_niet_vl].astype(float)
            niet_br = self.df_contour.loc[zone_mask, col_niet_br].astype(float)
            iso_vl = self.df_contour.loc[zone_mask, col_iso_vl].astype(float)
            iso_br = self.df_contour.loc[zone_mask, col_iso_br].astype(float)
            if "gemiddeld_aantal_inwoners_per_huis" in self.df_contour.columns:
                gem_inw = self.df_contour.loc[zone_mask, "gemiddeld_aantal_inwoners_per_huis"].astype(
                    float
                )
            else:
                gem_inw = pd.Series(2.5, index=niet_vl.index)
            dosis = self._dosis_effect_series(zone_mask)
            return pd.DataFrame(
                {
                    "bewoonde_niet_geïsoleerde_woning_vlaanderen": niet_vl,
                    "bewoonde_niet_geïsoleerde_woning_brussel": niet_br,
                    "bewoonde_geïsoleerde_woning_vlaanderen": iso_vl,
                    "bewoonde_geïsoleerde_woning_brussel": iso_br,
                    "bewoonde_niet_geïsoleerde_woning": niet_vl + niet_br,
                    "bewoonde_geïsoleerde_woning": iso_vl + iso_br,
                    "gemiddeld_aantal_inwoners_per_huis": gem_inw.fillna(2.5),
                    "dosis_effect_relatie": dosis,
                }
            )

        if self._flow_schema:
            col_niet = self._ensure_stock_year_column("bewoonde_niet_geïsoleerde_woning", jaar)
            col_iso = self._ensure_stock_year_column("bewoonde_geïsoleerde_woning", jaar)
            self._flush_pending_contour_columns()
            niet = self.df_contour.loc[zone_mask, col_niet].astype(float)
            iso = self.df_contour.loc[zone_mask, col_iso].astype(float)
            woningen = niet + iso
            if "inwoners_per_contour" in self.df_contour.columns:
                inw = self.df_contour.loc[zone_mask, "inwoners_per_contour"].astype(float)
                gem_inw = inw / woningen.replace(0, np.nan)
            else:
                gem_inw = pd.Series(2.5, index=niet.index)
            dosis = self._dosis_effect_series(zone_mask)
            return pd.DataFrame(
                {
                    "bewoonde_niet_geïsoleerde_woning": niet,
                    "bewoonde_geïsoleerde_woning": iso,
                    "bewoonde_niet_geïsoleerde_woning_vlaanderen": niet,
                    "bewoonde_niet_geïsoleerde_woning_brussel": 0.0,
                    "bewoonde_geïsoleerde_woning_vlaanderen": iso,
                    "bewoonde_geïsoleerde_woning_brussel": 0.0,
                    "gemiddeld_aantal_inwoners_per_huis": gem_inw.fillna(2.5),
                    "dosis_effect_relatie": dosis,
                }
            )

        col_niet_vl = self._ensure_stock_year_column(
            "bewoonde_niet_geïsoleerde_woning_vlaanderen", jaar
        )
        col_niet_br = self._ensure_stock_year_column(
            "bewoonde_niet_geïsoleerde_woning_brussel", jaar
        )
        col_iso_vl = self._ensure_stock_year_column(
            "bewoonde_geïsoleerde_woning_vlaanderen", jaar
        )
        col_iso_br = self._ensure_stock_year_column(
            "bewoonde_geïsoleerde_woning_brussel", jaar
        )
        self._flush_pending_contour_columns()

        niet_vl = self.df_contour.loc[zone_mask, col_niet_vl].values
        niet_br = self.df_contour.loc[zone_mask, col_niet_br].values
        iso_vl = self.df_contour.loc[zone_mask, col_iso_vl].values
        iso_br = self.df_contour.loc[zone_mask, col_iso_br].values

        return pd.DataFrame(
            {
                "bewoonde_niet_geïsoleerde_woning_vlaanderen": niet_vl,
                "bewoonde_niet_geïsoleerde_woning_brussel": niet_br,
                "bewoonde_geïsoleerde_woning_vlaanderen": iso_vl,
                "bewoonde_geïsoleerde_woning_brussel": iso_br,
                "bewoonde_niet_geïsoleerde_woning": niet_vl + niet_br,
                "bewoonde_geïsoleerde_woning": iso_vl + iso_br,
                "gemiddeld_aantal_inwoners_per_huis": self.df_contour.loc[
                    zone_mask, "gemiddeld_aantal_inwoners_per_huis"
                ].values,
                "dosis_effect_relatie": self.df_contour.loc[
                    zone_mask, "dosis_effect_relatie"
                ].values,
            }
        )

    def get_aantal(self, naam: str, jaar: int, zone: str) -> float:
        if (naam, jaar, zone) not in self.df_stock.index:
            return 0.0
        return float(self.df_stock.loc[(naam, jaar, zone), "aantal"])

    def set_aantal(self, naam: str, jaar: int, zone: str, aantal: float) -> None:
        if naam not in self.stock_columns or not self.stock_columns[naam]:
            self.df_stock.loc[(naam, jaar, zone), "aantal"] = float(aantal)
            self.df_stock.sort_index(inplace=True)
            return

        col = self._ensure_stock_year_column(naam, jaar)
        zone_mask = self.df_contour["zone"] == zone
        if not zone_mask.any():
            self.df_stock.loc[(naam, jaar, zone), "aantal"] = float(aantal)
            self.df_stock.sort_index(inplace=True)
            return

        current_zone_total = float(self.df_contour.loc[zone_mask, col].sum())
        target_total = float(aantal)
        if current_zone_total <= 0:
            share = target_total / float(zone_mask.sum())
            self.df_contour.loc[zone_mask, col] = share
        else:
            factor = target_total / current_zone_total
            self.df_contour.loc[zone_mask, col] = self.df_contour.loc[zone_mask, col] * factor

        self.df_stock.loc[(naam, jaar, zone), "aantal"] = float(
            self.df_contour.loc[zone_mask, col].sum()
        )
        self.df_stock.sort_index(inplace=True)

    def save(self, output_file: str) -> None:
        df_to_save = self.df_stock.reset_index()
        df_to_save.to_csv(output_file, sep=";", index=False)

    def get_dataframe(self) -> pd.DataFrame:
        return self.df_stock.copy()
