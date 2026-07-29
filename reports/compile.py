"""Compile the Typst simulation PDF."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from models.measure_selection_manager import MeasureSelectionManager
from models.scenario_manager import NONE_SCENARIO_ID, NONE_SCENARIO_LABEL
from models.stock_manager import StockManager
from reports.brand import APTOS_FONT_PATHS, LOGO_PATH, RESOURCES_DIR, TEMPLATES_DIR
from reports.charts import export_report_charts
from reports.context import build_report_context


def compile_simulation_report(
    *,
    stock_manager: StockManager,
    measure_selection_manager: MeasureSelectionManager,
    kost_overheid: float,
    kost_prive: float,
    scenario_id: str | None = None,
    scenario_label: str | None = None,
) -> bytes:
    """Build chart PNGs + JSON context and compile Typst to PDF bytes."""
    try:
        import typst
    except ImportError as exc:
        raise ImportError(
            "Het pakket 'typst' is niet geïnstalleerd. "
            "Voeg typst toe aan de deployment-dependencies om PDF-rapporten te genereren."
        ) from exc

    template_src = TEMPLATES_DIR / "simulatierapport.typ"
    if not template_src.exists():
        raise FileNotFoundError(f"Typst-template ontbreekt: {template_src}")
    if not LOGO_PATH.exists():
        raise FileNotFoundError(f"Logo ontbreekt: {LOGO_PATH}")
    missing_fonts = [p for p in APTOS_FONT_PATHS if not p.exists()]
    if missing_fonts:
        raise FileNotFoundError(
            "Aptos-fonts ontbreken in resources/: "
            + ", ".join(p.name for p in missing_fonts)
        )

    with tempfile.TemporaryDirectory(prefix="ba_report_") as tmp:
        root = Path(tmp)
        figures_dir = root / "figures"
        figures = export_report_charts(stock_manager, figures_dir)

        ctx = build_report_context(
            stock_manager=stock_manager,
            measure_selection_manager=measure_selection_manager,
            kost_overheid=kost_overheid,
            kost_prive=kost_prive,
            scenario_id=scenario_id or NONE_SCENARIO_ID,
            scenario_label=scenario_label or NONE_SCENARIO_LABEL,
            figures=figures,
        )
        (root / "data.json").write_text(
            json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        shutil.copy2(LOGO_PATH, root / "logo.png")
        shutil.copy2(template_src, root / "simulatierapport.typ")

        pdf: Any = typst.compile(
            root / "simulatierapport.typ",
            root=root,
            font_paths=[str(RESOURCES_DIR)],
        )
        if isinstance(pdf, (bytes, bytearray)):
            return bytes(pdf)
        return Path(pdf).read_bytes()
