"""Core simulation state and typed flow definitions."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import numpy as np


@dataclass(frozen=True)
class FlowRule:
    """Explicit rule used by the simulation core."""

    rule_id: str
    measure_id: str
    zone: str
    inflow_stock: str
    outflow_stock: str
    inflow_rate_baseline: float
    outflow_rate_baseline: float
    inflow_rate_active: float
    outflow_rate_active: float
    active: bool
    cost_stock: str
    rel_cost_overheid: float
    rel_cost_prive: float
    priority: int = 100


@dataclass
class SimulationState:
    """Single source of truth for simulation internals."""

    beginjaar: int
    eindjaar: int
    zones: Tuple[str, ...]
    stock_names: Tuple[str, ...]
    sim_state: np.ndarray
    zone_to_idx: Dict[str, int]
    stock_to_idx: Dict[str, int]
    year_to_idx: Dict[int, int]
    flow_rules_by_zone: Dict[str, List[FlowRule]]
    flow_log_rows: List[Dict[str, object]] = field(default_factory=list)
    totale_kost_overheid: float = 0.0
    totale_kost_prive: float = 0.0
    timings: Dict[str, float] = field(default_factory=dict)


@dataclass
class SimulationOutputs:
    """Output bundle produced after simulation run."""

    flow_log_rows: List[Dict[str, object]]
    kost_overheid: float
    kost_prive: float
    sim_state: np.ndarray
    zones: Tuple[str, ...]
    stock_names: Tuple[str, ...]
    beginjaar: int
    eindjaar: int
