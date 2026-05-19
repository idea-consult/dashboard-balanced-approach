"""Tests for point-based leefbaarheidspunten calculation."""

import unittest
import pandas as pd

from config import (
    BEGINJAAR,
    EINDJAAR,
    LDEN_CONTOUR_FILE,
    LDEN_ZONES_FILE,
    MEASURES_FILE,
    FLOW_RULES_FILE,
    MEASURE_COSTS_FILE,
)
from models.stock_manager import StockManager
from models.measure_selection_manager import MeasureSelectionManager
from simulation.engine import SimulationEngine
from simulation.helpers import calculate_leefbaarheidspunten_for_contour


class TestLeefbaarheidspunten(unittest.TestCase):
    def test_calculate_leefbaarheidspunten_for_contour(self):
        contour_df = pd.DataFrame(
            {
                "bewoonde_niet_geïsoleerde_woning": [2.0, 1.0],
                "bewoonde_geïsoleerde_woning": [1.0, 0.0],
                "gemiddeld_aantal_inwoners_per_huis": [2.0, 4.0],
            }
        )
        zonder, met, totaal = calculate_leefbaarheidspunten_for_contour(
            contour_df, punten_niet_geisoleerd=64.0, punten_geisoleerd=32.0
        )
        self.assertEqual(zonder, (2 * 2 + 1 * 4) * 64)
        self.assertEqual(met, (1 * 2 + 0 * 4) * 32)
        self.assertEqual(totaal, zonder + met)

    def test_default_weights_from_lden_zones(self):
        stock_manager = StockManager(LDEN_CONTOUR_FILE, LDEN_ZONES_FILE, BEGINJAAR)
        weights = stock_manager.get_default_leefbaarheidspunten_weights()
        self.assertEqual(weights["A"]["niet_geïsoleerd"], 64.0)
        self.assertEqual(weights["A"]["geïsoleerd"], 32.0)
        self.assertEqual(weights["F"]["niet_geïsoleerd"], 2.0)
        self.assertEqual(weights["F"]["geïsoleerd"], 1.0)

    def test_engine_calculate_leefbaarheidspunten_stores_metrics(self):
        stock_manager = StockManager(LDEN_CONTOUR_FILE, LDEN_ZONES_FILE, BEGINJAAR)
        selection_manager = MeasureSelectionManager(
            zones_file=LDEN_ZONES_FILE,
            measures_file=MEASURES_FILE,
            flow_rules_file=FLOW_RULES_FILE,
            measure_costs_file=MEASURE_COSTS_FILE,
        )
        engine = SimulationEngine(
            stock_manager,
            selection_manager,
            zones=stock_manager.get_zones(),
            zones_file=LDEN_ZONES_FILE,
        )
        weights = stock_manager.get_default_leefbaarheidspunten_weights()
        engine.calculate_leefbaarheidspunten(BEGINJAAR, EINDJAAR, weights)

        total_begin = stock_manager.get_aantal("leefbaarheidspunten", BEGINJAAR, "Totaal")
        zone_a_begin = stock_manager.get_aantal("leefbaarheidspunten", BEGINJAAR, "A")
        self.assertGreater(total_begin, 0)
        self.assertGreater(zone_a_begin, 0)
        self.assertEqual(
            stock_manager.get_aantal("leefbaarheidspunten", BEGINJAAR, "A"),
            stock_manager.get_aantal("leefbaarheidspunten_zonder_isolatie", BEGINJAAR, "A")
            + stock_manager.get_aantal("leefbaarheidspunten_met_isolatie", BEGINJAAR, "A"),
        )


if __name__ == "__main__":
    unittest.main()
