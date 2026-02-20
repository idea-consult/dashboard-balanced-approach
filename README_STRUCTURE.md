# Code Structure Documentation

This document describes the refactored structure of the simulation application.

## Overview

The application has been restructured into a modular architecture with clear separation of concerns:

- **Configuration**: Centralized constants and settings
- **Models**: Data management classes for stocks and flows
- **Simulation**: Business logic for year-by-year calculations
- **UI**: Streamlit interface components

## Directory Structure

```
.
├── app.py                      # Main Streamlit application entry point
├── config.py                   # Configuration constants
├── calculations.py            # Original file (kept for reference)
│
├── models/                    # Data models
│   ├── __init__.py
│   ├── stock_manager.py       # Manages stock data operations
│   └── flow_manager.py        # Manages flow data and measures
│
├── simulation/                # Simulation logic
│   ├── __init__.py
│   ├── engine.py             # Main simulation engine
│   └── calculators.py        # Calculation helper functions
│
├── ui/                        # UI components
│   ├── __init__.py
│   ├── auth.py               # Authentication logic
│   └── components.py         # Streamlit UI components
│
└── util/                      # Utility functions
    └── helpers.py            # Helper functions (existing)
```

## Module Descriptions

### `config.py`
Centralized configuration for:
- Authentication settings
- Simulation parameters (beginjaar, looptijd, eindjaar)
- Zones
- Conversion factors
- File paths

### `models/stock_manager.py`
`StockManager` class for managing stock data:
- `get_aantal(naam, jaar, zone)`: Get stock value
- `set_aantal(naam, jaar, zone, aantal)`: Set stock value
- `save(output_file)`: Save stock data to CSV
- `get_dataframe()`: Get underlying DataFrame

### `models/flow_manager.py`
`FlowManager` class for managing flow data and measures:
- `get_flow(naam, zone)`: Get flow value (considers if measure is applied)
- `get_selected_zones(maatregel_naam)`: Get zones where measure is applied
- `set_selected_zones(maatregel_naam, selected_zones)`: Set measure zones
- `get_total_cost()`: Get total cost of applied measures
- `is_measure_applied(naam, zone)`: Check if measure is applied

### `simulation/engine.py`
`SimulationEngine` class for running simulations:
- `run_simulation(beginjaar, eindjaar)`: Main simulation loop
- `_simulate_year_zone(jaar, zone)`: Simulate one year for one zone
- `_simulate_parcels(jaar, zone)`: Calculate parcel stock changes
- `_simulate_houses(jaar, zone)`: Calculate house stock changes
- `_calculate_derived_metrics(jaar, zone)`: Calculate derived metrics

### `simulation/calculators.py`
Helper functions for calculations:
- `calculate_initial_metrics()`: Calculate initial year metrics
- `calculate_totals()`: Calculate totals across zones

### `ui/auth.py`
Authentication module:
- `check_password()`: Check user authentication

### `ui/components.py`
UI rendering functions:
- `render_sidebar_controls()`: Render measure selection sidebar
- `render_metrics()`: Render key metrics
- `render_total_cost()`: Render total cost metric
- `render_charts()`: Render visualization charts

### `app.py`
Main application entry point that:
1. Handles authentication
2. Initializes managers
3. Renders sidebar controls
4. Runs simulation
5. Saves results
6. Renders UI

## Benefits of This Structure

1. **Separation of Concerns**: Each module has a single, clear responsibility
2. **Easier Testing**: Individual components can be tested in isolation
3. **Maintainability**: Changes to one area don't affect others
4. **Extensibility**: Easy to add new stocks, flows, or UI components
5. **Reusability**: Components can be reused in different contexts
6. **Readability**: Clear structure makes code easier to understand

## Adding New Features

### Adding a New Stock
1. Add initial data to `input/stock.csv`
2. Add calculation logic in `simulation/engine.py` if needed
3. Add UI display in `ui/components.py` if needed

### Adding a New Flow/Measure
1. Add data to `input/flow.csv` and `input/beschrijving_maatregelen.csv`
2. Add flow logic in `simulation/engine.py` methods
3. UI will automatically pick up new measures from CSV files

### Adding a New Calculation
1. Add helper function in `simulation/calculators.py` or `util/helpers.py`
2. Call from `simulation/engine.py` as needed
3. Add UI display in `ui/components.py` if needed

## Migration Notes

The original `calculations.py` file is kept for reference. The new `app.py` replaces it and provides the same functionality with improved structure.
