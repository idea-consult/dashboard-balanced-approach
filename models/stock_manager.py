"""Stock manager for handling stock data operations."""

import pandas as pd
from typing import Dict, List, Tuple
from config import OUTPUT_STOCK_FILE


class StockManager:
    """Manages stock data with operations for getting and setting values."""

    STOCK_COLUMN_MAP = {
        "aantal_bewoonde_geïsoleerde_huizen": "bewoonde_geïsoleerde_woning",
        "aantal_bewoonde_niet_geïsoleerde_huizen": "bewoonde_niet_geïsoleerde_woning",
        "aantal_onbebouwde_bebouwbare_percelen": "onbebouwde_bebouwbare_percelen",
        "aantal_perceel_eigendom_overheid": "perceel_eigendom_overheid",
        "woning_eigendom_overheid": "woning_eigendom_overheid",
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

    def __init__(self, contour_file: str, zones_file: str, beginjaar: int):
        """
        Initialize the stock manager.

        Args:
            contour_file: Path to contour stock CSV file
            zones_file: Path to zones CSV file
            beginjaar: Initial model year
        """
        self.beginjaar = beginjaar
        self.df_zones = pd.read_csv(zones_file)
        self.df_zones = self.df_zones.dropna(subset=["zone"]).reset_index(drop=True)
        self.df_zones = self.df_zones.sort_values("min dBel", ascending=False).reset_index(drop=True)

        self.df_contour = pd.read_csv(contour_file)
        if "Unnamed: 0" in self.df_contour.columns:
            self.df_contour = self.df_contour.drop(columns=["Unnamed: 0"])
        if "" in self.df_contour.columns:
            self.df_contour = self.df_contour.drop(columns=[""])

        self.df_contour["zone"] = self.df_contour["midden"].map(self._map_midden_to_zone)
        self.stock_columns: Dict[str, Dict[int, str]] = {}
        self._register_initial_stock_columns()
        self.df_stock = self._build_aggregated_stock_table()

    def _map_midden_to_zone(self, midden: float) -> str:
        for _, zone_row in self.df_zones.iterrows():
            if zone_row["min dBel"] <= midden < zone_row["max dBel"]:
                return str(zone_row["zone"])
        return "Onbekend"

    def _register_initial_stock_columns(self) -> None:
        for raw_column in self.df_contour.columns:
            if not raw_column.endswith(f"_{self.beginjaar}"):
                continue
            base_name = raw_column[: -(len(str(self.beginjaar)) + 1)]
            stock_name = self.STOCK_COLUMN_MAP.get(base_name, base_name)
            # Stockkolommen moeten float ondersteunen voor fracties tijdens simulatie.
            self.df_contour[raw_column] = self.df_contour[raw_column].astype(float)
            self.stock_columns.setdefault(stock_name, {})[self.beginjaar] = raw_column

        # Kolom zonder jaarsuffix
        if "woning_eigendom_overheid" in self.df_contour.columns:
            self.df_contour["woning_eigendom_overheid"] = self.df_contour[
                "woning_eigendom_overheid"
            ].astype(float)
            self.stock_columns.setdefault("woning_eigendom_overheid", {})[self.beginjaar] = "woning_eigendom_overheid"

        for stock_name in self.REQUIRED_STOCKS:
            if stock_name not in self.stock_columns:
                col = f"{stock_name}_{self.beginjaar}"
                self.df_contour[col] = 0.0
                self.stock_columns[stock_name] = {self.beginjaar: col}

    def _ensure_stock_year_column(self, naam: str, jaar: int) -> str:
        if naam not in self.stock_columns:
            self.stock_columns[naam] = {}
        if jaar in self.stock_columns[naam]:
            return self.stock_columns[naam][jaar]
        if not self.stock_columns[naam]:
            # Afgeleide metrics (zoals hinder/personen) hebben geen
            # contourniveau-bronkolom en worden enkel geaggregeerd bewaard.
            raise KeyError(f"No contour backing column for stock '{naam}'")

        previous_year = max(self.stock_columns[naam].keys())
        previous_col = self.stock_columns[naam][previous_year]
        new_col = f"{naam}_{jaar}"
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
                    rows.append({"naam": stock_name, "jaar": int(jaar), "zone": zone, "aantal": aantal})
        df_stock = pd.DataFrame(rows)
        df_stock.set_index(["naam", "jaar", "zone"], inplace=True)
        df_stock.sort_index(inplace=True)
        return df_stock

    def get_zones(self) -> Tuple[str, ...]:
        return tuple(self.df_zones["zone"].astype(str).tolist())

    def get_default_leefbaarheidspunten_weights(self) -> Dict[str, Dict[str, float]]:
        """Default leefbaarheidspunten per inwoner per zone uit zones-CSV."""
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
        """Return contour-level values for a zone and year."""
        zone_mask = self.df_contour["zone"] == zone
        if not zone_mask.any():
            return pd.DataFrame(
                columns=[
                    "bewoonde_niet_geïsoleerde_woning",
                    "bewoonde_geïsoleerde_woning",
                    "gemiddeld_aantal_inwoners_per_huis",
                    "dosis_effect_relatie",
                ]
            )

        col_niet_iso = self._ensure_stock_year_column("bewoonde_niet_geïsoleerde_woning", jaar)
        col_iso = self._ensure_stock_year_column("bewoonde_geïsoleerde_woning", jaar)

        return pd.DataFrame(
            {
                "bewoonde_niet_geïsoleerde_woning": self.df_contour.loc[zone_mask, col_niet_iso].values,
                "bewoonde_geïsoleerde_woning": self.df_contour.loc[zone_mask, col_iso].values,
                "gemiddeld_aantal_inwoners_per_huis": self.df_contour.loc[
                    zone_mask, "gemiddeld_aantal_inwoners_per_huis"
                ].values,
                "dosis_effect_relatie": self.df_contour.loc[zone_mask, "dosis_effect_relatie"].values,
            }
        )

    def get_aantal(self, naam: str, jaar: int, zone: str) -> float:
        """
        Get the value of a stock for a specific name, year, and zone.

        Args:
            naam: Stock name
            jaar: Year
            zone: Zone identifier

        Returns:
            The stock value
        """
        if (naam, jaar, zone) not in self.df_stock.index:
            return 0.0
        return float(self.df_stock.loc[(naam, jaar, zone), "aantal"])

    def set_aantal(self, naam: str, jaar: int, zone: str, aantal: float) -> None:
        """
        Set the value of a stock for a specific name, year, and zone.

        Args:
            naam: Stock name
            jaar: Year
            zone: Zone identifier
            aantal: Value to set
        """
        if naam not in self.stock_columns or not self.stock_columns[naam]:
            # Metrics zonder contourbacking alleen in geaggregeerde tabel opslaan.
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
        """
        Save the stock data to a CSV file.

        Args:
            output_file: Path to save the CSV file
        """
        df_to_save = self.df_stock.reset_index()
        df_to_save.to_csv(output_file, sep=";", index=False)

    def get_dataframe(self) -> pd.DataFrame:
        """
        Get the underlying DataFrame.

        Returns:
            The stock DataFrame
        """
        return self.df_stock.copy()
