"""Tests for contour_data_vlaanderen.ipynb code generation."""

import unittest

from contour.data_notebook import DATA_STAP_VOLGORDE
from contour.data_notebook_vlaanderen import (
    stap_grafiek_code_vla,
    stap_notebook_code_vla,
)


class TestDataNotebookVlaanderen(unittest.TestCase):
    def test_notebook_code_voor_alle_stappen(self) -> None:
        for stap_id in DATA_STAP_VOLGORDE:
            code = stap_notebook_code_vla(stap_id)
            self.assertTrue(len(code) > 10, stap_id)
            self.assertNotIn("brussel", code.lower(), stap_id)
            self.assertNotIn("lnight", code, stap_id)

    def test_grafiek_code_voor_alle_stappen(self) -> None:
        for stap_id in DATA_STAP_VOLGORDE:
            code = stap_grafiek_code_vla(stap_id)
            self.assertTrue("staafdiagram" in code or "toon_staaf_per_contour" in code, stap_id)

    def test_gebruikt_vla_tabel(self) -> None:
        code = stap_notebook_code_vla("inwoners_per_contour")
        self.assertIn("vla['inwoners_per_contour']", code)
        self.assertIn("raw_vla_lden", code)

    def test_capakey_extern_vlaanderen(self) -> None:
        prep = stap_notebook_code_vla("transacties_en_capakey_prijzen")
        self.assertIn("laad_capakey_contour_extern", prep)
        self.assertNotIn("bouw_capakey_contour_mapping", prep)


if __name__ == "__main__":
    unittest.main()
