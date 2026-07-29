"""Load and validate scenario presets from CSV."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import pandas as pd

from models.lden_data_loader import OVERLAY_IDS

NONE_SCENARIO_ID = ""
NONE_SCENARIO_LABEL = "Geen"


@dataclass(frozen=True)
class MeasureSelection:
    """Zones A–F and/or one overlay for a single measure."""

    zones: Tuple[str, ...]
    overlay: str | None


@dataclass(frozen=True)
class ScenarioInfo:
    scenario_id: str
    label: str
    priority: int


class ScenarioManager:
    """CSV-driven presets: one scenario selects zones/overlays per measure."""

    def __init__(self, scenarios_file: str, known_measure_ids: set[str] | None = None):
        self._scenarios_file = scenarios_file
        self._known_measure_ids = known_measure_ids
        self._scenarios: list[ScenarioInfo] = []
        self._selections: Dict[str, Dict[str, MeasureSelection]] = {}
        self._load()

    def _load(self) -> None:
        df = pd.read_csv(self._scenarios_file)
        required = {
            "scenario_id",
            "scenario_label",
            "priority",
            "measure_id",
            "zones",
            "overlay",
        }
        missing = sorted(required - set(df.columns))
        if missing:
            raise ValueError(
                f"scenarios.csv mist kolommen: {', '.join(missing)}"
            )

        df = df.copy()
        for col in ("scenario_id", "scenario_label", "measure_id", "zones", "overlay"):
            df[col] = df[col].fillna("").astype(str).str.strip()
        df["priority"] = pd.to_numeric(df["priority"], errors="coerce").fillna(100).astype(int)

        scenario_meta: dict[str, ScenarioInfo] = {}
        selections: Dict[str, Dict[str, MeasureSelection]] = {}

        for _, row in df.iterrows():
            sid = str(row["scenario_id"]).strip()
            if not sid:
                continue
            label = str(row["scenario_label"]).strip() or sid
            priority = int(row["priority"])
            if sid not in scenario_meta:
                scenario_meta[sid] = ScenarioInfo(
                    scenario_id=sid, label=label, priority=priority
                )
            elif scenario_meta[sid].label != label:
                # Keep first label; priority stays min
                pass
            if priority < scenario_meta[sid].priority:
                scenario_meta[sid] = ScenarioInfo(
                    scenario_id=sid, label=scenario_meta[sid].label, priority=priority
                )

            measure_id = str(row["measure_id"]).strip()
            if not measure_id:
                continue

            if self._known_measure_ids is not None and measure_id not in self._known_measure_ids:
                raise ValueError(
                    f"scenarios.csv: onbekende measure_id '{measure_id}' "
                    f"(scenario '{sid}')"
                )

            zones_raw = str(row["zones"]).strip()
            overlay_raw = str(row["overlay"]).strip().lower()
            zones = tuple(
                z.strip()
                for z in zones_raw.replace(",", ";").split(";")
                if z.strip()
            )
            overlay: str | None = overlay_raw if overlay_raw else None
            if overlay is not None and overlay not in OVERLAY_IDS:
                raise ValueError(
                    f"scenarios.csv: ongeldige overlay '{overlay_raw}' "
                    f"(scenario '{sid}', measure '{measure_id}')"
                )
            if zones and overlay is not None:
                raise ValueError(
                    f"scenarios.csv: maatregel '{measure_id}' in scenario '{sid}' "
                    "heeft zowel zones als overlay; kies één van beide."
                )
            if not zones and overlay is None:
                raise ValueError(
                    f"scenarios.csv: maatregel '{measure_id}' in scenario '{sid}' "
                    "heeft geen zones en geen overlay."
                )

            selections.setdefault(sid, {})[measure_id] = MeasureSelection(
                zones=zones, overlay=overlay
            )

        self._scenarios = sorted(
            scenario_meta.values(), key=lambda s: (s.priority, s.label)
        )
        self._selections = selections

    def list_scenarios(self) -> tuple[ScenarioInfo, ...]:
        return tuple(self._scenarios)

    def get_selections(self, scenario_id: str) -> Dict[str, MeasureSelection]:
        if not scenario_id:
            return {}
        return dict(self._selections.get(scenario_id, {}))

    def radio_options(self) -> list[tuple[str, str]]:
        """(id, label) pairs including Geen first."""
        return [(NONE_SCENARIO_ID, NONE_SCENARIO_LABEL)] + [
            (s.scenario_id, s.label) for s in self._scenarios
        ]
