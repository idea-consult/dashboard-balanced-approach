"""Tests for jaarlijks gemiddelde vergunningstellers."""

import unittest

import pandas as pd

from contour.vergunningen import (
    JAAR_TELLERS_LABEL,
    gem_wooneenheden_per_vergunning_gemiddelde,
    gemiddelde_jaarlijkse_vergunningen,
)


class TestVergunningenGemiddelde(unittest.TestCase):
    def _rij(self, jaar: int, waarde: float, handeling: str = "Nieuwbouw") -> dict:
        return {
            "bron": "omgevingsloket",
            "jaar_indiening": jaar,
            "gemeente": "Teststad",
            "handeling": handeling,
            "gebouw_functie": "-",
            "metriek": "Aantal wooneenheden",
            "waarde": waarde,
        }

    def test_gemiddelde_over_zes_jaar(self) -> None:
        df = pd.DataFrame(
            [
                self._rij(2020, 12.0),
                self._rij(2021, 18.0),
            ]
        )
        out = gemiddelde_jaarlijkse_vergunningen(df, 2020, 2025)
        self.assertEqual(len(out), 1)
        self.assertEqual(out.iloc[0]["jaar_indiening"], JAAR_TELLERS_LABEL)
        # (12 + 18) / 6 = 5.0
        self.assertAlmostEqual(float(out.iloc[0]["waarde"]), 5.0)

    def test_sluit_totalen_uit(self) -> None:
        df = pd.DataFrame(
            [
                self._rij(2020, 6.0),
                {
                    **self._rij(2020, 999.0),
                    "gemeente": "Totalen",
                    "handeling": "Totalen",
                },
            ]
        )
        out = gemiddelde_jaarlijkse_vergunningen(df, 2020, 2025)
        self.assertAlmostEqual(float(out.iloc[0]["waarde"]), 1.0)

    def test_gem_wooneenheden_per_vergunning_jaarlijks(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "bron": "omgevingsloket",
                    "jaar_indiening": 2020,
                    "gemeente": "A",
                    "handeling": "Nieuwbouw",
                    "gebouw_functie": "-",
                    "metriek": "Aantal projecten",
                    "waarde": 10.0,
                },
                {
                    "bron": "omgevingsloket",
                    "jaar_indiening": 2020,
                    "gemeente": "A",
                    "handeling": "Nieuwbouw",
                    "gebouw_functie": "-",
                    "metriek": "Aantal wooneenheden",
                    "waarde": 20.0,
                },
                {
                    "bron": "omgevingsloket",
                    "jaar_indiening": 2021,
                    "gemeente": "A",
                    "handeling": "Nieuwbouw",
                    "gebouw_functie": "-",
                    "metriek": "Aantal projecten",
                    "waarde": 5.0,
                },
                {
                    "bron": "omgevingsloket",
                    "jaar_indiening": 2021,
                    "gemeente": "A",
                    "handeling": "Nieuwbouw",
                    "gebouw_functie": "-",
                    "metriek": "Aantal wooneenheden",
                    "waarde": 15.0,
                },
            ]
        )
        # ratio 2020=2.0, 2021=3.0, over 2020-2025 => (2+3+0+0+0+0)/6
        gem = gem_wooneenheden_per_vergunning_gemiddelde(df, 2020, 2025)
        self.assertAlmostEqual(gem, 5.0 / 6.0)


if __name__ == "__main__":
    unittest.main()
