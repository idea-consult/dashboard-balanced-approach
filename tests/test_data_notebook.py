"""Tests for contour_data.ipynb code generation."""

import unittest

from contour.data_notebook import DATA_STAP_VOLGORDE, stap_notebook_code


class TestDataNotebook(unittest.TestCase):
    def test_notebook_code_voor_alle_stappen(self) -> None:
        for stap_id in DATA_STAP_VOLGORDE:
            code = stap_notebook_code(stap_id)
            self.assertTrue(len(code) > 10, stap_id)
            self.assertNotIn("run_data_pipeline", code)
            self.assertNotIn("bouw_lden(", code)

    def test_grafiek_code_voor_alle_stappen(self) -> None:
        from contour.data_notebook import stap_grafiek_code

        for stap_id in DATA_STAP_VOLGORDE:
            code = stap_grafiek_code(stap_id)
            self.assertTrue("staafdiagram" in code or "toon_staaf_per_contour" in code, stap_id)

    def test_prijs_woning_expliciet(self) -> None:
        code = stap_notebook_code("prijs_bewoonde_niet_geïsoleerde_woning")
        self.assertIn("capakey_prijzen", code)
        self.assertIn("capakey_mapping", code)
        self.assertIn("_gewogen_gem", code)
        self.assertIn("prijs_bewoonde_niet_geïsoleerde_woning", code)

        prep = stap_notebook_code("transacties_en_capakey_prijzen")
        self.assertIn("SEGMENTEN_PER_PRIJSKOLOM", prep)
        self.assertIn("prijs_bewoonde_niet_geïsoleerde_woning", prep)


if __name__ == "__main__":
    unittest.main()
