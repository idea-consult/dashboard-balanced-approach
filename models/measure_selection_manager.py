"""UI-focused measure selection manager."""

from typing import Literal, Tuple
import os
import pandas as pd

from models.lden_data_loader import OVERLAY_IDS

SidebarEntry = tuple[Literal["group", "measure"], str]

# Visuele secties in de sidebar: --- rondom + geprefixte maatregel-labels.
SIDEBAR_SECTIONS: tuple[dict[str, object], ...] = (
    {
        "label": "Aankopen percelen",
        "members": (
            ("measure", "aankoopbeleid_percelen"),
            ("measure", "voorkooprecht_percelen"),
            ("measure", "onteigening_percelen"),
        ),
        "short_labels": {
            "aankoopbeleid_percelen": "Aankopen percelen: aankoopbeleid",
            "voorkooprecht_percelen": "Aankopen percelen: voorkooprecht",
            "onteigening_percelen": "Aankopen percelen: onteigenen",
        },
    },
    {
        "label": "Aankopen woningen",
        "members": (
            ("group", "aankoopbeleid_woningen"),
            ("group", "voorkooprecht_woningen"),
            ("group", "onteigenen_woningen"),
        ),
        "short_labels": {
            "aankoopbeleid_woningen": "Aankopen woningen: aankoopbeleid",
            "voorkooprecht_woningen": "Aankopen woningen: voorkooprecht",
            "onteigenen_woningen": "Aankopen woningen: onteigenen",
        },
    },
)


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

        if "priority" in measures_df.columns:
            measures_df["priority"] = pd.to_numeric(measures_df["priority"], errors="coerce")
            measures_df = measures_df.sort_values("priority", kind="stable")

        self.df_measures = measures_df.rename(columns={"measure_id": "naam"})
        if "help" not in self.df_measures.columns:
            self.df_measures["help"] = ""
        if "naam_mooi" not in self.df_measures.columns:
            self.df_measures["naam_mooi"] = self.df_measures["naam"]
        self.df_measures = self.df_measures.set_index(["naam"], verify_integrity=True)

        flow_rules_df = flow_rules_df.copy()
        if "priority" in flow_rules_df.columns:
            flow_rules_df["priority"] = pd.to_numeric(
                flow_rules_df["priority"], errors="coerce"
            )
        self.df_flow_rules = flow_rules_df

        self.df_selection = (
            self.df_measures.reset_index()[["naam"]]
            .assign(_k=1)
            .merge(pd.DataFrame({"zone": list(zones), "_k": 1}), on="_k", how="inner")
            .drop(columns=["_k"])
            .assign(maatregel_toepassen=False)
        )
        self._overlay_by_measure: dict[str, str | None] = {
            str(name): None for name in self.df_measures.index
        }

    def _validate_normalized_inputs(
        self,
        measures_df: pd.DataFrame,
        flow_rules_df: pd.DataFrame,
        costs_df: pd.DataFrame,
    ) -> None:
        required_measures = {"measure_id", "naam_mooi", "help", "priority"}
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
        zone_series = df_zones["zone"].dropna().astype(str).str.strip()
        zones = sorted(zone_series[zone_series != ""].unique().tolist())
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
        if selected_zones:
            self._overlay_by_measure[str(maatregel_naam)] = None

    def get_selected_overlay(self, maatregel_naam: str) -> str | None:
        return self._overlay_by_measure.get(str(maatregel_naam))

    def set_selected_overlay(
        self, maatregel_naam: str, overlay_id: str | None
    ) -> None:
        key = str(maatregel_naam)
        if overlay_id is None:
            self._overlay_by_measure[key] = None
            return
        if overlay_id not in OVERLAY_IDS:
            raise ValueError(f"Onbekende overlay: {overlay_id}")
        self._overlay_by_measure[key] = overlay_id
        # Overlay en A–F zijn wederzijds uitsluitend.
        mask = self._mask_for_measure(maatregel_naam)
        self.df_selection.loc[mask, "maatregel_toepassen"] = False

    def get_measure_descriptions(self) -> pd.DataFrame:
        return self.df_measures.copy()

    def get_flow_rules_for_measure(self, measure_id: str) -> pd.DataFrame:
        return self.df_flow_rules[
            self.df_flow_rules["measure_id"].astype(str) == str(measure_id)
        ]

    def is_measure_applied(self, naam: str, zone: str) -> bool:
        if self.get_selected_overlay(naam) is not None:
            return False
        mask = self._mask_for_measure(naam) & (self.df_selection["zone"] == zone)
        subset = self.df_selection[mask]
        if subset.empty:
            return False
        return bool(subset["maatregel_toepassen"].any())

    def is_measure_applied_on_overlay(self, naam: str, overlay_id: str) -> bool:
        return self.get_selected_overlay(naam) == overlay_id

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
            group_id: tuple(measures)
            for group_id, measures in groups.items()
            if len(measures) > 1
        }

    def get_ui_sidebar_entries(self) -> list[SidebarEntry]:
        """Sidebar-volgorde = rijvolgorde in measures.csv (kolom priority)."""
        hidden = self.get_hidden_measures()
        measure_to_group = {
            measure: group_id
            for group_id, members in self.get_measure_groups().items()
            for measure in members
        }
        seen_groups: set[str] = set()
        entries: list[SidebarEntry] = []

        for measure_id in self.df_measures.index.astype(str):
            if measure_id in hidden:
                continue
            group_id = measure_to_group.get(measure_id)
            if group_id is not None:
                if group_id not in seen_groups:
                    seen_groups.add(group_id)
                    entries.append(("group", group_id))
                continue
            entries.append(("measure", measure_id))

        return entries

    def get_sidebar_section_starts(self) -> dict[SidebarEntry, str]:
        """Map eerste zichtbare entry van een sectie → sectietitel."""
        entries = set(self.get_ui_sidebar_entries())
        starts: dict[SidebarEntry, str] = {}
        for section in SIDEBAR_SECTIONS:
            members: tuple[SidebarEntry, ...] = section["members"]  # type: ignore[assignment]
            for member in members:
                if member in entries:
                    starts[member] = str(section["label"])
                    break
        return starts

    def get_sidebar_section_ends(self) -> set[SidebarEntry]:
        """Laatste zichtbare entry van elke sectie (voor --- erna)."""
        entries = set(self.get_ui_sidebar_entries())
        ends: set[SidebarEntry] = set()
        for section in SIDEBAR_SECTIONS:
            members: tuple[SidebarEntry, ...] = section["members"]  # type: ignore[assignment]
            last_visible: SidebarEntry | None = None
            for member in members:
                if member in entries:
                    last_visible = member
            if last_visible is not None:
                ends.add(last_visible)
        return ends

    def get_sidebar_short_label(self, entry_kind: str, entry_key: str) -> str | None:
        """Geprefixte label binnen een sidebar-sectie, of None."""
        entry: SidebarEntry = (entry_kind, entry_key)  # type: ignore[assignment]
        for section in SIDEBAR_SECTIONS:
            members: tuple[SidebarEntry, ...] = section["members"]  # type: ignore[assignment]
            if entry not in members:
                continue
            short_labels: dict[str, str] = section["short_labels"]  # type: ignore[assignment]
            return short_labels.get(entry_key)
        return None
