"""Tests for ScenarioManager."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from models.scenario_manager import NONE_SCENARIO_ID, ScenarioManager


class TestScenarioManager(unittest.TestCase):
    def test_loads_scenario_labels_without_measures(self) -> None:
        csv = (
            "scenario_id,scenario_label,priority,measure_id,zones,overlay\n"
            "minimaal,Minimaal ambitieniveau,1,,,\n"
            "maximaal,Maximaal ambitieniveau,2,,,\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scenarios.csv"
            path.write_text(csv, encoding="utf-8")
            mgr = ScenarioManager(str(path), known_measure_ids={"woongebiedverbod"})
            scenarios = mgr.list_scenarios()
            self.assertEqual(len(scenarios), 2)
            self.assertEqual(scenarios[0].scenario_id, "minimaal")
            self.assertEqual(mgr.get_selections("minimaal"), {})
            options = mgr.radio_options()
            self.assertEqual(options[0][0], NONE_SCENARIO_ID)

    def test_zones_and_overlay_selection(self) -> None:
        csv = (
            "scenario_id,scenario_label,priority,measure_id,zones,overlay\n"
            "minimaal,Minimaal,1,woongebiedverbod,A;B;C,\n"
            "minimaal,Minimaal,1,verkavelingsverbod,,lnight45\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scenarios.csv"
            path.write_text(csv, encoding="utf-8")
            mgr = ScenarioManager(
                str(path),
                known_measure_ids={"woongebiedverbod", "verkavelingsverbod"},
            )
            sel = mgr.get_selections("minimaal")
            self.assertEqual(sel["woongebiedverbod"].zones, ("A", "B", "C"))
            self.assertIsNone(sel["woongebiedverbod"].overlay)
            self.assertEqual(sel["verkavelingsverbod"].overlay, "lnight45")
            self.assertEqual(sel["verkavelingsverbod"].zones, ())

    def test_rejects_zones_and_overlay_together(self) -> None:
        csv = (
            "scenario_id,scenario_label,priority,measure_id,zones,overlay\n"
            "minimaal,Minimaal,1,woongebiedverbod,A,lnight45\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scenarios.csv"
            path.write_text(csv, encoding="utf-8")
            with self.assertRaises(ValueError):
                ScenarioManager(str(path), known_measure_ids={"woongebiedverbod"})

    def test_rejects_unknown_measure(self) -> None:
        csv = (
            "scenario_id,scenario_label,priority,measure_id,zones,overlay\n"
            "minimaal,Minimaal,1,onbekend,A,\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scenarios.csv"
            path.write_text(csv, encoding="utf-8")
            with self.assertRaises(ValueError):
                ScenarioManager(str(path), known_measure_ids={"woongebiedverbod"})

    def test_real_scenarios_file_loads(self) -> None:
        from config import MEASURES_FILE, SCENARIOS_FILE

        known = set(
            pd.read_csv(MEASURES_FILE, usecols=["measure_id"])["measure_id"].astype(str)
        )
        mgr = ScenarioManager(SCENARIOS_FILE, known_measure_ids=known)
        self.assertGreaterEqual(len(mgr.list_scenarios()), 4)


if __name__ == "__main__":
    unittest.main()
