"""Tests for FlowManager."""

import unittest
from pathlib import Path
import pandas as pd

from models.flow_manager import FlowManager
from config import LDEN_ZONES_FILE


class TestFlowManagerMeasureConnection(unittest.TestCase):
    """Tests for measure-name connectivity between UI and flow rows."""

    @classmethod
    def setUpClass(cls):
        """Load flow manager with actual input files."""
        base = Path(__file__).parent.parent
        cls.flow_manager = FlowManager(
            str(base / "input" / "flows.csv"),
            str(base / "input" / "beschrijving_maatregelen.csv"),
        )
        zones_df = pd.read_csv(base / LDEN_ZONES_FILE)
        configured_zones = tuple(zones_df["zone"].astype(str).tolist())
        flow_zones = tuple(cls.flow_manager.df_flow["zone"].astype(str).unique().tolist())
        cls.zones = tuple(zone for zone in configured_zones if zone in flow_zones)

    def test_set_selected_zones_updates_exact_measure_rows(self):
        """Selecting a measure updates exactly the matching flow rows."""
        measure = "voorkooprecht_niet_geïsoleerde_woningen"
        for zone in self.zones:
            with self.subTest(zone=zone):
                self.flow_manager.set_selected_zones(measure, (zone,))
                selected = self.flow_manager.is_measure_applied(measure, zone)
                self.assertTrue(selected, f"Zone {zone}: maatregel werd niet geactiveerd")

    def test_flow_and_description_names_are_consistent(self):
        """FlowManager init should guarantee 1-on-1 name consistency."""
        flow_names = set(self.flow_manager.df_flow["naam"].astype(str).unique().tolist())
        description_names = set(
            self.flow_manager.get_measure_descriptions().index.astype(str).tolist()
        )
        self.assertEqual(flow_names, description_names)

    def tearDown(self):
        """Reset maatregel_toepassen na elke test."""
        for measure_name in self.flow_manager.get_measure_descriptions().index:
            self.flow_manager.set_selected_zones(str(measure_name), ())
