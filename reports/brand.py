"""IDEA Consult brand tokens for PDF reports."""

from __future__ import annotations

from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = REPORTS_DIR.parent
ASSETS_DIR = REPORTS_DIR / "assets"
TEMPLATES_DIR = REPORTS_DIR / "templates"
RESOURCES_DIR = PROJECT_ROOT / "resources"
LOGO_PATH = ASSETS_DIR / "ideaconsultlogo.png"
APTOS_FONT_PATHS = (
    RESOURCES_DIR / "Aptos.ttf",
    RESOURCES_DIR / "Aptos-Bold.ttf",
)

# Dashboard chart colours (ui/components.py)
COLOR_PURPLE = "#4E2567"
COLOR_PURPLE_LIGHT = "#A68BB8"
COLOR_RED = "#DD5B61"
COLOR_RED_LIGHT = "#F0A8AC"
COLOR_TEXT = "#333333"

OPDRACHTREGEL = (
    "Gemaakt door IDEA Consult in opdracht van het "
    "Departement Omgeving van Vlaanderen"
)

REPORT_TITLE = "Balanced Approach — simulatierapport"
