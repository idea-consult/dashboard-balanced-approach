"""Optionele kunstmatige vertraging en spinners voor demo / latere snelheidsvergelijking."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Iterator

import streamlit as st

from config import ARTIFICIAL_DELAY_ENABLED, ARTIFICIAL_DELAY_STAGES

STAGE_SPINNER_LABELS = {
    "init": "Data laden…",
    "simulation": "Simulatie uitvoeren…",
    "leefbaarheidspunten": "Leefbaarheidspunten berekenen…",
    "render": "Resultaten tonen…",
    "save": "Resultaten opslaan…",
}


def artificial_delay(stage: str) -> None:
    """
    Pauzeer kort op een vaste stap in de app-run.

    Zet ARTIFICIAL_DELAY_ENABLED=false of per-stap seconden op 0 voor productie/snelle modus.
    """
    if not ARTIFICIAL_DELAY_ENABLED:
        return

    seconds = float(ARTIFICIAL_DELAY_STAGES.get(stage, 0.0))
    if seconds <= 0:
        return

    if os.getenv("PRINT_TIMINGS", "false").strip().lower() == "true":
        print(f"[DELAY] {stage}: {seconds * 1000:.0f} ms")

    time.sleep(seconds)


@contextmanager
def spinner_step(stage: str) -> Iterator[None]:
    """Toon een Streamlit-spinner tijdens een stap (inclusief optionele vertraging)."""
    label = STAGE_SPINNER_LABELS.get(stage, "Bezig…")
    with st.spinner(label):
        artificial_delay(stage)
        yield
