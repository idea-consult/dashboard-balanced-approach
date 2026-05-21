"""Number formatting for the Streamlit dashboard (Belgian/Dutch style)."""

from __future__ import annotations

import math
from typing import Union

Number = Union[int, float]

# Vega-Lite / Altair: requires numberFormatLocale in idea_consult_altair_theme.
ALTAIR_INTEGER_FORMAT = ",.0f"
ALTAIR_DECIMAL_FORMAT = ",.2f"
ALTAIR_EURO_FORMAT = "$,.2f"


def format_number(value: Number, *, decimals: int = 2) -> str:
    """Format a number as 1.000.000,00 (dot thousands, comma decimals)."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""

    num = float(value)
    sign = "-" if num < 0 else ""
    num = abs(num)

    if decimals == 0:
        int_part = int(round(num))
        grouped = f"{int_part:,}".replace(",", ".")
        return f"{sign}{grouped}"

    formatted = f"{num:,.{decimals}f}"
    integer, _, fraction = formatted.partition(".")
    grouped = integer.replace(",", ".")
    return f"{sign}{grouped},{fraction}"


def format_integer(value: Number) -> str:
    """Format a whole number as 1.000.000 (no decimals)."""
    return format_number(value, decimals=0)


def format_euro(value: Number) -> str:
    """Format a monetary value as € 1.000.000,00."""
    return f"€ {format_number(value)}"


def format_percent(value: Number, *, decimals: int = 0) -> str:
    """Format a percentage with Dutch number style, e.g. 12,5 %."""
    return f"{format_number(value, decimals=decimals)} %"
