"""Configuration constants for the simulation application."""

import os

# Authentication
ACCESS_CODE = os.getenv("ACCESS_CODE", "code")

# Simulation parameters
BEGINJAAR = 2026
LOOPTIJD = 5  # in jaren
EINDJAAR = BEGINJAAR + LOOPTIJD

# Conversion factors
PERSONEN_PER_WOONUNIT = 2
WOON_UNITS_PER_KLEINSCHALIGE_WONING = 1.2
WOON_UNITS_PER_GROOTSCHALIGE_WONING = 60

# File paths
INPUT_DIR = "input"
OUTPUT_DIR = "output"
MEASURES_FILE = f"{INPUT_DIR}/measures.csv"
FLOW_RULES_FILE = f"{INPUT_DIR}/flow_rules.csv"
MEASURE_COSTS_FILE = f"{INPUT_DIR}/measure_costs.csv"
LDEN_CONTOUR_FILE = f"{INPUT_DIR}/lden_contour.csv"
LNIGHT_CONTOUR_FILE = f"{INPUT_DIR}/lnight_contour.csv"
LDEN_CONTOUR_REGIONAL_FILE = f"{INPUT_DIR}/lden_contour_regional.csv"
LNIGHT_CONTOUR_REGIONAL_FILE = f"{INPUT_DIR}/lnight_contour_regional.csv"
LDEN_ZONES_FILE = f"{INPUT_DIR}/lden_zones.csv"
LNIGHT_ZONES_FILE = f"{INPUT_DIR}/lnight_zones.csv"
STOCKS_FILE = f"{INPUT_DIR}/stocks.csv"
FLOW_SIZE_FILE = f"{INPUT_DIR}/flow_size.csv"
STOCK_PRICES_FILE = f"{INPUT_DIR}/stock_prices.csv"
# Default zones file (Lden)
ZONES_FILE = LDEN_ZONES_FILE
OUTPUT_STOCK_FILE = f"{OUTPUT_DIR}/stock.csv"
OUTPUT_FLOW_LOG_ZONE_FILE = f"{OUTPUT_DIR}/flow_log_zone.csv"

# Kunstmatige vertraging (demo): zet ARTIFICIAL_DELAY_ENABLED=false voor snelle modus
ARTIFICIAL_DELAY_ENABLED = (
    os.getenv("ARTIFICIAL_DELAY_ENABLED", "true").strip().lower() == "true"
)


def _delay_seconds(env_name: str, default: float) -> float:
    raw = os.getenv(env_name, str(default)).strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return max(0.0, default)


ARTIFICIAL_DELAY_STAGES = {
    "init": _delay_seconds("ARTIFICIAL_DELAY_INIT_S", 0.69),
    "simulation": _delay_seconds("ARTIFICIAL_DELAY_SIMULATION_S", 6.3),
    "leefbaarheidspunten": _delay_seconds("ARTIFICIAL_DELAY_LEEFBAARHEIDSPUNTEN_S", 0.9),
    "render": _delay_seconds("ARTIFICIAL_DELAY_RENDER_S", 1.6),
    "save": _delay_seconds("ARTIFICIAL_DELAY_SAVE_S", 0.3),
}
