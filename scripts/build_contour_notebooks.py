"""Generate contour_data.ipynb, contour_data_vlaanderen.ipynb and contour_flows.ipynb."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _cell(cell_type: str, source: str, **meta) -> dict:
    cell = {"cell_type": cell_type, "metadata": meta, "source": source.splitlines(keepends=True)}
    if cell_type == "code":
        cell["outputs"] = []
        cell["execution_count"] = None
    return cell


def build_data_notebook() -> dict:
    from contour.data_notebook import (
        DATA_SETUP_CODE,
        DATA_STAP_VOLGORDE,
        stap_definitie,
        stap_grafiek_code,
        stap_notebook_code,
        _md,
    )

    cells = [
        _cell(
            "markdown",
            "# Contour data â€” laden en consolidatie\n\n"
            "Dit notebook laadt alle bronnen uit `data/`, bouwt **`lden` / `lnight` stap voor stap** "
            "(FLOW Â§2, 27 variabelen per `db_ondergrens`) en schrijft parquet naar `output/intermediate/`.\n\n"
            "Referentie: [STOCKS_EN_FLOWS_BEREKENEN.md Â§2](../STOCKS_EN_FLOWS_BEREKENEN.md).",
        ),
        _cell("markdown", "## Deel A â€” Data-inventaris (FLOW Â§2)"),
        _cell(
            "code",
            "from contour.inventory import maak_data_inventory\n\n"
            "df_data_inventory = maak_data_inventory()\n"
            "df_data_inventory",
        ),
        _cell(
            "markdown",
            "## Deel B â€” Laden ruwe bronnen\n\n"
            "Overzicht van ruwe bestanden vÃ³Ã³r consolidatie naar contourbanden.",
        ),
        _cell(
            "code",
            "from contour.loaders import (\n"
            "    lees_contour_vlaanderen,\n"
            "    lees_brussel_sector,\n"
            "    lees_vergunningen,\n"
            "    lees_transacties,\n"
            ")\n\n"
            "raw_vlaanderen_lden, raw_vlaanderen_lnight = lees_contour_vlaanderen()\n"
            "raw_brussel_lden, raw_brussel_lnight = lees_brussel_sector()\n"
            "vergunningen_omgevingsloket, kwetsbare, verkaveling = lees_vergunningen()\n"
            "transacties = lees_transacties()\n\n"
            "print('Vlaanderen lden:', raw_vlaanderen_lden.shape)\n"
            "print('Brussel lden:', raw_brussel_lden.shape)\n"
            "print('Vergunningen omg:', len(vergunningen_omgevingsloket))\n"
            "print('Transacties:', len(transacties))",
        ),
        _cell(
            "markdown",
            "## Deel B2 â€” Traceerbare opbouw `lden` / `lnight`\n\n"
            "Elke kolom uit FLOW Â§2.0 krijgt **Ã©Ã©n eigen stap**: documentatie + expliciete code "
            "die `lden[â€¦]` en `lnight[â€¦]` vult.\n\n"
            "- **Stap 0**: alleen index `db_ondergrens`\n"
            "- **Stappen 1â€“27**: Ã©Ã©n variabele per stap\n"
            "- **Stap 28**: kolomvolgorde FLOW + schema-check\n\n"
            "Onder elke stap: **staafdiagram** met verdeling over alle dB-banden (lden Â± lnight).",
        ),
        _cell("code", DATA_SETUP_CODE),
    ]

    for stap_id in DATA_STAP_VOLGORDE:
        if stap_id == "vergunde_wooneenheden_nieuwbouw":
            from contour.vergunningen import VERGUNNINGEN_GEMIDDELDE_MD

            cells.append(_cell("markdown", VERGUNNINGEN_GEMIDDELDE_MD))
        info = stap_definitie(stap_id)
        cells.append(_cell("markdown", _md(info)))
        cells.append(_cell("code", stap_notebook_code(stap_id)))
        cells.append(_cell("code", stap_grafiek_code(stap_id)))

    cells.extend(
        [
            _cell(
                "markdown",
                "## Deel C â€” Export parquet + validatie\n\n"
                "Schrijft het eindresultaat uit Deel B2 naar `output/intermediate/` "
                "en vergelijkt met de volledige pipeline.",
            ),
            _cell(
                "code",
                "from pathlib import Path\n"
                "from contour.pipeline import run_data_pipeline, validatie_consolidatie\n\n"
                "INTERMEDIATE = Path('output/intermediate')\n"
                "lden.to_parquet(INTERMEDIATE / 'lden.parquet')\n"
                "lnight.to_parquet(INTERMEDIATE / 'lnight.parquet')\n"
                "print('Geschreven:', INTERMEDIATE / 'lden.parquet')\n"
                "lden.describe()",
            ),
            _cell(
                "code",
                "tables = run_data_pipeline()\n"
                "checks = validatie_consolidatie(tables)\n"
                "checks",
            ),
            _cell(
                "markdown",
                "**Waarschuwing:** vergunningsdata = Vlaamse ringgemeenten; tellers = **jaarlijks gemiddelde 2020â€“2025** "
                "(niet Ã©Ã©n enkel jaar). "
                "Brusselse conversietabel dekt andere gemeenten â†’ deel niet toewijsbaar "
                "(zie `vergunningen_niet_toewijsbaar.parquet`).\n\n"
                "Flow rates: [`contour_flows.ipynb`](contour_flows.ipynb).",
            ),
        ]
    )

    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "cells": cells,
    }


def _flow_stap_cells(measure_id: str) -> list[dict]:
    from contour.flows_per_contour import stap_definitie, stap_notebook_code

    info = stap_definitie(measure_id)
    variabelen = "\n".join(f"- `{v}`" for v in info.variabelen) or "- Geen (vaste waarde of geen effect)"
    stock = f"### Stock-flow\n\n`{info.stock_flow}`\n\n" if info.stock_flow else ""
    aannames = f"### Aannames\n\n{info.aannames}\n\n" if info.aannames else ""
    md = (
        f"## {info.titel}\n\n"
        f"### Uitleg\n\n{info.uitleg}\n\n"
        f"{stock}"
        f"### Berekening\n\n"
        f"- **Baseline:** `{info.formule_baseline}`\n"
        f"- **Active:** `{info.formule_active}`\n\n"
        f"{aannames}"
        f"### Gebruikte variabelen\n\n{variabelen}"
    )
    code = stap_notebook_code(measure_id)
    return [_cell("markdown", md), _cell("code", code)]


def build_data_vlaanderen_notebook() -> dict:
    from contour.data_notebook import DATA_STAP_VOLGORDE
    from contour.data_notebook_vlaanderen import (
        VLAANDEREN_SETUP_CODE,
        md_vla,
        stap_definitie_vla,
        stap_grafiek_code_vla,
        stap_notebook_code_vla,
    )

    cells = [
        _cell(
            "markdown",
            "# Contour data â€” Vlaanderen\n\n"
            "Stap-voor-stap opbouw van **27 FLOW-variabelen** per `db_ondergrens`, "
            "alleen voor **Vlaanderen** (geen Brussel).\n\n"
            "EÃ©n tabel `vla` (index = dB-band 45â€“74). Onder elke stap: expliciete berekening + staafdiagram.\n\n"
            "Referentie: [STOCKS_EN_FLOWS_BEREKENEN.md Â§2](../STOCKS_EN_FLOWS_BEREKENEN.md).\n\n"
            "Gecombineerd Vlaanderen+Brussel: [`contour_data.ipynb`](contour_data.ipynb).",
        ),
        _cell(
            "markdown",
            "## Deel A â€” Data-inventaris (Vlaanderen-relevant)",
        ),
        _cell(
            "code",
            "from contour.inventory import maak_data_inventory\n\n"
            "inv = maak_data_inventory()\n"
            "inv[inv['bestand'].str.contains('vlaanderen|vergunning|transactie', case=False, na=False)]",
        ),
        _cell(
            "markdown",
            "## Deel B â€” Laden ruwe bronnen (Vlaanderen)",
        ),
        _cell(
            "code",
            "from contour.loaders import lees_contour_vlaanderen, lees_vergunningen, lees_transacties\n\n"
            "raw_vla_lden, raw_vla_lnight = lees_contour_vlaanderen()\n"
            "verg_omg, verg_kwets, verg_verk = lees_vergunningen()\n"
            "transacties = lees_transacties()\n\n"
            "print('Vlaanderen lden:', raw_vla_lden.shape)\n"
            "print('Vergunningen omg:', len(verg_omg))\n"
            "print('Transacties:', len(transacties))",
        ),
        _cell(
            "markdown",
            "## Deel C â€” Traceerbare opbouw `vla`\n\n"
            "Elke FLOW-kolom krijgt **Ã©Ã©n eigen stap** met documentatie, expliciete code en grafiek.\n\n"
            "- **Stap 0**: index `db_ondergrens`\n"
            "- **Stappen 1â€“27**: Ã©Ã©n variabele per stap\n"
            "- **Stap 28**: kolomvolgorde FLOW + schema-check",
        ),
        _cell("code", VLAANDEREN_SETUP_CODE),
    ]

    for stap_id in DATA_STAP_VOLGORDE:
        if stap_id == "vergunde_wooneenheden_nieuwbouw":
            from contour.vergunningen import VERGUNNINGEN_GEMIDDELDE_MD

            cells.append(_cell("markdown", VERGUNNINGEN_GEMIDDELDE_MD))
        info = stap_definitie_vla(stap_id)
        cells.append(_cell("markdown", md_vla(info)))
        cells.append(_cell("code", stap_notebook_code_vla(stap_id)))
        cells.append(_cell("code", stap_grafiek_code_vla(stap_id)))

    cells.extend(
        [
            _cell(
                "markdown",
                "## Deel D â€” Export parquet\n\n"
                "Schrijft het eindresultaat naar `output/intermediate/vlaanderen_lden.parquet`.",
            ),
            _cell(
                "code",
                "from pathlib import Path\n\n"
                "INTERMEDIATE = Path('output/intermediate')\n"
                "INTERMEDIATE.mkdir(parents=True, exist_ok=True)\n"
                "vla.to_parquet(INTERMEDIATE / 'vlaanderen_lden.parquet')\n"
                "print('Geschreven:', INTERMEDIATE / 'vlaanderen_lden.parquet')\n"
                "vla.describe()",
            ),
            _cell(
                "markdown",
                "**Beperkingen Vlaanderen-only:**\n\n"
                "- Vergunningen = Vlaamse ringgemeenten; tellers = **jaarlijks gemiddelde 2020â€“2025**.\n"
                "- `onbebouwde_*` percelen = placeholder 0 (geen stockdata).\n"
                "- Isolatiesplit woningen = 80/20 placeholder.\n\n"
                "Flow rates: [`contour_flows.ipynb`](contour_flows.ipynb).",
            ),
        ]
    )

    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "cells": cells,
    }


def build_flows_notebook() -> dict:
    from contour.flows_per_contour import FLOW_STAP_VOLGORDE

    cells = [
        _cell(
            "markdown",
            "# Contour flows â€” flow rates per dB-band\n\n"
            "Leest parquet uit `output/intermediate/` (gegenereerd door `contour_data.ipynb`).\n\n"
            "Elke maatregel krijgt **twee kolommen** in `lden_flows`: `{measure}_baseline` en `{measure}_active`, "
            "berekend **per `db_ondergrens`** uit kolommen van `lden_vars`.\n\n"
            "Referentie: [STOCKS_EN_FLOWS_BEREKENEN.md Â§4](../STOCKS_EN_FLOWS_BEREKENEN.md) + `contour/flows_per_contour.py`.",
        ),
        _cell(
            "code",
            "from pathlib import Path\n"
            "import pandas as pd\n\n"
            "INTERMEDIATE = Path('output/intermediate')\n"
            "contour_lden = pd.read_parquet(INTERMEDIATE / 'lden.parquet')\n"
            "vergunningen_contour = pd.read_parquet(INTERMEDIATE / 'vergunningen_contour.parquet')\n"
            "transacties_capakey = pd.read_parquet(INTERMEDIATE / 'transacties_capakey.parquet')",
        ),
        _cell(
            "markdown",
            "## Deel A â€” Variabelen per band (`lden_vars`)\n\n"
            "Alle FLOW-kolommen uit `lden.parquet`, index = `db_ondergrens`.",
        ),
        _cell(
            "code",
            "from contour.flows_per_contour import lden_vars_bereiden\n\n"
            "lden_vars = lden_vars_bereiden(contour_lden)\n"
            "lden_flows = pd.DataFrame(index=lden_vars.index)\n"
            "lden_vars.head()",
        ),
        _cell(
            "markdown",
            "## Deel B â€” Flow rates stap voor stap (FLOW Â§3)\n\n"
            "Elke stap schrijft expliciet `{measure}_baseline` en `{measure}_active` "
            "uit kolommen van `lden_vars` (teller / noemer, veilig bij noemer 0).",
        ),
    ]

    for measure_id in FLOW_STAP_VOLGORDE:
        cells.extend(_flow_stap_cells(measure_id))

    cells.extend(
        [
            _cell(
                "markdown",
                "## Deel C â€” Overzicht en aggregatie\n\n"
                "Volledige `lden_flows` per band + gewogen gemiddelde voor `flow_rules.csv`.",
            ),
            _cell(
                "code",
                "from contour.flows_per_contour import lden_flows_met_metadata, aggregeer_naar_flow_rules\n"
                "from contour.flows import valideer_flow_rates\n\n"
                "lden_flows_export = lden_flows_met_metadata(lden_vars, lden_flows)\n"
                "flow_rates = aggregeer_naar_flow_rules(lden_vars, lden_flows)\n"
                "validatie = valideer_flow_rates(flow_rates)\n"
                "lden_flows_export.head()",
            ),
            _cell("code", "flow_rates"),
            _cell("markdown", "## Deel D â€” Export naar dashboard-inputs"),
            _cell(
                "code",
                "from contour.export import export_lden_contour, export_lnight_contour, update_flow_rules_rates\n\n"
                "contour_lnight = pd.read_parquet(INTERMEDIATE / 'lnight.parquet')\n"
                "export_lden_contour(contour_lden)\n"
                "export_lnight_contour(contour_lnight)\n"
                "update_flow_rules_rates(flow_rates)\n"
                "lden_flows_export.to_parquet(INTERMEDIATE / 'lden_flows.parquet', index=False)\n"
                "flow_rates.to_parquet(INTERMEDIATE / 'flow_rates.parquet', index=False)\n"
                "validatie",
            ),
        ]
    )

    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "cells": cells,
    }


def main() -> None:
    for naam, builder in [
        ("contour_data.ipynb", build_data_notebook),
        ("contour_data_vlaanderen.ipynb", build_data_vlaanderen_notebook),
        ("contour_flows.ipynb", build_flows_notebook),
    ]:
        pad = ROOT / naam
        pad.write_text(json.dumps(builder(), indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"geschreven: {pad}")


if __name__ == "__main__":
    main()
