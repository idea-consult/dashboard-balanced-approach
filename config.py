"""Configuration constants for the simulation application."""

import os

# Authentication
ACCESS_CODE = os.getenv("ACCESS_CODE", "code")

# Simulation parameters
BEGINJAAR = 2026
LOOPTIJD = 5  # in jaren
EINDJAAR = BEGINJAAR + LOOPTIJD

# Zones
ZONES = ("A", "B", "C", "D")

# Conversion factors
PERSONEN_PER_WOONUNIT = 2
WOON_UNITS_PER_KLEINSCHALIGE_WONING = 1.2
WOON_UNITS_PER_GROOTSCHALIGE_WONING = 60

# File paths
INPUT_DIR = "input"
OUTPUT_DIR = "output"
STOCK_FILE = f"{INPUT_DIR}/20260302_stocks.csv"
FLOW_FILE = f"{INPUT_DIR}/20260302_flows.csv"
BESCHRIJVING_MAATREGELEN_FILE = f"{INPUT_DIR}/beschrijving_maatregelen.csv"
OUTPUT_STOCK_FILE = f"{OUTPUT_DIR}/stock.csv"
