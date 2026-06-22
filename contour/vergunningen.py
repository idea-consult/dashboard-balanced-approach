"""Omgevingsloket pivot parsing (raw Excel and lang CSV)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


METRIEKEN = [
    "Aantal projecten",
    "Aantal gebouwen",
    "Aantal wooneenheden",
    "Nuttige woonoppervlakte",
    "Bovengronds nuttige oppervlakte",
    "Bovengronds grond oppervlakte",
]


def lees_omgevingsloket_raw(pad: Path) -> pd.DataFrame:
    """Read Excel without header; first 3 rows are pivot headers."""
    return pd.read_excel(pad, sheet_name=0, header=None)


def parse_omgevingsloket_waarde(waarde):
    """Parse Belgian number formats and areas like '1.234,56 m²'."""
    if pd.isna(waarde):
        return pd.NA
    if isinstance(waarde, (int, float)) and not isinstance(waarde, bool):
        return float(waarde)

    tekst = str(waarde).strip()
    if not tekst or tekst.lower() == "nan":
        return pd.NA

    tekst = re.sub(r"\s*m.?$", "", tekst, flags=re.IGNORECASE).strip()
    if "," in tekst:
        tekst = tekst.replace(".", "").replace(",", ".")
    try:
        return float(tekst)
    except ValueError:
        return pd.NA


def normaliseer_jaar_indiening(waarde) -> int | str:
    tekst = str(waarde).strip()
    if tekst == "Totalen":
        return "Totalen"
    try:
        return int(tekst)
    except ValueError:
        return tekst


def pivot_naar_lang(raw: pd.DataFrame, bron: str) -> pd.DataFrame:
    """Pivot Excel to long: year x gemeente x handeling x functie x metriek."""
    rij_handeling = raw.iloc[0].fillna("")
    rij_functie = raw.iloc[1].fillna("")
    rij_metriek = raw.iloc[2].fillna("")

    records: list[dict] = []
    for row_idx in range(3, len(raw)):
        jaar_raw = str(raw.iloc[row_idx, 0]).strip()
        if jaar_raw in ("nan", "Jaar indiening"):
            continue

        gemeente_raw = raw.iloc[row_idx, 1]
        gemeente = pd.NA if pd.isna(gemeente_raw) else str(gemeente_raw).strip()

        for col in range(2, raw.shape[1]):
            metriek = str(rij_metriek[col]).strip()
            if not metriek or metriek == "nan":
                continue

            handeling = str(rij_handeling[col]).strip() or pd.NA
            gebouw_functie = str(rij_functie[col]).strip() or pd.NA
            waarde = parse_omgevingsloket_waarde(raw.iloc[row_idx, col])

            records.append(
                {
                    "bron": bron,
                    "jaar_indiening": normaliseer_jaar_indiening(jaar_raw),
                    "gemeente": gemeente,
                    "handeling": handeling,
                    "gebouw_functie": gebouw_functie,
                    "metriek": metriek,
                    "waarde": waarde,
                }
            )

    return pd.DataFrame(records)


def lees_vergunningen_lang(pad: Path) -> pd.DataFrame:
    return pd.read_csv(pad, sep=";")


def combineer_vergunningen_lang(*frames: pd.DataFrame) -> pd.DataFrame:
    return pd.concat(frames, ignore_index=True)


# Jaarvenster voor vergunningstellers in flow rates (jaarlijks gemiddelde).
JAAR_TELLERS_START = 2020
JAAR_TELLERS_EIND = 2025
JAAR_TELLERS_LABEL = f"gemiddelde_{JAAR_TELLERS_START}_{JAAR_TELLERS_EIND}"
JAAR_TELLERS_VENSTER = f"{JAAR_TELLERS_START}–{JAAR_TELLERS_EIND}"

VERGUNNINGEN_GEMIDDELDE_MD = f"""\
## Vergunningstellers — jaarlijks gemiddelde ({JAAR_TELLERS_VENSTER})

Stappen **11–14** gebruiken dezelfde methode voor omgevingsloket, kwetsbare functies en verkaveling.

### Periode en eenheid

- **Geen enkel kalenderjaar** — we nemen het **jaarlijks gemiddelde** over **{JAAR_TELLERS_VENSTER}** (6 jaren).
- Elke waarde in `vla` / `lden` is dus: *“gemiddeld aantal per jaar”*, geschikt als **flow-teller** (jaarlijkse instroom).

### Methode (per vergunningstype)

1. Filter gemeente-rijen in `{JAAR_TELLERS_VENSTER}`; sluit `Totalen`-rijen en `handeling == "Totalen"` uit.
2. Per **type** (`bron`, `gemeente`, `handeling`, `gebouw_functie`, `metriek`): som per kalenderjaar.
3. **Gemiddelde** = som over 6 jaren ÷ 6 (ontbrekende jaren = 0).
4. `gemiddelde_jaarlijkse_vergunningen()` → label `jaar_indiening = "{JAAR_TELLERS_LABEL}"`.
5. Daarna: gemeente → dB-contour via ruimtelijke conversietabel.

### Koppeling flow rates

| Variabele | Vergunningstype | Gebruikt in |
|---|---|---|
| `vergunde_wooneenheden_nieuwbouw` | Nieuwbouw × Aantal wooneenheden | `verbod_kleine_woning` |
| `vergunningen_kwetsbare_groep` | kwetsbare_functies | `verbod_kwetsbare_groep` |
| `renovatie_totaal` | Verbouwen of hergebruik | R+, R−, renovatiemaatregelen |
| `gem_wooneenheden_per_vergunning` | omgevingsloket (WE/projecten) | hulpcijfer; nog niet in flow-formules |

**Scope:** Vlaamse ringgemeenten die naar contour kunnen worden gemapt (niet heel Vlaanderen/Brussel).
"""

VERGUNNINGEN_STAP_BEREKENING = f"""\
1. `verg_gem = gemiddelde_jaarlijkse_vergunningen(verg_combined)` — jaarlijks gemiddelde per type ({JAAR_TELLERS_VENSTER}).\n\
2. `verdeel_gemeente_naar_contour(verg_gem, …)` — verdeling naar dB-band.\n\
3. Som per band over de rijen die bij deze variabele horen (filter op `handeling` / `metriek` / `bron`).\
"""

_DIM_VERGUNNING = ["bron", "gemeente", "handeling", "gebouw_functie", "metriek"]


def _is_jaar_in_bereik(waarde, start: int, end: int) -> bool:
    try:
        jaar = int(str(waarde).strip())
    except (TypeError, ValueError):
        return False
    return start <= jaar <= end


def filter_jaar_tellersbereik(
    df: pd.DataFrame,
    start: int = JAAR_TELLERS_START,
    end: int = JAAR_TELLERS_EIND,
) -> pd.DataFrame:
    """Gemeente-rijen in jaarvenster; sluit landelijke totalen en dubbeltellingen uit."""
    out = df.copy()
    out = out[out["gemeente"].notna() & ~out["gemeente"].astype(str).isin(["-", "Totalen", ""])]
    out = out[out["handeling"].astype(str) != "Totalen"]
    mask = out["jaar_indiening"].apply(lambda j: _is_jaar_in_bereik(j, start, end))
    return out.loc[mask].copy()


def gemiddelde_jaarlijkse_vergunningen(
    df: pd.DataFrame,
    start: int = JAAR_TELLERS_START,
    end: int = JAAR_TELLERS_EIND,
) -> pd.DataFrame:
    """
    Jaarlijks gemiddelde per vergunningstype (handeling × metriek × …) over ``start``–``end``.

    Per gemeente en type: som per kalenderjaar, daarna gemiddelde over het volledige
    jaarvenster (ontbrekende jaren tellen als 0).
    """
    gefilterd = filter_jaar_tellersbereik(df, start, end)
    if gefilterd.empty:
        return pd.DataFrame(
            columns=[*_DIM_VERGUNNING, "jaar_indiening", "waarde"],
        )

    jaren = list(range(start, end + 1))
    n_jaren = len(jaren)
    jaar_kolom = gefilterd["jaar_indiening"].astype(str)

    yearly = (
        gefilterd.assign(_jaar=jaar_kolom)
        .groupby([*_DIM_VERGUNNING, "_jaar"], dropna=False)["waarde"]
        .sum()
        .unstack("_jaar", fill_value=0.0)
    )
    for jaar in jaren:
        kolom = str(jaar)
        if kolom not in yearly.columns:
            yearly[kolom] = 0.0
    yearly = yearly[[str(j) for j in jaren]]
    gemiddelde = yearly.sum(axis=1) / n_jaren

    out = gemiddelde.reset_index(name="waarde")
    out["jaar_indiening"] = JAAR_TELLERS_LABEL if (start, end) == (JAAR_TELLERS_START, JAAR_TELLERS_EIND) else f"gemiddelde_{start}_{end}"
    return out[[*_DIM_VERGUNNING, "jaar_indiening", "waarde"]]


def gem_wooneenheden_per_vergunning_gemiddelde(
    df: pd.DataFrame,
    start: int = JAAR_TELLERS_START,
    end: int = JAAR_TELLERS_EIND,
) -> float:
    """Gemiddelde over jaren van (som wooneenheden / som projecten) voor omgevingsloket."""
    gefilterd = filter_jaar_tellersbereik(df, start, end)
    omg = gefilterd[gefilterd["bron"] == "omgevingsloket"]
    if omg.empty:
        return 0.0

    jaren = list(range(start, end + 1))
    ratios: list[float] = []
    for jaar in jaren:
        y = omg[omg["jaar_indiening"].astype(str) == str(jaar)]
        proj = y.loc[y["metriek"] == "Aantal projecten", "waarde"].sum()
        we = y.loc[y["metriek"] == "Aantal wooneenheden", "waarde"].sum()
        ratios.append(float(we / proj) if proj > 0 else 0.0)
    return sum(ratios) / len(jaren) if jaren else 0.0
