import unittest

import pandas as pd

from config import FLOW_RULES_FILE, MEASURE_COSTS_FILE, MEASURES_FILE, LDEN_ZONES_FILE
from models.measure_selection_manager import MeasureSelectionManager
from ui.components import _measure_help
from ui.measure_help import combine_measure_help, format_flow_help_section


class TestMeasureHelp(unittest.TestCase):
    def test_format_flow_help_contains_mode_and_rates(self):
        rules = pd.DataFrame(
            [
                {
                    "measure_id": "aankoopbeleid_percelen",
                    "inflow_stock": "onbebouwde_bebouwbare_percelen",
                    "outflow_stock": "perceel_eigendom_overheid",
                    "flow_rate_baseline": 0.0,
                    "flow_rate_active": 0.01,
                    "flow_mode": "transfer",
                    "priority": 3,
                    "comments": "",
                }
            ]
        )
        text = format_flow_help_section(rules)
        self.assertIn("krimpt", text)
        self.assertIn("overgedragen wordt naar", text)
        self.assertIn("niet geselecteerd", text)
        self.assertIn("wel geselecteerd", text)
        self.assertIn("onbebouwde bebouwbare percelen", text)
        self.assertIn("1,0000 %", text)

    def test_measure_help_via_manager(self):
        manager = MeasureSelectionManager(
            zones_file=LDEN_ZONES_FILE,
            measures_file=MEASURES_FILE,
            flow_rules_file=FLOW_RULES_FILE,
            measure_costs_file=MEASURE_COSTS_FILE,
        )
        help_text = _measure_help(manager, "verkavelingsverbod")
        self.assertIn("### Uitleg", help_text)
        self.assertIn("zorgt ervoor dat de stock groeit", help_text)
        self.assertIn("niet geselecteerd", help_text)
        self.assertIn("0,0000 %", help_text)
        self.assertIn("gewogen gemiddelden", help_text)

    def test_combine_without_flow_rules(self):
        result = combine_measure_help("Alleen uitleg", pd.DataFrame())
        self.assertEqual(result, "Alleen uitleg")


if __name__ == "__main__":
    unittest.main()
