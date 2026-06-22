"""Tests for transaction-based contour prices."""

import unittest

import pandas as pd

from contour.loaders import lees_transacties
from contour.prices import (
    PRIJS_KOLOMMEN,
    bereken_capakey_prijzen,
    transactie_prijs_euro,
    vervang_prijzen_uit_transacties,
)
from contour.schema import FLOW_KOLOMMEN, leeg_contour


class TestPrices(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.transacties = lees_transacties()

    def test_transactie_prijs_euro_prefers_p50(self) -> None:
        rij = pd.Series({"avg_PriceP50": 300000, "average_price_m2": 100, "avg_ParcelsAreaP50": 500})
        self.assertEqual(transactie_prijs_euro(rij), 300000.0)

    def test_transactie_prijs_euro_fallback_m2(self) -> None:
        rij = pd.Series({"avg_PriceP50": "", "average_price_m2": 2000, "avg_ParcelsAreaP50": 100})
        self.assertEqual(transactie_prijs_euro(rij), 200000.0)

    def test_capakey_prijzen_niet_constant_dummy(self) -> None:
        prijzen = bereken_capakey_prijzen(self.transacties)
        kolom = "prijs_bewoonde_niet_geïsoleerde_woning"
        ingevuld = prijzen[kolom].dropna()
        self.assertGreater(len(ingevuld), 1000)
        self.assertGreater(ingevuld.nunique(), 100)
        self.assertNotAlmostEqual(ingevuld.median(), 400000.0, delta=50000)

    def test_vervang_prijzen_zet_alle_kolommen(self) -> None:
        contour = leeg_contour(pd.Index([50], name="db_ondergrens"))
        self.assertEqual(list(contour.columns), list(FLOW_KOLOMMEN))
        brussel = pd.DataFrame(
            {
                "CS01012022": ["21001A00-"],
                "dB": [50],
                "Part de la surface du qs dans le noise contour": [1.0],
            }
        )
        out, _, _ = vervang_prijzen_uit_transacties(contour, self.transacties, brussel)
        for kolom in PRIJS_KOLOMMEN:
            self.assertIn(kolom, out.columns)
            self.assertTrue(pd.notna(out.loc[50, kolom]))


if __name__ == "__main__":
    unittest.main()
