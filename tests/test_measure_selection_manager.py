"""Tests for MeasureSelectionManager."""

import unittest
from pathlib import Path
import pandas as pd

from models.measure_selection_manager import MeasureSelectionManager
from config import (
    LDEN_ZONES_FILE,
    MEASURES_FILE,
    FLOW_RULES_FILE,
    MEASURE_COSTS_FILE,
)


class TestMeasureSelectionManagerConnection(unittest.TestCase):
    """Tests for measure-name connectivity between UI and flow rows."""

    @classmethod
    def setUpClass(cls):
        """Load flow manager with actual input files."""
        base = Path(__file__).parent.parent
        cls.selection_manager = MeasureSelectionManager(
            zones_file=str(base / LDEN_ZONES_FILE),
            measures_file=str(base / MEASURES_FILE),
            flow_rules_file=str(base / FLOW_RULES_FILE),
            measure_costs_file=str(base / MEASURE_COSTS_FILE),
        )
        zones_df = pd.read_csv(base / LDEN_ZONES_FILE)
        configured_zones = tuple(zones_df["zone"].astype(str).tolist())
        selection_zones = tuple(
            cls.selection_manager.df_selection["zone"].astype(str).unique().tolist()
        )
        cls.zones = tuple(zone for zone in configured_zones if zone in selection_zones)

    def test_set_selected_zones_updates_exact_measure_rows(self):
        """Selecting a measure updates exactly the matching flow rows."""
        measure = "voorkooprecht_niet_geïsoleerde_woningen"
        for zone in self.zones:
            with self.subTest(zone=zone):
                self.selection_manager.set_selected_zones(measure, (zone,))
                selected = self.selection_manager.is_measure_applied(measure, zone)
                self.assertTrue(selected, f"Zone {zone}: maatregel werd niet geactiveerd")

    def test_flow_and_description_names_are_consistent(self):
        """Manager init should guarantee 1-on-1 name consistency."""
        flow_names = set(self.selection_manager.df_selection["naam"].astype(str).unique().tolist())
        description_names = set(
            self.selection_manager.get_measure_descriptions().index.astype(str).tolist()
        )
        self.assertEqual(flow_names, description_names)

    def test_ui_sidebar_follows_measures_csv_priority(self):
        """Sidebar order follows priority column in measures.csv."""
        entries = self.selection_manager.get_ui_sidebar_entries()
        keys = [key for _, key in entries]
        self.assertEqual(keys[0], "verkavelingsverbod")
        self.assertEqual(keys[1], "woongebiedverbod")
        self.assertIn(("group", "aankoopbeleid_woningen"), entries)
        aankoop_idx = keys.index("aankoopbeleid_woningen")
        voorkoop_idx = keys.index("voorkooprecht_woningen")
        onteigening_idx = keys.index("onteigenen_woningen")
        self.assertLess(aankoop_idx, voorkoop_idx)
        self.assertLess(voorkoop_idx, onteigening_idx)
        self.assertNotIn("renovatie_zonder_maatregel", keys)

    def tearDown(self):
        """Reset maatregel_toepassen na elke test."""
        for measure_name in self.selection_manager.get_measure_descriptions().index:
            self.selection_manager.set_selected_zones(str(measure_name), ())
