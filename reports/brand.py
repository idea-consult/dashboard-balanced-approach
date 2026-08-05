"""IDEA Consult brand tokens for PDF reports and dashboard charts."""

from __future__ import annotations

from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = REPORTS_DIR.parent
ASSETS_DIR = REPORTS_DIR / "assets"
TEMPLATES_DIR = REPORTS_DIR / "templates"
RESOURCES_DIR = PROJECT_ROOT / "resources"
LOGO_PATH = ASSETS_DIR / "ideaconsultlogo.png"
CONTOUR_MAP_PATH = RESOURCES_DIR / "kaart contouren.png"
APTOS_FONT_PATHS = (
    RESOURCES_DIR / "Aptos.ttf",
    RESOURCES_DIR / "Aptos-Bold.ttf",
)

# Primary UI/chart font (TTF's in resources/). Cross-platform via vl-convert + CSS.
CHART_FONT = "Aptos"

_VL_FONTS_REGISTERED = False


def register_vl_convert_fonts() -> None:
    """Register bundled Aptos fonts for Altair/vl-convert PNG export (e.g. on Render)."""
    global _VL_FONTS_REGISTERED
    if _VL_FONTS_REGISTERED:
        return
    try:
        import vl_convert as vlc
    except ImportError:
        return
    if RESOURCES_DIR.is_dir():
        vlc.register_font_directory(str(RESOURCES_DIR))
    _VL_FONTS_REGISTERED = True

# Dashboard chart colours (ui/components.py)
COLOR_PURPLE = "#4E2567"
COLOR_PURPLE_LIGHT = "#A68BB8"
COLOR_RED = "#DD5B61"
COLOR_RED_LIGHT = "#F0A8AC"
COLOR_TEXT = "#333333"

# Expliciete zonekleuren voor stock-lijngrafieken (6 zones; theme heeft maar 5 categoriekleuren).
ZONE_CHART_DOMAIN = ("A", "B", "C", "D", "E", "F")
ZONE_CHART_RANGE = (
    "#9B4F96",  # A — violet (niet #4E2567, anders identiek aan F)
    COLOR_RED,  # B
    "#EB914D",  # C
    "#36A3C9",  # D
    "#00989A",  # E
    COLOR_PURPLE,  # F
)

OPDRACHTREGEL = (
    "Gemaakt door IDEA Consult in opdracht van het "
    "Departement Omgeving van Vlaanderen"
)

REPORT_TITLE = "Balanced Approach — simulatierapport"
