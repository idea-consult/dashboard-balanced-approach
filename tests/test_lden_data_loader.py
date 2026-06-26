"""Tests for Lden analysis data loader."""

import unittest

import pandas as pd

from config import (
    FLOW_RULES_FILE,
    FLOW_SIZE_FILE,
    LDEN_ZONES_FILE,
    MEASURES_FILE,
    STOCK_PRICES_FILE,
    STOCKS_FILE,
)
from models.lden_data_loader import (
    MEASURE_ID_TO_FLOW_COLUMN,
    load_lden_data,
)


class TestLdenDataLoader(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        measure_ids = tuple(
            pd.read_csv(MEASURES_FILE, usecols=["measure_id"])["measure_id"].astype(str)
        )
        cls.loaded = load_lden_data(
            stocks_file=STOCKS_FILE,
            flow_size_file=FLOW_SIZE_FILE,
            stock_prices_file=STOCK_PRICES_FILE,
            zones_file=LDEN_ZONES_FILE,
            measure_ids=measure_ids,
        )

    def test_bands_have_zones(self) -> None:
        self.assertGreater(len(self.loaded.bands), 0)
        for band in self.loaded.bands:
            self.assertIn(band, self.loaded.band_to_zone)
            self.assertIn(self.loaded.band_to_zone[band], {"A", "B", "C", "D", "E", "F"})

    def test_regional_stock_columns_present(self) -> None:
        df = self.loaded.df_contour
        self.assertIn("bewoonde_niet_geïsoleerde_woning_vlaanderen", df.columns)
        self.assertIn("bewoonde_niet_geïsoleerde_woning_brussel", df.columns)
        self.assertIn("inwoners_vlaanderen", df.columns)
        self.assertIn("inwoners_brussel", df.columns)

    def test_regional_stocks_have_no_nan(self) -> None:
        df = self.loaded.df_contour
        regional_cols = [c for c in df.columns if c.endswith(("_vlaanderen", "_brussel"))]
        self.assertGreater(len(regional_cols), 0)
        self.assertFalse(df[regional_cols].isna().any().any())

    def test_inwoners_split_sums_to_total(self) -> None:
        df = self.loaded.df_contour
        total = df["inwoners_vlaanderen"] + df["inwoners_brussel"]
        pd.testing.assert_series_equal(
            total,
            df["inwoners_per_contour"],
            check_names=False,
            rtol=1e-9,
            atol=1e-6,
        )

    def test_verkavelingsverbod_column_mapping(self) -> None:
        self.assertEqual(
            MEASURE_ID_TO_FLOW_COLUMN["verkavelingsverbod"], "verkavelings_verbod"
        )
        flow_df = pd.read_csv(FLOW_SIZE_FILE)
        self.assertIn("verkavelings_verbod_baseline", flow_df.columns)
        rates = self.loaded.flow_rates_by_band[self.loaded.bands[0]]
        self.assertIn("verkavelingsverbod", rates)

    def test_flow_rates_from_flow_rules_measures(self) -> None:
        measure_ids = set(pd.read_csv(FLOW_RULES_FILE)["measure_id"].astype(str))
        for band, band_rates in self.loaded.flow_rates_by_band.items():
            self.assertEqual(set(band_rates.keys()), measure_ids, f"band {band}")
