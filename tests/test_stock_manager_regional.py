"""Tests for FLOW contour + regional sidecar in StockManager."""

import unittest

from config import BEGINJAAR, LDEN_CONTOUR_FILE, LDEN_ZONES_FILE
from contour.export import export_lden_contour, export_lden_contour_regional
from contour.consolidate import bouw_lden, bouw_lden_regional
from models.stock_manager import StockManager


class TestStockManagerRegional(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        export_lden_contour(bouw_lden())
        export_lden_contour_regional(bouw_lden_regional())
        cls.manager = StockManager(LDEN_CONTOUR_FILE, LDEN_ZONES_FILE, BEGINJAAR)

    def test_regional_layer_geladen(self) -> None:
        self.assertTrue(self.manager._has_regional_layer)

    def test_simulatie_gebruikt_regionale_stocks(self) -> None:
        names = self.manager.get_simulation_stock_names()
        self.assertIn("bewoonde_geïsoleerde_woning_vlaanderen", names)
        self.assertIn("bewoonde_geïsoleerde_woning_brussel", names)
        self.assertNotIn("bewoonde_geïsoleerde_woning", names)

    def test_brussel_stock_positief(self) -> None:
        brussel = sum(
            self.manager.get_aantal("bewoonde_niet_geïsoleerde_woning_brussel", BEGINJAAR, z)
            for z in self.manager.get_zones()
        )
        vlaanderen = sum(
            self.manager.get_aantal("bewoonde_niet_geïsoleerde_woning_vlaanderen", BEGINJAAR, z)
            for z in self.manager.get_zones()
        )
        self.assertGreater(brussel, 0.0)
        self.assertGreater(vlaanderen, 0.0)


if __name__ == "__main__":
    unittest.main()
