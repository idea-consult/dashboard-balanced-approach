import unittest

import pandas as pd

from config import FLOW_SIZE_FILE, FLOW_RULES_FILE, MEASURES_FILE, MEASURE_COSTS_FILE, LDEN_ZONES_FILE, STOCKS_FILE, STOCK_PRICES_FILE, BEGINJAAR
from models.flow_help_rates import apply_flow_size_rates_to_rules, summarize_measure_rates
from models.measure_selection_manager import MeasureSelectionManager
from models.stock_manager import StockManager


class TestFlowHelpRates(unittest.TestCase):
    def test_aankoopbeleid_active_rate_from_flow_size_not_flow_rules(self):
        flow_size = pd.read_csv(FLOW_SIZE_FILE)
        baseline, active = summarize_measure_rates(
            flow_size, "aankoopbeleid_niet_geïsoleerde_woningen"
        )
        self.assertLess(active, 0.1)
        self.assertGreater(active, 0.01)

        rules = pd.read_csv(FLOW_RULES_FILE)
        row = rules[rules.measure_id == "aankoopbeleid_niet_geïsoleerde_woningen"].iloc[0]
        self.assertGreater(float(row.flow_rate_active), 0.9)

        enriched = apply_flow_size_rates_to_rules(
            rules[rules.measure_id == "aankoopbeleid_niet_geïsoleerde_woningen"],
            flow_size,
        )
        self.assertAlmostEqual(float(enriched.iloc[0].flow_rate_active), active, places=9)

    def test_measure_help_uses_flow_size_when_stock_manager_given(self):
        from ui.components import _measure_help

        measure_ids = tuple(
            pd.read_csv(MEASURES_FILE, usecols=["measure_id"])["measure_id"].astype(str)
        )
        stock_manager = StockManager.from_lden_analysis(
            stocks_file=STOCKS_FILE,
            flow_size_file=FLOW_SIZE_FILE,
            stock_prices_file=STOCK_PRICES_FILE,
            zones_file=LDEN_ZONES_FILE,
            beginjaar=BEGINJAAR,
            measure_ids=measure_ids,
        )
        manager = MeasureSelectionManager(
            zones_file=LDEN_ZONES_FILE,
            measures_file=MEASURES_FILE,
            flow_rules_file=FLOW_RULES_FILE,
            measure_costs_file=MEASURE_COSTS_FILE,
        )
        help_text = _measure_help(
            manager, "aankoopbeleid_niet_geïsoleerde_woningen", pd.read_csv(FLOW_SIZE_FILE)
        )
        self.assertIn("3,2752 %", help_text)
        self.assertNotIn("97", help_text)


if __name__ == "__main__":
    unittest.main()
