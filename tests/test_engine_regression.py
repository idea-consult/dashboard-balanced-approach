"""Regression tests for SimulationEngine pipeline outputs."""

import unittest
from pathlib import Path
import pandas as pd

from config import (
    BEGINJAAR,
    EINDJAAR,
    MEASURES_FILE,
    FLOW_RULES_FILE,
    MEASURE_COSTS_FILE,
    LDEN_CONTOUR_FILE,
    LDEN_ZONES_FILE,
    OUTPUT_FLOW_LOG_ZONE_FILE,
)
from models.stock_manager import StockManager
from models.measure_selection_manager import MeasureSelectionManager
from simulation.engine import SimulationEngine


class TestEngineRegression(unittest.TestCase):
    """Ensure split pipeline and wrapper produce stable outputs."""

    def _build_engine(self) -> tuple[SimulationEngine, MeasureSelectionManager]:
        stock_manager = StockManager(LDEN_CONTOUR_FILE, LDEN_ZONES_FILE, BEGINJAAR)
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
            by=["zone", "jaar", "naam_flow", "inflow_stock_name", "outflow_stock_name"]
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
            by=["zone", "jaar", "naam_flow", "inflow_stock_name", "outflow_stock_name"]
        )

        self.assertEqual(len(flow_a), len(flow_b))
        numeric_cols = [
            "inflow_relative",
            "outflow_relative",
            "orig_future_inflow_stock_value",
            "new_future_inflow_stock_value",
            "delta_inflow",
            "orig_future_outflow_stock_value",
            "new_future_outflow_stock_value",
            "delta_outflow",
        ]
        for col in numeric_cols:
            max_diff = float((flow_a[col].reset_index(drop=True) - flow_b[col].reset_index(drop=True)).abs().max())
            self.assertLessEqual(max_diff, 1e-9, f"Mismatch in {col}: {max_diff}")

        self.assertAlmostEqual(engine_a.get_total_costs()[0], engine_b.get_total_costs()[0], places=9)
        self.assertAlmostEqual(engine_a.get_total_costs()[1], engine_b.get_total_costs()[1], places=9)

        zone_log_path = Path(OUTPUT_FLOW_LOG_ZONE_FILE)
        self.assertTrue(zone_log_path.exists())

