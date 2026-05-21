import unittest

import pandas as pd

from ui.components import _stock_plot_frame


class TestStockPlotFrame(unittest.TestCase):
    def test_sums_regional_stocks_per_zone_and_year(self):
        df_stock = pd.DataFrame(
            [
                {"naam": "bewoonde_geïsoleerde_woning_vlaanderen", "jaar": 2026, "zone": "A", "aantal": 10.0},
                {"naam": "bewoonde_geïsoleerde_woning_brussel", "jaar": 2026, "zone": "A", "aantal": 5.0},
                {"naam": "bewoonde_geïsoleerde_woning_vlaanderen", "jaar": 2027, "zone": "A", "aantal": 8.0},
                {"naam": "bewoonde_geïsoleerde_woning_brussel", "jaar": 2027, "zone": "A", "aantal": 4.0},
            ]
        )
        result = _stock_plot_frame(df_stock, "bewoonde_geïsoleerde_woning")
        self.assertEqual(len(result), 2)
        by_year = result.set_index("jaar")["aantal"].to_dict()
        self.assertEqual(by_year[2026], 15.0)
        self.assertEqual(by_year[2027], 12.0)


if __name__ == "__main__":
    unittest.main()
