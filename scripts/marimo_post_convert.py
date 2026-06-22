"""Post-process contour_data.py after marimo convert."""
import re
from pathlib import Path


def _patch_params(params: str) -> str:
    state = "lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen"
    parts = [p.strip() for p in params.split(",") if p.strip()]
    drop = {"lden", "lnight", "vorige_kolommen", "_vorige"}
    parts = [p for p in parts if p not in drop]
    return state + (", " + ", ".join(parts) if parts else "")


path = Path("contour_data.py")
text = path.read_text(encoding="utf-8")

STATE_CELL = '''

@app.cell
def _(mo):
    """Gedeelde B2-state (marimo: één definitie per variabele)."""
    lden_b2, set_lden_b2 = mo.state(None)
    lnight_b2, set_lnight_b2 = mo.state(None)
    vorige_kolommen, set_vorige_kolommen = mo.state(None)
    return (
        lden_b2,
        lnight_b2,
        set_lden_b2,
        set_lnight_b2,
        set_vorige_kolommen,
        vorige_kolommen,
    )

'''

text = text.replace(
    '@app.cell(hide_code=True)\ndef _(mo):\n    mo.md(r"""\n    ### Stap 0 — Index',
    STATE_CELL + '@app.cell(hide_code=True)\ndef _(mo):\n    mo.md(r"""\n    ### Stap 0 — Index',
    1,
)

# Stap 0 — init state (geen lden_b2 inlezen)
text = re.sub(
    r"@app\.cell\ndef _\(\n    init_lden_lnight_index,\n    raw_vlaanderen_lden_1,\n    raw_vlaanderen_lnight_1,\n    toon_stap,\n\):\n"
    r"    lden, lnight = init_lden_lnight_index\(raw_vlaanderen_lden_1, raw_vlaanderen_lnight_1\)\n"
    r"    _vorige = toon_stap\('0 index', lden, lnight\)\n"
    r"    list\(lden\.columns\)\n"
    r"    return lden, lnight\n",
    "@app.cell\ndef _(\n"
    "    init_lden_lnight_index,\n"
    "    raw_vlaanderen_lden_1,\n"
    "    raw_vlaanderen_lnight_1,\n"
    "    set_lden_b2,\n"
    "    set_lnight_b2,\n"
    "    set_vorige_kolommen,\n"
    "    toon_stap,\n"
    "):\n"
    "    _lden, _lnight = init_lden_lnight_index(raw_vlaanderen_lden_1, raw_vlaanderen_lnight_1)\n"
    "    _kolommen_na_stap = toon_stap('0 index', _lden, _lnight)\n"
    "    set_lden_b2(_lden)\n"
    "    set_lnight_b2(_lnight)\n"
    "    set_vorige_kolommen(_kolommen_na_stap)\n"
    "    list(_lden.columns)\n",
    text,
    count=1,
)

text = re.sub(r"\b_vorige\b", "vorige_kolommen", text)
text = re.sub(r"\b_won_totaal_lden\b", "won_totaal_lden", text)
text = re.sub(r"\b_won_totaal_lnight\b", "won_totaal_lnight", text)
text = re.sub(r"\b_som_per_band\b", "som_per_band", text)
text = re.sub(r"\b_tx_percelen\b", "tx_percelen", text)
text = re.sub(r"\b_agg_transacties\b", "agg_transacties", text)
text = re.sub(r"\b_tx_woningen\b", "tx_woningen", text)
text = re.sub(r"\b_prijzen\b", "prijzen_idx", text)

cells = text.split("@app.cell")
out = [cells[0]]
in_b2 = False
for chunk in cells[1:]:
    cell = "@app.cell" + chunk
    if "set_lden_b2 = mo.state" in cell:
        in_b2 = True
    if in_b2 and "### Stap 29" in cell and "hide_code=True" in cell:
        in_b2 = False

    if in_b2 and re.search(r"def _\([^)]*\):", cell) and "def _(mo):" not in cell:
        if "init_lden_lnight_index" in cell and "set_lden_b2(_lden)" in cell:
            out.append(cell)
            continue

        cell = re.sub(
            r"def _\((.*?)\):",
            lambda m: "def _(" + _patch_params(m.group(1)) + "):",
            cell,
            count=1,
            flags=re.DOTALL,
        )
        cell = cell.replace(
            "):\n",
            "):\n"
            "    if lden_b2 is None or lnight_b2 is None:\n"
            "        raise RuntimeError('Voer eerst stap 0 (index) uit.')\n"
            "    _lden = lden_b2\n"
            "    _lnight = lnight_b2\n",
            1,
        )
        # lden/lnight → _lden/_lnight in cellichaam (niet in strings)
        for old, new in [
            ("lden[_KOL]", "_lden[_KOL]"),
            ("lnight[_KOL]", "_lnight[_KOL]"),
            ("lden.index", "_lden.index"),
            ("lnight.index", "_lnight.index"),
            ("toon_stap(f'", "toon_stap(f'"),
            (", lden, lnight,", ", _lden, _lnight,"),
            ("set_lden_b2(lden)", "set_lden_b2(_lden)"),
            ("set_lnight_b2(lnight)", "set_lnight_b2(_lnight)"),
            ("lden[[_KOL]]", "_lden[[_KOL]]"),
            ("lden_1 = lden[", "lden_1 = _lden["),
            ("brussel_lden, lden)", "brussel_lden, _lden)"),
            ("koppel_conversie_aan_contourband(conversie_lden, lden)", "koppel_conversie_aan_contourband(conversie_lden, _lden)"),
            ("[lden[_KOL].iloc[0]]", "[_lden[_KOL].iloc[0]]"),
            ("won_totaal_lden = _won_vla_lden", "won_totaal_lden = _won_vla_lden"),
        ]:
            cell = cell.replace(old, new)
        cell = re.sub(
            r"(    vorige_kolommen = toon_stap\([^\n]+\n)(?!    set_lden_b2)",
            r"\1    set_lden_b2(_lden)\n    set_lnight_b2(_lnight)\n    set_vorige_kolommen(_kolommen_na_stap)\n",
            cell,
        )
        cell = re.sub(r"\n    return[^\n]+\n", "\n", cell)

    if "lden_1 = _lden[list(FLOW_KOLOMMEN)]" in cell or "lden_1 = lden[list(FLOW_KOLOMMEN)]" in cell:
        cell = cell.replace("lden_1 = lden[", "lden_1 = _lden[")
        cell = cell.replace("lnight_1 = lnight[", "lnight_1 = _lnight[")
        if "return (lden_1, lnight_1)" not in cell:
            cell = cell.replace(
                "    list(lden_1.columns)\n",
                "    list(lden_1.columns)\n    return (lden_1, lnight_1)\n",
                1,
            )

    out.append(cell)
text = "".join(out)

text = text.replace(
    "@app.cell\ndef _(lden_1, lnight_1):\n"
    "    lden_handmatig, _lnight_handmatig = (lden_1.copy(), lnight_1.copy())\n"
    "    print(f'lden: {lden_handmatig.shape}, lnight: {_lnight_handmatig.shape}')\n"
    "    lden_handmatig.head(3)\n"
    "    return\n\n\n"
    "@app.cell\ndef _(lden_1, lnight_1):",
    "@app.cell\ndef _(lden_1, lnight_1):",
    1,
)

path.write_text(text, encoding="utf-8")
print("OK", path)
