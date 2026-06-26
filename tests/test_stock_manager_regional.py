"""Tests for FLOW contour + regional sidecar in StockManager."""

import unittest

import pandas as pd

from config import (
    BEGINJAAR,
    FLOW_SIZE_FILE,
    LDEN_ZONES_FILE,
    MEASURES_FILE,
    STOCK_PRICES_FILE,
    STOCKS_FILE,
)
from models.stock_manager import StockManager


class TestStockManagerRegional(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        measure_ids = tuple(
            pd.read_csv(MEASURES_FILE, usecols=["measure_id"])["measure_id"].astype(str)
        )
        cls.manager = StockManager.from_lden_analysis(
            stocks_file=STOCKS_FILE,
            flow_size_file=FLOW_SIZE_FILE,
            stock_prices_file=STOCK_PRICES_FILE,
            zones_file=LDEN_ZONES_FILE,
            beginjaar=BEGINJAAR,
            measure_ids=measure_ids,
        )

    def test_regional_layer_geladen(self) -> None:
        self.assertTrue(self.manager._has_regional_layer)
        self.assertTrue(self.manager._lden_band_mode)

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

    def test_band_totals_match_zone_aggregation(self) -> None:
        stock = "bewoonde_geïsoleerde_woning_vlaanderen"
        zone = self.manager.get_zones()[0]
        zone_total = self.manager.get_aantal(stock, BEGINJAAR, zone)
        band_sum = sum(
            self.manager.get_aantal_for_band(stock, BEGINJAAR, band)
            for band in self.manager.get_bands()
            if self.manager.band_to_zone[band] == zone
        )
        self.assertAlmostEqual(zone_total, band_sum, places=3)


if __name__ == "__main__":
    unittest.main()
