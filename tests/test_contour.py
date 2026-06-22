"""Tests for contour data pipeline and flow rates."""

import unittest
from pathlib import Path

import pandas as pd

from contour.columns import (
    KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR,
    KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR,
    _EXCEL_WOONGEBIED_AANDUIDING,
    _EXCEL_WOONGEBIED_SCHRAPPING,
    hernoem_vlaanderen_kolommen,
)
from contour.consolidate import bouw_contour_lden, bouw_lden, bouw_lden_regional
from contour.schema import FLOW_STOCKS, regional_stock_kolom
from contour.flows import bereken_flow_rate, bereken_alle_flow_rates, valideer_flow_rates
from contour.pipeline import run_data_pipeline, run_flows_pipeline
from contour.paths import INTERMEDIATE_DIR
from contour.schema import FLOW_KOLOMMEN, assert_flow_schema


class TestContourPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tables = run_data_pipeline()
        cls.flows = run_flows_pipeline(cls.tables, export_inputs=False)

    def test_contour_band_count(self) -> None:
        self.assertEqual(len(self.tables["lden"]), 30)

    def test_flow_schema(self) -> None:
        assert_flow_schema(self.tables["lden"])
        assert_flow_schema(self.tables["lnight"])
        self.assertEqual(list(self.tables["lden"].columns), list(FLOW_KOLOMMEN))

    def test_parquet_written(self) -> None:
        self.assertTrue((INTERMEDIATE_DIR / "lden.parquet").exists())
        self.assertTrue((INTERMEDIATE_DIR / "flow_rates.parquet").exists())

    def test_vergunningen_contour_toegewezen(self) -> None:
        verg_contour = self.tables["vergunningen_contour"]
        self.assertGreater(len(verg_contour), 0, "vergunningen_contour moet rijen hebben na gemeente-koppeling")
        self.assertGreater(float(verg_contour["waarde"].sum()), 0)

    def test_flow_rates_cover_all_measures(self) -> None:
        rules = pd.read_csv("input/flow_rules.csv")
        rates = self.flows["flow_rates"]
        self.assertEqual(len(rates), len(rules))
        self.assertSetEqual(set(rates["measure_id"]), set(rules["measure_id"]))

    def test_flow_rates_bounded(self) -> None:
        validatie = valideer_flow_rates(self.flows["flow_rates"])
        flagged = validatie[~validatie["rate_ok"]]
        self.assertTrue(
            flagged.empty,
            f"Rates > 1: {flagged['measure_id'].tolist()}",
        )

    def test_bereken_flow_rate_safe(self) -> None:
        self.assertEqual(bereken_flow_rate(10, 0), 0.0)
        self.assertEqual(bereken_flow_rate(5, 10), 0.5)


class TestRegionalLayer(unittest.TestCase):
    def test_regional_som_gelijk_aan_flow_totaal(self) -> None:
        lden = bouw_lden()
        regional = bouw_lden_regional()
        self.assertEqual(len(regional), len(lden))
        for stock in FLOW_STOCKS:
            totaal = (
                regional[regional_stock_kolom(stock, "vlaanderen")]
                + regional[regional_stock_kolom(stock, "brussel")]
            )
            pd.testing.assert_series_equal(
                totaal,
                lden[stock],
                check_names=False,
                obj=f"stock {stock}",
            )
        self.assertGreater(regional["inwoners_brussel"].sum(), 0)
        self.assertGreater(regional["inwoners_vlaanderen"].sum(), 0)


class TestPlaceholderStocks(unittest.TestCase):
    def test_onbebouwde_percelen_niet_uit_woongebied(self) -> None:
        """Woongebied-kolommen zijn flow-tellers; parcel-stocks starten op 0."""
        df = bouw_contour_lden()
        assert_flow_schema(df)
        self.assertEqual(df["onbebouwde_bebouwbare_percelen"].sum(), 0.0)
        self.assertEqual(df["onbebouwde_onbebouwbare_percelen"].sum(), 0.0)
        mask = df[KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR] > 0
        if mask.any():
            self.assertFalse((df.loc[mask, "onbebouwde_bebouwbare_percelen"] > 0).any())
            self.assertFalse((df.loc[mask, "onbebouwde_onbebouwbare_percelen"] > 0).any())


class TestColumnRename(unittest.TestCase):
    def test_woongebied_kolommen_flow_namen(self) -> None:
        df = hernoem_vlaanderen_kolommen(
            pd.DataFrame(
                columns=[
                    "db_contour",
                    _EXCEL_WOONGEBIED_AANDUIDING,
                    _EXCEL_WOONGEBIED_SCHRAPPING,
                ]
            )
        )
        self.assertIn(KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR, df.columns)
        self.assertIn(KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR, df.columns)


if __name__ == "__main__":
    unittest.main()
