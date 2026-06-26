"""Regression tests for SimulationEngine pipeline outputs."""

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    BEGINJAAR,
    EINDJAAR,
    MEASURES_FILE,
    FLOW_RULES_FILE,
    MEASURE_COSTS_FILE,
    FLOW_SIZE_FILE,
    LDEN_ZONES_FILE,
    OUTPUT_FLOW_LOG_ZONE_FILE,
    STOCK_PRICES_FILE,
    STOCKS_FILE,
)
from models.stock_manager import StockManager
from models.measure_selection_manager import MeasureSelectionManager
from simulation.engine import SimulationEngine
from simulation.state import FlowRule, SimulationState


class TestEngineRegression(unittest.TestCase):
    """Ensure split pipeline and wrapper produce stable outputs."""

    def _build_engine(self) -> tuple[SimulationEngine, MeasureSelectionManager]:
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
        selection_manager = MeasureSelectionManager(
            zones_file=LDEN_ZONES_FILE,
            measures_file=MEASURES_FILE,
            flow_rules_file=FLOW_RULES_FILE,
            measure_costs_file=MEASURE_COSTS_FILE,
        )
        zones = stock_manager.get_zones()
        engine = SimulationEngine(
            stock_manager,
            selection_manager,
            zones,
            zones_file=LDEN_ZONES_FILE,
            measures_file=MEASURES_FILE,
            flow_rules_file=FLOW_RULES_FILE,
            measure_costs_file=MEASURE_COSTS_FILE,
        )
        return engine, selection_manager

    def test_pipeline_matches_wrapper_output(self):
        engine_a, _ = self._build_engine()
        engine_a.run_simulation(BEGINJAAR, EINDJAAR)
        flow_a = pd.DataFrame(engine_a._flow_log_rows).sort_values(
            by=["db_ondergrens", "jaar", "naam_flow", "inflow_stock_name", "outflow_stock_name"]
        )

        engine_b, selection_manager_b = self._build_engine()
        selected = [
            (name, selection_manager_b.get_selected_zones(str(name)))
            for name in selection_manager_b.get_measure_descriptions().index
        ]
        state = engine_b.load_inputs(BEGINJAAR, EINDJAAR, selected)
        state = engine_b.run_simulation_state(state)
        outputs = engine_b.build_outputs(state)
        engine_b.persist_outputs(outputs)
        flow_b = pd.DataFrame(engine_b._flow_log_rows).sort_values(
            by=["db_ondergrens", "jaar", "naam_flow", "inflow_stock_name", "outflow_stock_name"]
        )

        self.assertEqual(len(flow_a), len(flow_b))
        numeric_cols = [
            "flow_rate",
            "orig_future_inflow_stock_value",
            "new_future_inflow_stock_value",
            "delta_inflow",
            "orig_future_outflow_stock_value",
            "new_future_outflow_stock_value",
            "delta_outflow",
        ]
        for col in numeric_cols:
            max_diff = float(
                (flow_a[col].reset_index(drop=True) - flow_b[col].reset_index(drop=True))
                .abs()
                .max()
            )
            self.assertLessEqual(max_diff, 1e-9, f"Mismatch in {col}: {max_diff}")

        self.assertAlmostEqual(engine_a.get_total_costs()[0], engine_b.get_total_costs()[0], places=9)
        self.assertAlmostEqual(engine_a.get_total_costs()[1], engine_b.get_total_costs()[1], places=9)

        zone_log_path = Path(OUTPUT_FLOW_LOG_ZONE_FILE)
        self.assertTrue(zone_log_path.exists())

    def test_growth_flow_mode_increases_same_stock(self):
        engine, _ = self._build_engine()
        state = SimulationState(
            beginjaar=2026,
            eindjaar=2027,
            zones=("A",),
            stock_names=("onbebouwde_bebouwbare_percelen",),
            sim_state=np.array([[[100.0]], [[0.0]]], dtype=float),
            zone_to_idx={"A": 0},
            stock_to_idx={"onbebouwde_bebouwbare_percelen": 0},
            year_to_idx={2026: 0, 2027: 1},
            flow_rules_by_zone={
                "A": [
                    FlowRule(
                        rule_id="growth_rule",
                        measure_id="growth_measure",
                        zone="A",
                        inflow_stock="onbebouwde_bebouwbare_percelen",
                        outflow_stock="onbebouwde_bebouwbare_percelen",
                        flow_rate_baseline=0.1,
                        flow_rate_active=0.2,
                        flow_mode="growth",
                        active=False,
                        cost_stock="-",
                        rel_cost_overheid=0.0,
                        rel_cost_prive=0.0,
                        priority=1,
                    )
                ]
            },
        )

        new_state = engine._run_zone_simulation_state(state)
        result = float(new_state.sim_state[new_state.year_to_idx[2027], 0, 0])
        self.assertAlmostEqual(result, 110.0, places=9)

    def test_regional_ernstig_gehinderden_sum_matches_total(self):
        engine, selection_manager = self._build_engine()
        selected = [
            (name, selection_manager.get_selected_zones(str(name)))
            for name in selection_manager.get_measure_descriptions().index
        ]
        state = engine.load_inputs(BEGINJAAR, EINDJAAR, selected)
        state = engine.run_simulation_state(state)
        engine.persist_outputs(engine.build_outputs(state))

        stock_manager = engine.stock_manager
        for jaar in (BEGINJAAR, EINDJAAR):
            sum_vlaanderen = 0.0
            sum_brussel = 0.0
            for zone in engine.zones:
                vlaanderen = stock_manager.get_aantal(
                    "aantal_ernstig_gehinderden_vlaanderen", jaar, zone
                )
                brussel = stock_manager.get_aantal(
                    "aantal_ernstig_gehinderden_brussel", jaar, zone
                )
                totaal = stock_manager.get_aantal("aantal_ernstig_gehinderden", jaar, zone)
                self.assertAlmostEqual(totaal, vlaanderen + brussel, places=3)
                sum_vlaanderen += vlaanderen
                sum_brussel += brussel
            self.assertGreater(sum_vlaanderen, 0.0)
            self.assertGreater(sum_brussel, 0.0)

    def test_regional_gehinderde_personen_sum_matches_total(self):
        engine, selection_manager = self._build_engine()
        selected = [
            (name, selection_manager.get_selected_zones(str(name)))
            for name in selection_manager.get_measure_descriptions().index
        ]
        state = engine.load_inputs(BEGINJAAR, EINDJAAR, selected)
        state = engine.run_simulation_state(state)
        engine.persist_outputs(engine.build_outputs(state))

        stock_manager = engine.stock_manager
        for jaar in (BEGINJAAR, EINDJAAR):
            for zone in engine.zones:
                vlaanderen = stock_manager.get_aantal(
                    "totaal_gehinderde_personen_vlaanderen", jaar, zone
                )
                brussel = stock_manager.get_aantal(
                    "totaal_gehinderde_personen_brussel", jaar, zone
                )
                totaal = stock_manager.get_aantal("totaal_gehinderde_personen", jaar, zone)
                self.assertAlmostEqual(totaal, vlaanderen + brussel, places=3)

    def test_active_measure_costs_are_finite(self):
        engine, selection_manager = self._build_engine()
        selection_manager.set_selected_zones(
            "aankoopbeleid_niet_geïsoleerde_woningen", ("A",)
        )
        selected = [
            (name, selection_manager.get_selected_zones(str(name)))
            for name in selection_manager.get_measure_descriptions().index
        ]
        state = engine.load_inputs(BEGINJAAR, EINDJAAR, selected)
        state = engine.run_simulation_state(state)
        outputs = engine.build_outputs(state)

        self.assertFalse(np.isnan(outputs.kost_overheid))
        self.assertFalse(np.isnan(outputs.kost_prive))
        self.assertGreater(outputs.kost_overheid, 0.0)
