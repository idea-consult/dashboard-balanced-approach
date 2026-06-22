"""Tests for per-contour flow rate calculation."""

import unittest

import pandas as pd

from contour.consolidate import bouw_lden
from contour.flows_per_contour import (
    FLOW_STAP_VOLGORDE,
    aggregeer_naar_flow_rules,
    bouw_lden_flows,
    kolom_active,
    kolom_baseline,
    lden_vars_bereiden,
    stap_notebook_code,
    stap_woongebiedverbod,
    init_lden_flows,
)


class TestFlowsPerContour(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        lden = bouw_lden()
        cls.lden_vars = lden_vars_bereiden(lden)

    def test_woongebiedverbod_per_band(self) -> None:
        flows = stap_woongebiedverbod(init_lden_flows(self.lden_vars), self.lden_vars)
        idx = 45
        bebouw = float(self.lden_vars.loc[idx, "bebouwbare_percelen_woongebied(5jr)"]) / 5
        schr = float(self.lden_vars.loc[idx, "niet_bebouwbare_percelen_woongebied_schrapping(5jr)"]) / 5
        noemer = float(self.lden_vars.loc[idx, "onbebouwde_onbebouwbare_percelen"])
        if noemer > 0:
            self.assertAlmostEqual(
                float(flows.loc[idx, kolom_baseline("woongebiedverbod")]),
                (bebouw - schr) / noemer,
            )
            self.assertAlmostEqual(
                float(flows.loc[idx, kolom_active("woongebiedverbod")]),
                schr / noemer,
            )

    def test_alle_stappen_kolommen(self) -> None:
        flows = bouw_lden_flows(self.lden_vars)
        expected = {kolom_baseline(m) for m in FLOW_STAP_VOLGORDE} | {
            kolom_active(m) for m in FLOW_STAP_VOLGORDE
        }
        self.assertEqual(set(flows.columns), expected)
        self.assertEqual(len(flows), len(self.lden_vars))

    def test_notebook_code_voor_alle_stappen(self) -> None:
        from contour.flow_stap_docs import FLOW_STAP_DEFINITIES

        for measure_id in FLOW_STAP_VOLGORDE:
            code = stap_notebook_code(measure_id)
            self.assertIn(f'lden_flows["{kolom_baseline(measure_id)}"]', code)
            self.assertIn(f'lden_flows["{kolom_active(measure_id)}"]', code)
            self.assertNotIn("voer_flow_stap", code)
            info = FLOW_STAP_DEFINITIES[measure_id]
            self.assertTrue(info.uitleg)
            self.assertTrue(info.aannames)

    def test_aggregeer_flow_rules(self) -> None:
        flows = bouw_lden_flows(self.lden_vars)
        agg = aggregeer_naar_flow_rules(self.lden_vars, flows)
        self.assertEqual(len(agg), len(FLOW_STAP_VOLGORDE))
        self.assertIn("flow_rate_baseline", agg.columns)
        self.assertIn("flow_rate_active", agg.columns)


if __name__ == "__main__":
    unittest.main()
