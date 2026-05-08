"""Flow manager for handling flow data and measure selections."""

import pandas as pd
from typing import Tuple, Iterable


def _parse_percentage(value) -> float:
    """'102,00%' -> 1.02 (factor)."""
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace("%", "").replace(",", ".")
    if not s:
        return 0.0
    return float(s) / 100.0


def _parse_decimal(value) -> float:
    """'1,05' -> 1.05."""
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", ".")
    if not s or s == "-":
        return 0.0
    return float(s)


class FlowRow:
    """Kleine helperklasse die één flow-rij representeert."""

    def __init__(self, row: pd.Series, df_all: pd.DataFrame):
        self._row = row
        self._df_all = df_all

    def get_name_measure(self) -> str:
        """Logische naam van de maatregel voor deze rij."""
        return str(self._row["naam"])

    def is_applied(self) -> bool:
        """Of de maatregel in deze rij effectief wordt toegepast."""
        return bool(self._row["maatregel_toepassen"])

    def get_zone(self) -> str:
        return str(self._row["zone"])

    def get_inflow_stock_name(self) -> str:
        return str(self._row["inflow_stock"])

    def get_outflow_stock_name(self) -> str:
        return str(self._row["outflow_stock"])

    def get_flow(self) -> tuple[float, float]:
        """
        Effectieve inflow- en outflow-factoren (0..n) voor deze rij.

        - Standaard: flow_met_maatregel als maatregel_toepassen True, anders flow_zonder_maatregel.
        - renovatie_zonder_maatregel: altijd actief met flow_met_maatregel,
          behalve als één van de drie andere renovatiemaatregelen actief is; dan 0.
        """
        naam = str(self._row["naam"])
        zone = str(self._row["zone"])

        # Specifieke logica voor renovatie_zonder_maatregel:
        # deze valt weg (0,0) als een van de andere renovatieprogramma's actief is.
        if naam == "renovatie_zonder_maatregel":
            mask_programs = (
                self._df_all["zone"].astype(str).eq(zone)
                & self._df_all["naam"].isin(
                    [
                        "verplicht_isoleren_renovatie",
                        "gesubsidieerd_isolatieprogramma",
                        "gestuurd_isolatieprogramma",
                    ]
                )
            )
            if self._df_all.loc[mask_programs, "maatregel_toepassen"].any():
                return (0.0, 0.0)
            inflow_col = "inflow_met_maatregel"
            outflow_col = "outflow_met_maatregel"
        else:
            if bool(self._row["maatregel_toepassen"]):
                inflow_col = "inflow_met_maatregel"
                outflow_col = "outflow_met_maatregel"
            else:
                inflow_col = "inflow_zonder_maatregel"
                outflow_col = "outflow_zonder_maatregel"

        return float(self._row[inflow_col]), float(self._row[outflow_col])

    def get_relative_cost_overheid(self) -> float:
        return float(self._row["relatieve_kost_overheid"])

    def get_relative_cost_prive(self) -> float:
        return float(self._row["relatieve_kost_privé"])

    def get_kost_stock(self) -> str:
        return str(self._row["kost_stock"]).strip()


class FlowManager:
    """Manages flow data and measure applications voor het nieuwe flow-formaat."""

    def __init__(self, flow_file: str, beschrijving_file: str):
        # 20260302_flows.csv: ';'-gescheiden, met inflow/outflow + vier flow-kolommen.
        df_flow = pd.read_csv(flow_file, sep=";")
        for col in [
            "inflow_zonder_maatregel",
            "outflow_zonder_maatregel",
            "inflow_met_maatregel",
            "outflow_met_maatregel",
        ]:
            df_flow[col] = df_flow[col].map(_parse_percentage)
        for col in ["maatregel_kost", "relatieve_kost_overheid", "relatieve_kost_privé"]:
            if col in df_flow.columns:
                df_flow[col] = df_flow[col].map(_parse_decimal)
        df_flow["maatregel_toepassen"] = (
            df_flow["maatregel_toepassen"].astype(str).str.upper() == "TRUE"
        )
        self.df_flow = df_flow

        # Beschrijvingen per logische maatregel (zonder zone)
        self.df_beschrijving_maatregelen = pd.read_csv(beschrijving_file).set_index(
            ["naam"], verify_integrity=True
        )
        self._validate_measure_definitions()

    def _validate_measure_definitions(self) -> None:
        """
        Validate that measure names in flows and descriptions are identical.

        Raises:
            ValueError: when one of both files contains missing/extra names.
        """
        flow_names = set(self.df_flow["naam"].astype(str).unique().tolist())
        description_names = set(
            self.df_beschrijving_maatregelen.index.astype(str).tolist()
        )

        missing_in_descriptions = sorted(flow_names - description_names)
        missing_in_flows = sorted(description_names - flow_names)

        if missing_in_descriptions or missing_in_flows:
            parts = []
            if missing_in_descriptions:
                parts.append(
                    "Ontbreekt in beschrijving_maatregelen.csv: "
                    + ", ".join(missing_in_descriptions)
                )
            if missing_in_flows:
                parts.append(
                    "Ontbreekt in flows.csv: " + ", ".join(missing_in_flows)
                )
            raise ValueError("Maatregel-definities inconsistent. " + " | ".join(parts))

    def _mask_for_measure(self, maatregel_naam: str) -> pd.Series:
        """Exacte matching van één maatregel op flow-rijen."""
        return self.df_flow["naam"] == maatregel_naam

    # ---- API voor SimulationEngine ----

    def get_flows(self, zone: str) -> Iterable[FlowRow]:
        """Geef alle flow-rijen terug als FlowRow-objecten voor één zone."""
        zone = str(zone)
        for _, row in self.df_flow.iterrows():
            if str(row["zone"]) == zone:
                yield FlowRow(row, self.df_flow)

    # ---- API voor tests en UI ----

    def get_flow(self, naam: str, zone: str) -> tuple[float, float]:
        """Geaggregeerde inflow- en outflow-factor voor (maatregel, zone)."""
        mask = self._mask_for_measure(naam) & (self.df_flow["zone"] == zone)
        subset = self.df_flow[mask]
        if subset.empty:
            raise KeyError(f"Geen flow gevonden voor maatregel {naam} in zone {zone}")

        if naam == "renovatie_zonder_maatregel":
            # Gebruik dezelfde logica als FlowRow.get_flow voor deze rij.
            row = subset.iloc[0]
            return FlowRow(row, self.df_flow).get_flow()

        if subset["maatregel_toepassen"].any():
            return (
                float(
                    subset.loc[subset["maatregel_toepassen"], "inflow_met_maatregel"].sum()
                ),
                float(
                    subset.loc[subset["maatregel_toepassen"], "outflow_met_maatregel"].sum()
                ),
            )

        return (
            float(subset["inflow_zonder_maatregel"].sum()),
            float(subset["outflow_zonder_maatregel"].sum()),
        )

    def get_selected_zones(self, maatregel_naam: str) -> Tuple[str, ...]:
        subset = self.df_flow[self._mask_for_measure(maatregel_naam)]
        zones = subset.loc[subset["maatregel_toepassen"], "zone"].unique().tolist()
        return tuple(zones)

    def set_selected_zones(
        self, maatregel_naam: str, selected_zones: Tuple[str, ...]
    ) -> None:
        mask = self._mask_for_measure(maatregel_naam)
        self.df_flow.loc[mask, "maatregel_toepassen"] = self.df_flow.loc[
            mask, "zone"
        ].isin(selected_zones)

    def get_total_cost(self) -> float:
        return float(
            self.df_flow.loc[self.df_flow["maatregel_toepassen"], "maatregel_kost"].sum()
        )

    def get_measure_descriptions(self) -> pd.DataFrame:
        return self.df_beschrijving_maatregelen.copy()

    def is_measure_applied(self, naam: str, zone: str) -> bool:
        mask = self._mask_for_measure(naam) & (self.df_flow["zone"] == zone)
        subset = self.df_flow[mask]
        if subset.empty:
            return False
        return bool(subset["maatregel_toepassen"].any())
