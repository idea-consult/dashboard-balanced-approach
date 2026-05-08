"""UI-focused measure selection manager."""

from typing import Tuple
import os
import pandas as pd


class MeasureSelectionManager:
    """Manages measure metadata and per-zone UI activation state."""

    def __init__(
        self,
        zones_file: str,
        measures_file: str,
        flow_rules_file: str,
        measure_costs_file: str,
    ):
        zones = self._load_zones_from_file(zones_file)
        measures_df = pd.read_csv(measures_file)
        flow_rules_df = pd.read_csv(flow_rules_file)
        costs_df = pd.read_csv(measure_costs_file)

        self._validate_normalized_inputs(
            measures_df=measures_df,
            flow_rules_df=flow_rules_df,
            costs_df=costs_df,
        )

        self.df_measures = measures_df.rename(columns={"measure_id": "naam"})
        if "help" not in self.df_measures.columns:
            self.df_measures["help"] = ""
        if "naam_mooi" not in self.df_measures.columns:
            self.df_measures["naam_mooi"] = self.df_measures["naam"]
        self.df_measures = self.df_measures.set_index(["naam"], verify_integrity=True)

        self.df_selection = (
            self.df_measures.reset_index()[["naam"]]
            .assign(_k=1)
            .merge(pd.DataFrame({"zone": list(zones), "_k": 1}), on="_k", how="inner")
            .drop(columns=["_k"])
            .assign(maatregel_toepassen=False)
        )

    def _validate_normalized_inputs(
        self,
        measures_df: pd.DataFrame,
        flow_rules_df: pd.DataFrame,
        costs_df: pd.DataFrame,
    ) -> None:
        required_measures = {"measure_id", "naam_mooi", "help"}
        required_rules = {
            "rule_id",
            "measure_id",
            "inflow_stock",
            "outflow_stock",
            "flow_rate_baseline",
            "flow_rate_active",
            "flow_mode",
        }
        required_costs = {
            "measure_id",
            "rel_cost_overheid",
            "rel_cost_prive",
            "kost_stock",
        }

        for name, df, required in [
            ("measures.csv", measures_df, required_measures),
            ("flow_rules.csv", flow_rules_df, required_rules),
            ("measure_costs.csv", costs_df, required_costs),
        ]:
            missing = sorted(required - set(df.columns))
            if missing:
                raise ValueError(f"{name} mist kolommen: {', '.join(missing)}")

        if measures_df["measure_id"].duplicated().any():
            raise ValueError("measures.csv bevat dubbele measure_id waarden.")
        if flow_rules_df["rule_id"].duplicated().any():
            raise ValueError("flow_rules.csv bevat dubbele rule_id waarden.")

        measure_ids = set(measures_df["measure_id"].astype(str))
        for name, df in [
            ("flow_rules.csv", flow_rules_df),
            ("measure_costs.csv", costs_df),
        ]:
            unknown = sorted(set(df["measure_id"].astype(str)) - measure_ids)
            if unknown:
                raise ValueError(
                    f"{name} bevat measure_id die niet in measures.csv staan: {', '.join(unknown)}"
                )

    def _load_zones_from_file(self, zones_file: str) -> Tuple[str, ...]:
        if not os.path.exists(zones_file):
            raise ValueError(f"Zones-bestand niet gevonden: {zones_file}")
        try:
            df_zones = pd.read_csv(zones_file, usecols=["zone"])
        except Exception as exc:
            raise ValueError(
                f"Kon zones niet lezen uit {zones_file}. Verwacht kolom 'zone'."
            ) from exc
        zones = sorted(df_zones["zone"].astype(str).unique().tolist())
        if not zones:
            raise ValueError(f"Zones-bestand {zones_file} bevat geen zones.")
        return tuple(zones)

    def _mask_for_measure(self, maatregel_naam: str) -> pd.Series:
        return self.df_selection["naam"] == maatregel_naam

    def get_selected_zones(self, maatregel_naam: str) -> Tuple[str, ...]:
        subset = self.df_selection[self._mask_for_measure(maatregel_naam)]
        zones = subset.loc[subset["maatregel_toepassen"], "zone"].unique().tolist()
        return tuple(zones)

    def set_selected_zones(
        self, maatregel_naam: str, selected_zones: Tuple[str, ...]
    ) -> None:
        mask = self._mask_for_measure(maatregel_naam)
        self.df_selection.loc[mask, "maatregel_toepassen"] = self.df_selection.loc[
            mask, "zone"
        ].isin(selected_zones)

    def get_measure_descriptions(self) -> pd.DataFrame:
        return self.df_measures.copy()

    def is_measure_applied(self, naam: str, zone: str) -> bool:
        mask = self._mask_for_measure(naam) & (self.df_selection["zone"] == zone)
        subset = self.df_selection[mask]
        if subset.empty:
            return False
        return bool(subset["maatregel_toepassen"].any())

    def get_hidden_measures(self) -> set[str]:
        if "hidden_in_ui" not in self.df_measures.columns:
            return set()
        hidden_mask = (
            self.df_measures["hidden_in_ui"].astype(str).str.upper().eq("TRUE")
        )
        return set(self.df_measures.index[hidden_mask].astype(str).tolist())

    def get_measure_groups(self) -> dict[str, tuple[str, ...]]:
        if "group_id" not in self.df_measures.columns:
            return {}
        groups: dict[str, list[str]] = {}
        for measure_name, row in self.df_measures.iterrows():
            raw_group_id = row.get("group_id", "")
            if pd.isna(raw_group_id):
                continue
            group_id = str(raw_group_id).strip()
            if not group_id:
                continue
            groups.setdefault(group_id, []).append(str(measure_name))
        return {
            group_id: tuple(sorted(measures))
            for group_id, measures in groups.items()
            if len(measures) > 1
        }
