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
LDEN_ZONES_FILE = f"{INPUT_DIR}/lden_zones.csv"
LNIGHT_ZONES_FILE = f"{INPUT_DIR}/lnight_zones.csv"
# Default zones file (Lden)
ZONES_FILE = LDEN_ZONES_FILE
OUTPUT_STOCK_FILE = f"{OUTPUT_DIR}/stock.csv"
OUTPUT_FLOW_LOG_ZONE_FILE = f"{OUTPUT_DIR}/flow_log_zone.csv"
