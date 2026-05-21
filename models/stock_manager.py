"""Stock manager for handling stock data operations."""

import pandas as pd
from typing import Dict, List, Tuple

from config import OUTPUT_STOCK_FILE


class StockManager:
    """Manages stock data with operations for getting and setting values."""

    REGIONS: Tuple[str, ...] = ("vlaanderen", "brussel")

    STOCK_TO_COLUMN_PREFIX = {
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

    # Afgeleide contour-metrics (geen simulatiestock, wel per regio opgeslagen)
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
        """Alle simulatiestocks: {basisstock}_{vlaanderen|brussel}."""
        return tuple(
            f"{stock}_{regio}" for stock in cls.REQUIRED_STOCKS for regio in cls.REGIONS
        )

    @classmethod
    def split_regional_stock_name(cls, stock_name: str) -> Tuple[str, str | None]:
        """Splits 'bewoonde_geïsoleerde_woning_vlaanderen' -> (basis, 'vlaanderen')."""
        for regio in cls.REGIONS:
            suffix = f"_{regio}"
            if stock_name.endswith(suffix):
                return stock_name[: -len(suffix)], regio
        return stock_name, None

    def __init__(self, contour_file: str, zones_file: str, beginjaar: int):
        self.beginjaar = beginjaar
        self.df_zones = pd.read_csv(zones_file)
        self.df_zones = self.df_zones.dropna(subset=["zone"]).reset_index(drop=True)
        self.df_zones = self.df_zones.sort_values("min dBel", ascending=False).reset_index(
            drop=True
        )

        self.df_contour = pd.read_csv(contour_file)
        if "Unnamed: 0" in self.df_contour.columns:
            self.df_contour = self.df_contour.drop(columns=["Unnamed: 0"])
        if "" in self.df_contour.columns:
            self.df_contour = self.df_contour.drop(columns=[""])

        midden_col = "db_midden" if "db_midden" in self.df_contour.columns else "midden"
        self.df_contour["zone"] = self.df_contour[midden_col].map(self._map_midden_to_zone)
        self.stock_columns: Dict[str, Dict[int, str]] = {}
        self._bases_with_regional_columns: set[str] = set()
        self._register_initial_stock_columns()
        self.df_stock = self._build_aggregated_stock_table()

    def _map_midden_to_zone(self, midden: float) -> str:
        for _, zone_row in self.df_zones.iterrows():
            if zone_row["min dBel"] <= midden < zone_row["max dBel"]:
                return str(zone_row["zone"])
        return "Onbekend"

    def _contour_column_name(self, stock_name: str, jaar: int) -> str:
        """Contour-CSV-kolom voor een regionale stock of metric."""
        base, regio = self.split_regional_stock_name(stock_name)
        if regio is None:
            return f"{stock_name}_{jaar}"
        col_prefix = self.STOCK_TO_COLUMN_PREFIX.get(base, base)
        return f"{col_prefix}_{regio}_{jaar}"

    def _parse_regional_column(self, raw_column: str) -> Tuple[str, str] | None:
        """Map contourkolom naar (stock_name, regio) of None."""
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
            for base_stock, expected_prefix in self.STOCK_TO_COLUMN_PREFIX.items():
                if col_prefix == expected_prefix:
                    return f"{base_stock}_{regio}", regio
            for metric_prefix, metric_stock in self.METRIC_COLUMN_PREFIXES.items():
                if col_prefix == metric_prefix:
                    return f"{metric_stock}_{regio}", regio
        return None

    def _parse_totaal_column(self, raw_column: str) -> str | None:
        if not raw_column.endswith(f"_{self.beginjaar}"):
            return None
        stem = raw_column[: -(len(str(self.beginjaar)) + 1)]
        if not stem.endswith("_totaal"):
            return None
        col_prefix = stem[: -len("_totaal")]
        if col_prefix in self._bases_with_regional_columns:
            return None
        for base_stock, expected_prefix in self.STOCK_TO_COLUMN_PREFIX.items():
            if col_prefix == expected_prefix:
                return base_stock
        return None

    def _register_initial_stock_columns(self) -> None:
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
                for regio in self.REGIONS:
                    regional_name = f"{stock_name}_{regio}"
                    if regional_name not in self.stock_columns:
                        col = self._contour_column_name(regional_name, self.beginjaar)
                        if col not in self.df_contour.columns:
                            self.df_contour[col] = 0.0
                        self.df_contour[col] = self.df_contour[col].astype(float)
                        self.stock_columns.setdefault(regional_name, {})[
                            self.beginjaar
                        ] = col

        for stock_name in self.regional_stock_names():
            if stock_name not in self.stock_columns:
                col = self._contour_column_name(stock_name, self.beginjaar)
                self.df_contour[col] = 0.0
                self.stock_columns[stock_name] = {self.beginjaar: col}

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
        self.df_contour[new_col] = self.df_contour[previous_col]
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
        """Contourwaarden per zone/jaar, incl. regionale bewoonde woningstocks."""
        zone_mask = self.df_contour["zone"] == zone
        empty_cols = [
            "bewoonde_niet_geïsoleerde_woning",
            "bewoonde_geïsoleerde_woning",
            "bewoonde_niet_geïsoleerde_woning_vlaanderen",
            "bewoonde_niet_geïsoleerde_woning_brussel",
            "bewoonde_geïsoleerde_woning_vlaanderen",
            "bewoonde_geïsoleerde_woning_brussel",
            "gemiddeld_aantal_inwoners_per_huis",
            "dosis_effect_relatie",
        ]
        if not zone_mask.any():
            return pd.DataFrame(columns=empty_cols)

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
