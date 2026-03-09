"""Tests for FlowManager."""

import unittest
from pathlib import Path

from models.flow_manager import FlowManager
from config import ZONES


class TestFlowManagerIsolatievoorschriften(unittest.TestCase):
    """Tests that isolatievoorschriften_nieuwbouw returns 1 when activated."""

    @classmethod
    def setUpClass(cls):
        """Load flow manager with actual input files."""
        base = Path(__file__).parent.parent
        cls.flow_manager = FlowManager(
            str(base / "input" / "20260302_flows.csv"),
            str(base / "input" / "beschrijving_maatregelen.csv"),
        )

    def test_get_flow_returns_1_when_isolatievoorschriften_activated(self):
        """
        Als isolatievoorschriften_nieuwbouw is geactiveerd voor een zone,
        moet get_flow ratio 1 retourneren (100% van nieuwbouw is geïsoleerd).
        """
        

        for zone in ZONES:
            with self.subTest(zone=zone):
                self.flow_manager.set_selected_zones(
                    "isolatievoorschriften_nieuwbouw", (zone,)
                )
                ratio = self.flow_manager.get_flow(
                    "isolatievoorschriften_nieuwbouw", zone
                )
                self.assertEqual(
                    ratio,
                    (1,1),
                    f"Zone {zone}: verwacht ratio 1 wanneer maatregel actief, krijg {ratio}",
                )

    def tearDown(self):
        """Reset maatregel_toepassen na elke test."""
        self.flow_manager.set_selected_zones("isolatievoorschriften_nieuwbouw", ())
