"""Tests for overlay shares and fractional measure activation."""

import unittest

import pandas as pd

from config import (
    FLOW_RULES_FILE,
    FLOW_SIZE_FILE,
    LDEN_ZONES_FILE,
    MEASURE_COSTS_FILE,
    MEASURES_FILE,
    STOCK_PRICES_FILE,
    STOCKS_FILE,
)
from models.measure_selection_manager import MeasureSelectionManager
from models.simulation_input_loader import load_simulation_inputs
from models.stock_manager import StockManager
from config import BEGINJAAR, EINDJAAR


class TestOverlayShares(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        measure_ids = tuple(
            pd.read_csv(MEASURES_FILE, usecols=["measure_id"])["measure_id"].astype(str)
        )
        cls.stock_manager = StockManager.from_lden_analysis(
            stocks_file=STOCKS_FILE,
            flow_size_file=FLOW_SIZE_FILE,
            stock_prices_file=STOCK_PRICES_FILE,
            zones_file=LDEN_ZONES_FILE,
            beginjaar=BEGINJAAR,
            measure_ids=measure_ids,
        )

    def test_share_columns_present(self) -> None:
        self.assertIn("share_lnight45", self.stock_manager.df_contour.columns)
        self.assertIn("share_na70", self.stock_manager.df_contour.columns)

    def test_lnight45_full_on_loud_bands(self) -> None:
        # Zone A/B bands should be fully covered by Lnight45
        for band, zone in self.stock_manager.band_to_zone.items():
            if zone in {"A", "B"}:
                self.assertAlmostEqual(
                    self.stock_manager.get_overlay_share(band, "lnight45"),
                    1.0,
                    places=5,
                    msg=f"band {band} zone {zone}",
                )

    def test_lnight45_zero_on_f(self) -> None:
        for band, zone in self.stock_manager.band_to_zone.items():
            if zone == "F":
                self.assertAlmostEqual(
                    self.stock_manager.get_overlay_share(band, "lnight45"),
                    0.0,
                    places=5,
                )

    def test_coverage_by_zone_matches_expectation(self) -> None:
        cov = self.stock_manager.get_overlay_coverage_by_zone().set_index("zone")
        self.assertGreater(float(cov.loc["A", "share_lnight45"]), 0.99)
        self.assertLess(float(cov.loc["F", "share_lnight45"]), 0.01)
        self.assertGreater(float(cov.loc["A", "share_na70"]), 0.99)
        self.assertLess(float(cov.loc["E", "share_na70"]), 0.01)


class TestOverlayActivation(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        measure_ids = tuple(
            pd.read_csv(MEASURES_FILE, usecols=["measure_id"])["measure_id"].astype(str)
        )
        cls.stock_manager = StockManager.from_lden_analysis(
            stocks_file=STOCKS_FILE,
            flow_size_file=FLOW_SIZE_FILE,
            stock_prices_file=STOCK_PRICES_FILE,
            zones_file=LDEN_ZONES_FILE,
            beginjaar=BEGINJAAR,
            measure_ids=measure_ids,
        )
        cls.zones = cls.stock_manager.get_zones()
        cls.selection = MeasureSelectionManager(
            zones_file=LDEN_ZONES_FILE,
            measures_file=MEASURES_FILE,
            flow_rules_file=FLOW_RULES_FILE,
            measure_costs_file=MEASURE_COSTS_FILE,
        )

    def tearDown(self) -> None:
        for measure_name in self.selection.get_measure_descriptions().index:
            self.selection.set_selected_overlay(str(measure_name), None)
            self.selection.set_selected_zones(str(measure_name), ())

    def test_overlay_clears_zones(self) -> None:
        measure = "verkavelingsverbod"
        self.selection.set_selected_zones(measure, ("A", "B"))
        self.selection.set_selected_overlay(measure, "lnight45")
        self.assertEqual(self.selection.get_selected_zones(measure), ())
        self.assertEqual(self.selection.get_selected_overlay(measure), "lnight45")

    def test_zones_clear_overlay(self) -> None:
        measure = "verkavelingsverbod"
        self.selection.set_selected_overlay(measure, "na70")
        self.selection.set_selected_zones(measure, ("C",))
        self.assertIsNone(self.selection.get_selected_overlay(measure))
        self.assertEqual(self.selection.get_selected_zones(measure), ("C",))

    def test_fractional_weight_on_band_rules(self) -> None:
        measure = "verkavelingsverbod"
        self.selection.set_selected_overlay(measure, "lnight45")
        selected_zones = [
            (name, self.selection.get_selected_zones(str(name)))
            for name in self.selection.get_measure_descriptions().index
        ]
        selected_overlays = [
            (name, self.selection.get_selected_overlay(str(name)))
            for name in self.selection.get_measure_descriptions().index
        ]
        state = load_simulation_inputs(
            stock_manager=self.stock_manager,
            beginjaar=BEGINJAAR,
            eindjaar=EINDJAAR,
            zones=self.zones,
            flow_rules_file=FLOW_RULES_FILE,
            measure_costs_file=MEASURE_COSTS_FILE,
            selected_zones=selected_zones,
            selected_overlays=selected_overlays,
        )
        # Find a zone-E band with partial share
        e_bands = [b for b, z in self.stock_manager.band_to_zone.items() if z == "E"]
        self.assertTrue(e_bands)
        band = e_bands[0]
        share = self.stock_manager.get_overlay_share(band, "lnight45")
        rules = [
            r for r in state.flow_rules_by_band[band] if r.measure_id == measure
        ]
        self.assertEqual(len(rules), 1)
        self.assertAlmostEqual(rules[0].activation_weight, share, places=5)
        self.assertEqual(rules[0].active, share > 0)

        # Zone F should be inactive for Lnight45
        f_bands = [b for b, z in self.stock_manager.band_to_zone.items() if z == "F"]
        if f_bands:
            f_rules = [
                r
                for r in state.flow_rules_by_band[f_bands[0]]
                if r.measure_id == measure
            ]
            self.assertEqual(f_rules[0].activation_weight, 0.0)
            self.assertFalse(f_rules[0].active)


if __name__ == "__main__":
    unittest.main()
