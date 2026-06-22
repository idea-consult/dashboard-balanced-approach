"""Per db_ondergrens flow rates (baseline + active) uit lden-kolommen."""

from __future__ import annotations

import pandas as pd

from contour.columns import (
    KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR,
    KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR,
)
from contour.flows import (
    AANKOOP_AANDEEL,
    ONTEIGING_RATE,
    RENOVATIE_ISO_AANDEEL,
)
from contour.schema import INDEX_NAME, band_metadata

WOONGEBIED_JAREN = 5
WOONVERDICHTING_BASELINE = 0.01
VERBOD_GROTE_WONING_BASELINE = 0.01
ISOLATIE_NIEUW_NIET_BASELINE = 0.5
ISOLATIE_NIEUW_GEO_BASELINE = 1.0


from contour.flow_stap_docs import FLOW_STAP_DEFINITIES, FlowStapDefinitie


def kolom_baseline(measure_id: str) -> str:
    return f"{measure_id}_baseline"


def kolom_active(measure_id: str) -> str:
    return f"{measure_id}_active"


def lden_vars_bereiden(lden: pd.DataFrame) -> pd.DataFrame:
    """FLOW-lden per band: index ``db_ondergrens``, numerieke kolommen."""
    if INDEX_NAME in lden.columns:
        out = lden.set_index(INDEX_NAME)
    elif lden.index.name == INDEX_NAME:
        out = lden.copy()
    else:
        raise ValueError(f"lden mist kolom/index '{INDEX_NAME}'")

    out.index = out.index.astype(int)
    out.index.name = INDEX_NAME
    return out.apply(pd.to_numeric, errors="coerce").fillna(0.0)


def init_lden_flows(lden_vars: pd.DataFrame) -> pd.DataFrame:
    """Leeg flow-frame met dezelfde index als ``lden_vars``."""
    return pd.DataFrame(index=lden_vars.index.copy())


def flow_rate_per_contour(
    teller: pd.Series,
    noemer: pd.Series,
    *,
    cap: float = 1.0,
) -> pd.Series:
    """Element-wise teller/noemer, veilig bij noemer 0, met cap."""
    t = teller.reindex(noemer.index).fillna(0.0).astype(float)
    n = noemer.fillna(0.0).astype(float)
    out = pd.Series(0.0, index=n.index, dtype=float)
    mask = n > 0
    out.loc[mask] = (t.loc[mask] / n.loc[mask]).clip(upper=cap)
    return out


def vaste_rate_per_contour(index: pd.Index, waarde: float) -> pd.Series:
    return pd.Series(float(waarde), index=index, dtype=float)


def toon_stap_flow(
    stap_naam: str,
    lden_flows: pd.DataFrame,
    vorige_kolommen: list[str] | None = None,
) -> list[str]:
    """Print kolomoverzicht na een flow-stap."""
    cols = list(lden_flows.columns)
    nieuw = [c for c in cols if vorige_kolommen is None or c not in vorige_kolommen]
    print(f"=== {stap_naam} ===")
    print(f"lden_flows.shape: {lden_flows.shape}")
    print(f"kolommen ({len(cols)}): {cols}")
    if nieuw:
        print(f"  + nieuw: {nieuw}")
    return cols


def _kolom(lden_vars: pd.DataFrame, naam: str) -> pd.Series:
    if naam in lden_vars.columns:
        return lden_vars[naam].astype(float)
    return pd.Series(0.0, index=lden_vars.index, dtype=float)


def _renovatie_split(lden_vars: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    renovatie = _kolom(lden_vars, "renovatie_totaal")
    r_plus = renovatie * RENOVATIE_ISO_AANDEEL
    r_min = renovatie * (1.0 - RENOVATIE_ISO_AANDEEL)
    return r_plus, r_min


def _voeg_stap_toe(
    lden_flows: pd.DataFrame,
    measure_id: str,
    baseline: pd.Series,
    active: pd.Series,
) -> pd.DataFrame:
    out = lden_flows.copy()
    out[kolom_baseline(measure_id)] = baseline.astype(float)
    out[kolom_active(measure_id)] = active.astype(float)
    return out


def stap_geen_effect(
    lden_flows: pd.DataFrame,
    lden_vars: pd.DataFrame,
    measure_id: str,
) -> pd.DataFrame:
    nul = pd.Series(0.0, index=lden_vars.index, dtype=float)
    return _voeg_stap_toe(lden_flows, measure_id, nul, nul)


def stap_woongebiedverbod(lden_flows: pd.DataFrame, lden_vars: pd.DataFrame) -> pd.DataFrame:
    """Baseline: netto woongebied-aanduiding; active: schrapping (jaarlijks)."""
    bebouw = _kolom(lden_vars, KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR) / WOONGEBIED_JAREN
    schrapping = _kolom(lden_vars, KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR) / WOONGEBIED_JAREN
    noemer = _kolom(lden_vars, "onbebouwde_onbebouwbare_percelen")
    baseline = flow_rate_per_contour(bebouw - schrapping, noemer)
    active = flow_rate_per_contour(schrapping, noemer)
    return _voeg_stap_toe(lden_flows, "woongebiedverbod", baseline, active)


def stap_aankoopbeleid_percelen(lden_flows: pd.DataFrame, lden_vars: pd.DataFrame) -> pd.DataFrame:
    teller = AANKOOP_AANDEEL * _kolom(lden_vars, "alle_transacties_percelen")
    noemer = _kolom(lden_vars, "onbebouwde_bebouwbare_percelen")
    nul = pd.Series(0.0, index=lden_vars.index, dtype=float)
    return _voeg_stap_toe(
        lden_flows,
        "aankoopbeleid_percelen",
        nul,
        flow_rate_per_contour(teller, noemer),
    )


def stap_voorkooprecht_percelen(lden_flows: pd.DataFrame, lden_vars: pd.DataFrame) -> pd.DataFrame:
    teller = _kolom(lden_vars, "alle_verkopen_onbebouwde_bebouwbare_percelen")
    noemer = _kolom(lden_vars, "onbebouwde_bebouwbare_percelen")
    nul = pd.Series(0.0, index=lden_vars.index, dtype=float)
    return _voeg_stap_toe(
        lden_flows,
        "voorkooprecht_percelen",
        nul,
        flow_rate_per_contour(teller, noemer),
    )


def stap_onteigening_percelen(lden_flows: pd.DataFrame, lden_vars: pd.DataFrame) -> pd.DataFrame:
    nul = pd.Series(0.0, index=lden_vars.index, dtype=float)
    vast = vaste_rate_per_contour(lden_vars.index, ONTEIGING_RATE)
    return _voeg_stap_toe(lden_flows, "onteigening_percelen", nul, vast)


def stap_verbod_kleine_woning(lden_flows: pd.DataFrame, lden_vars: pd.DataFrame) -> pd.DataFrame:
    teller = _kolom(lden_vars, "vergunde_wooneenheden_nieuwbouw")
    noemer = _kolom(lden_vars, "onbebouwde_bebouwbare_percelen")
    rate = flow_rate_per_contour(teller, noemer)
    return _voeg_stap_toe(lden_flows, "verbod_kleine_woning", rate, rate)


def stap_verbod_grote_woning(lden_flows: pd.DataFrame, lden_vars: pd.DataFrame) -> pd.DataFrame:
    baseline = vaste_rate_per_contour(lden_vars.index, VERBOD_GROTE_WONING_BASELINE)
    nul = pd.Series(0.0, index=lden_vars.index, dtype=float)
    return _voeg_stap_toe(lden_flows, "verbod_grote_woning", baseline, nul)


def stap_verbod_kwetsbare_groep(lden_flows: pd.DataFrame, lden_vars: pd.DataFrame) -> pd.DataFrame:
    teller = _kolom(lden_vars, "vergunningen_kwetsbare_groep")
    noemer = _kolom(lden_vars, "onbebouwde_bebouwbare_percelen")
    rate = flow_rate_per_contour(teller, noemer)
    return _voeg_stap_toe(lden_flows, "verbod_kwetsbare_groep", rate, rate)


def stap_woonverdichtingsverbod(
    lden_flows: pd.DataFrame,
    lden_vars: pd.DataFrame,
    measure_id: str,
) -> pd.DataFrame:
    baseline = vaste_rate_per_contour(lden_vars.index, WOONVERDICHTING_BASELINE)
    nul = pd.Series(0.0, index=lden_vars.index, dtype=float)
    return _voeg_stap_toe(lden_flows, measure_id, baseline, nul)


def stap_aankoopbeleid_woningen(
    lden_flows: pd.DataFrame,
    lden_vars: pd.DataFrame,
    measure_id: str,
    noemer_kolom: str,
) -> pd.DataFrame:
    teller = AANKOOP_AANDEEL * _kolom(lden_vars, "alle_transacties_woningen")
    noemer = _kolom(lden_vars, noemer_kolom)
    nul = pd.Series(0.0, index=lden_vars.index, dtype=float)
    return _voeg_stap_toe(
        lden_flows,
        measure_id,
        nul,
        flow_rate_per_contour(teller, noemer),
    )


def stap_voorkooprecht_woningen(
    lden_flows: pd.DataFrame,
    lden_vars: pd.DataFrame,
    measure_id: str,
    noemer_kolom: str,
) -> pd.DataFrame:
    teller = _kolom(lden_vars, "alle_verkopen_woningen")
    noemer = _kolom(lden_vars, noemer_kolom)
    nul = pd.Series(0.0, index=lden_vars.index, dtype=float)
    return _voeg_stap_toe(
        lden_flows,
        measure_id,
        nul,
        flow_rate_per_contour(teller, noemer),
    )


def stap_onteigening_woningen(
    lden_flows: pd.DataFrame,
    lden_vars: pd.DataFrame,
    measure_id: str,
) -> pd.DataFrame:
    nul = pd.Series(0.0, index=lden_vars.index, dtype=float)
    vast = vaste_rate_per_contour(lden_vars.index, ONTEIGING_RATE)
    return _voeg_stap_toe(lden_flows, measure_id, nul, vast)


def stap_isolatievoorschriften_nieuwbouw(
    lden_flows: pd.DataFrame,
    lden_vars: pd.DataFrame,
    measure_id: str,
    *,
    baseline_vast: float | None,
    active_vast: float | None,
    teller_kolom: str | None = None,
) -> pd.DataFrame:
    noemer = _kolom(lden_vars, "nieuwe_woning")
    if teller_kolom:
        baseline = flow_rate_per_contour(_kolom(lden_vars, teller_kolom), noemer)
    elif baseline_vast is not None:
        baseline = vaste_rate_per_contour(lden_vars.index, baseline_vast)
    else:
        baseline = pd.Series(0.0, index=lden_vars.index, dtype=float)

    if active_vast is not None:
        active = vaste_rate_per_contour(lden_vars.index, active_vast)
    else:
        active = pd.Series(0.0, index=lden_vars.index, dtype=float)

    return _voeg_stap_toe(lden_flows, measure_id, baseline, active)


def stap_renovatie(
    lden_flows: pd.DataFrame,
    lden_vars: pd.DataFrame,
    measure_id: str,
    *,
    baseline_factor: float,
    active_factor: float,
) -> pd.DataFrame:
    r_plus, r_min = _renovatie_split(lden_vars)
    noemer = _kolom(lden_vars, "bewoonde_niet_geïsoleerde_woning")
    baseline_teller = baseline_factor * r_plus
    active_teller = active_factor * (r_plus + r_min)
    baseline = flow_rate_per_contour(baseline_teller, noemer) if baseline_factor else pd.Series(
        0.0, index=lden_vars.index, dtype=float
    )
    active = flow_rate_per_contour(active_teller, noemer) if active_factor else pd.Series(
        0.0, index=lden_vars.index, dtype=float
    )
    return _voeg_stap_toe(lden_flows, measure_id, baseline, active)


def stap_aanleg_geluidsbuffers(lden_flows: pd.DataFrame, lden_vars: pd.DataFrame) -> pd.DataFrame:
    teller = _kolom(lden_vars, "potentieel_isoleerbare_woningen") / 5.0
    noemer = _kolom(lden_vars, "bewoonde_niet_geïsoleerde_woning")
    nul = pd.Series(0.0, index=lden_vars.index, dtype=float)
    return _voeg_stap_toe(
        lden_flows,
        "aanleg_geluidsbuffers",
        nul,
        flow_rate_per_contour(teller, noemer),
    )


FLOW_STAP_VOLGORDE: tuple[str, ...] = (
    "verkavelingsverbod",
    "woongebiedverbod",
    "aankoopbeleid_percelen",
    "voorkooprecht_percelen",
    "onteigening_percelen",
    "verbod_kleine_woning",
    "verbod_grote_woning",
    "verbod_kwetsbare_groep",
    "woonverdichtingsverbod_niet_geïsoleerde_woningen",
    "woonverdichtingsverbod_geïsoleerde_woningen",
    "aankoopbeleid_niet_geïsoleerde_woningen",
    "aankoopbeleid_geïsoleerde_woningen",
    "voorkooprecht_niet_geïsoleerde_woningen",
    "voorkooprecht_geïsoleerde_woningen",
    "onteigening_niet_geïsoleerde_woningen",
    "onteigening_geïsoleerde_woningen",
    "isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning",
    "isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning",
    "renovatie_zonder_maatregel",
    "verplicht_isoleren_renovatie",
    "gesubsidieerd_isolatieprogramma",
    "gestuurd_isolatieprogramma",
    "aanleg_geluidsbuffers",
    "compensatie_buitenzone",
    "compensatie_verhuis",
    "versterken_sociale_cohesie",
    "vergroenen_leefomgeving",
)


def voer_flow_stap(
    measure_id: str,
    lden_flows: pd.DataFrame,
    lden_vars: pd.DataFrame,
) -> pd.DataFrame:
    """Voer één flow-stap uit op basis van ``measure_id``."""
    if measure_id in {
        "verkavelingsverbod",
        "compensatie_buitenzone",
        "compensatie_verhuis",
        "versterken_sociale_cohesie",
        "vergroenen_leefomgeving",
    }:
        return stap_geen_effect(lden_flows, lden_vars, measure_id)
    if measure_id == "woongebiedverbod":
        return stap_woongebiedverbod(lden_flows, lden_vars)
    if measure_id == "aankoopbeleid_percelen":
        return stap_aankoopbeleid_percelen(lden_flows, lden_vars)
    if measure_id == "voorkooprecht_percelen":
        return stap_voorkooprecht_percelen(lden_flows, lden_vars)
    if measure_id == "onteigening_percelen":
        return stap_onteigening_percelen(lden_flows, lden_vars)
    if measure_id == "verbod_kleine_woning":
        return stap_verbod_kleine_woning(lden_flows, lden_vars)
    if measure_id == "verbod_grote_woning":
        return stap_verbod_grote_woning(lden_flows, lden_vars)
    if measure_id == "verbod_kwetsbare_groep":
        return stap_verbod_kwetsbare_groep(lden_flows, lden_vars)
    if measure_id.startswith("woonverdichtingsverbod_"):
        return stap_woonverdichtingsverbod(lden_flows, lden_vars, measure_id)
    if measure_id == "aankoopbeleid_niet_geïsoleerde_woningen":
        return stap_aankoopbeleid_woningen(
            lden_flows, lden_vars, measure_id, "bewoonde_niet_geïsoleerde_woning"
        )
    if measure_id == "aankoopbeleid_geïsoleerde_woningen":
        return stap_aankoopbeleid_woningen(
            lden_flows, lden_vars, measure_id, "bewoonde_geïsoleerde_woning"
        )
    if measure_id == "voorkooprecht_niet_geïsoleerde_woningen":
        return stap_voorkooprecht_woningen(
            lden_flows, lden_vars, measure_id, "bewoonde_niet_geïsoleerde_woning"
        )
    if measure_id == "voorkooprecht_geïsoleerde_woningen":
        return stap_voorkooprecht_woningen(
            lden_flows, lden_vars, measure_id, "bewoonde_geïsoleerde_woning"
        )
    if measure_id.startswith("onteigening_") and measure_id != "onteigening_percelen":
        return stap_onteigening_woningen(lden_flows, lden_vars, measure_id)
    if measure_id == "isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning":
        return stap_isolatievoorschriften_nieuwbouw(
            lden_flows,
            lden_vars,
            measure_id,
            baseline_vast=ISOLATIE_NIEUW_NIET_BASELINE,
            active_vast=0.0,
            teller_kolom="nieuwbouw_niet_geïsoleerd",
        )
    if measure_id == "isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning":
        return stap_isolatievoorschriften_nieuwbouw(
            lden_flows,
            lden_vars,
            measure_id,
            baseline_vast=ISOLATIE_NIEUW_GEO_BASELINE,
            active_vast=ISOLATIE_NIEUW_GEO_BASELINE,
            teller_kolom="nieuwbouw_geïsoleerd",
        )
    if measure_id == "renovatie_zonder_maatregel":
        return stap_renovatie(lden_flows, lden_vars, measure_id, baseline_factor=1.0, active_factor=0.0)
    if measure_id == "verplicht_isoleren_renovatie":
        return stap_renovatie(lden_flows, lden_vars, measure_id, baseline_factor=0.0, active_factor=1.0)
    if measure_id == "gesubsidieerd_isolatieprogramma":
        return stap_renovatie(lden_flows, lden_vars, measure_id, baseline_factor=0.0, active_factor=2.0)
    if measure_id == "gestuurd_isolatieprogramma":
        return stap_renovatie(lden_flows, lden_vars, measure_id, baseline_factor=0.0, active_factor=4.0)
    if measure_id == "aanleg_geluidsbuffers":
        return stap_aanleg_geluidsbuffers(lden_flows, lden_vars)
    raise KeyError(f"Onbekende flow-stap: {measure_id}")


def bouw_lden_flows(lden_vars: pd.DataFrame) -> pd.DataFrame:
    """Alle flow-stappen na elkaar."""
    flows = init_lden_flows(lden_vars)
    for measure_id in FLOW_STAP_VOLGORDE:
        flows = voer_flow_stap(measure_id, flows, lden_vars)
    return flows


def lden_flows_met_metadata(lden_vars: pd.DataFrame, lden_flows: pd.DataFrame) -> pd.DataFrame:
    """Voeg bandlabels toe voor leesbaarheid in notebook/export."""
    meta = band_metadata(lden_vars.index)
    out = lden_flows.copy()
    out.insert(0, "geluidscontour", meta["geluidscontour"].values)
    out.insert(0, INDEX_NAME, lden_vars.index.astype(int))
    return out


def aggregeer_naar_flow_rules(
    lden_vars: pd.DataFrame,
    lden_flows: pd.DataFrame,
    *,
    noemer_kolommen: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Gewogen gemiddelde per maatregel (noemer = stock op band) voor ``flow_rules.csv``.

    Fallback: ongewogen gemiddelde over banden met noemer > 0.
    """
    default_noemers = {
        "woongebiedverbod": "onbebouwde_onbebouwbare_percelen",
        "aankoopbeleid_percelen": "onbebouwde_bebouwbare_percelen",
        "voorkooprecht_percelen": "onbebouwde_bebouwbare_percelen",
        "verbod_kleine_woning": "onbebouwde_bebouwbare_percelen",
        "verbod_grote_woning": "onbebouwde_bebouwbare_percelen",
        "verbod_kwetsbare_groep": "onbebouwde_bebouwbare_percelen",
        "woonverdichtingsverbod_niet_geïsoleerde_woningen": "bewoonde_niet_geïsoleerde_woning",
        "woonverdichtingsverbod_geïsoleerde_woningen": "bewoonde_geïsoleerde_woning",
        "aankoopbeleid_niet_geïsoleerde_woningen": "bewoonde_niet_geïsoleerde_woning",
        "aankoopbeleid_geïsoleerde_woningen": "bewoonde_geïsoleerde_woning",
        "voorkooprecht_niet_geïsoleerde_woningen": "bewoonde_niet_geïsoleerde_woning",
        "voorkooprecht_geïsoleerde_woningen": "bewoonde_geïsoleerde_woning",
        "isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning": "nieuwe_woning",
        "isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning": "nieuwe_woning",
        "renovatie_zonder_maatregel": "bewoonde_niet_geïsoleerde_woning",
        "verplicht_isoleren_renovatie": "bewoonde_niet_geïsoleerde_woning",
        "gesubsidieerd_isolatieprogramma": "bewoonde_niet_geïsoleerde_woning",
        "gestuurd_isolatieprogramma": "bewoonde_niet_geïsoleerde_woning",
        "aanleg_geluidsbuffers": "bewoonde_niet_geïsoleerde_woning",
    }
    noemer_kolommen = noemer_kolommen or default_noemers

    records: list[dict] = []
    for measure_id in FLOW_STAP_VOLGORDE:
        bl_col = kolom_baseline(measure_id)
        act_col = kolom_active(measure_id)
        baseline_s = lden_flows[bl_col]
        active_s = lden_flows[act_col]
        noemer_col = noemer_kolommen.get(measure_id)
        if noemer_col and noemer_col in lden_vars.columns:
            gewicht = _kolom(lden_vars, noemer_col)
            totaal = float(gewicht.sum())
            if totaal > 0:
                bl = float((baseline_s * gewicht).sum() / totaal)
                act = float((active_s * gewicht).sum() / totaal)
            else:
                bl = act = 0.0
        else:
            bl = float(baseline_s.mean())
            act = float(active_s.mean())
        records.append(
            {
                "measure_id": measure_id,
                "flow_rate_baseline": bl,
                "flow_rate_active": act,
            }
        )
    return pd.DataFrame(records)


def _notebook_rate(teller: str, noemer: str) -> str:
    """Notebook: teller / noemer, veilig bij noemer 0, cap 1."""
    return f"({teller}).div({noemer}).where({noemer} > 0, 0).clip(upper=1)"


def stap_notebook_code(measure_id: str) -> str:
    """Expliciete pandas-code voor één flow-stap in het notebook."""
    bl = kolom_baseline(measure_id)
    act = kolom_active(measure_id)
    show = f'lden_flows[["{bl}", "{act}"]].head(10)'

    if measure_id in {
        "verkavelingsverbod",
        "compensatie_buitenzone",
        "compensatie_verhuis",
        "versterken_sociale_cohesie",
        "vergroenen_leefomgeving",
    }:
        return (
            f'lden_flows["{bl}"] = 0.0\n'
            f'lden_flows["{act}"] = 0.0\n'
            f"{show}"
        )

    if measure_id == "woongebiedverbod":
        beb = f'lden_vars["{KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR}"]'
        sch = f'lden_vars["{KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR}"]'
        noem = 'lden_vars["onbebouwde_onbebouwbare_percelen"]'
        return (
            f"lden_flows[\"{bl}\"] = (\n"
            f"    ({beb} - {sch}) / {WOONGEBIED_JAREN}\n"
            f").div({noem}).where({noem} > 0, 0).clip(upper=1)\n"
            f"lden_flows[\"{act}\"] = (\n"
            f"    {sch} / {WOONGEBIED_JAREN}\n"
            f").div({noem}).where({noem} > 0, 0).clip(upper=1)\n"
            f"{show}"
        )

    if measure_id == "aankoopbeleid_percelen":
        return (
            '_noemer = lden_vars["onbebouwde_bebouwbare_percelen"]\n'
            f'_teller = {AANKOOP_AANDEEL} * lden_vars["alle_transacties_percelen"]\n'
            f'lden_flows["{bl}"] = 0.0\n'
            f'lden_flows["{act}"] = {_notebook_rate("_teller", "_noemer")}\n'
            f"{show}"
        )

    if measure_id == "voorkooprecht_percelen":
        return (
            '_noemer = lden_vars["onbebouwde_bebouwbare_percelen"]\n'
            '_teller = lden_vars["alle_verkopen_onbebouwde_bebouwbare_percelen"]\n'
            f'lden_flows["{bl}"] = 0.0\n'
            f'lden_flows["{act}"] = {_notebook_rate("_teller", "_noemer")}\n'
            f"{show}"
        )

    if measure_id == "onteigening_percelen":
        return (
            f'lden_flows["{bl}"] = 0.0\n'
            f'lden_flows["{act}"] = {ONTEIGING_RATE}\n'
            f"{show}"
        )

    if measure_id == "verbod_kleine_woning":
        return (
            '_noemer = lden_vars["onbebouwde_bebouwbare_percelen"]\n'
            '_teller = lden_vars["vergunde_wooneenheden_nieuwbouw"]\n'
            f'_rate = {_notebook_rate("_teller", "_noemer")}\n'
            f'lden_flows["{bl}"] = _rate\n'
            f'lden_flows["{act}"] = _rate\n'
            f"{show}"
        )

    if measure_id == "verbod_grote_woning":
        return (
            f'lden_flows["{bl}"] = {VERBOD_GROTE_WONING_BASELINE}\n'
            f'lden_flows["{act}"] = 0.0\n'
            f"{show}"
        )

    if measure_id == "verbod_kwetsbare_groep":
        return (
            '_noemer = lden_vars["onbebouwde_bebouwbare_percelen"]\n'
            '_teller = lden_vars["vergunningen_kwetsbare_groep"]\n'
            f'_rate = {_notebook_rate("_teller", "_noemer")}\n'
            f'lden_flows["{bl}"] = _rate\n'
            f'lden_flows["{act}"] = _rate\n'
            f"{show}"
        )

    if measure_id.startswith("woonverdichtingsverbod_"):
        return (
            f'lden_flows["{bl}"] = {WOONVERDICHTING_BASELINE}\n'
            f'lden_flows["{act}"] = 0.0\n'
            f"{show}"
        )

    if measure_id == "aankoopbeleid_niet_geïsoleerde_woningen":
        noemer = "bewoonde_niet_geïsoleerde_woning"
    elif measure_id == "aankoopbeleid_geïsoleerde_woningen":
        noemer = "bewoonde_geïsoleerde_woning"
    elif measure_id == "voorkooprecht_niet_geïsoleerde_woningen":
        noemer = "bewoonde_niet_geïsoleerde_woning"
    elif measure_id == "voorkooprecht_geïsoleerde_woningen":
        noemer = "bewoonde_geïsoleerde_woning"
    else:
        noemer = None

    if measure_id.startswith("aankoopbeleid_") and measure_id.endswith("_woningen"):
        return (
            f'_noemer = lden_vars["{noemer}"]\n'
            f'_teller = {AANKOOP_AANDEEL} * lden_vars["alle_transacties_woningen"]\n'
            f'lden_flows["{bl}"] = 0.0\n'
            f'lden_flows["{act}"] = {_notebook_rate("_teller", "_noemer")}\n'
            f"{show}"
        )

    if measure_id.startswith("voorkooprecht_") and measure_id.endswith("_woningen"):
        return (
            f'_noemer = lden_vars["{noemer}"]\n'
            '_teller = lden_vars["alle_verkopen_woningen"]\n'
            f'lden_flows["{bl}"] = 0.0\n'
            f'lden_flows["{act}"] = {_notebook_rate("_teller", "_noemer")}\n'
            f"{show}"
        )

    if measure_id.startswith("onteigening_") and measure_id != "onteigening_percelen":
        return (
            f'lden_flows["{bl}"] = 0.0\n'
            f'lden_flows["{act}"] = {ONTEIGING_RATE}\n'
            f"{show}"
        )

    if measure_id == "isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning":
        return (
            '_noemer = lden_vars["nieuwe_woning"]\n'
            '_teller = lden_vars["nieuwbouw_niet_geïsoleerd"]\n'
            f'lden_flows["{bl}"] = {_notebook_rate("_teller", "_noemer")}\n'
            f'lden_flows["{act}"] = 0.0\n'
            f"{show}"
        )

    if measure_id == "isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning":
        return (
            '_noemer = lden_vars["nieuwe_woning"]\n'
            '_teller = lden_vars["nieuwbouw_geïsoleerd"]\n'
            f'lden_flows["{bl}"] = {_notebook_rate("_teller", "_noemer")}\n'
            f'lden_flows["{act}"] = {ISOLATIE_NIEUW_GEO_BASELINE}\n'
            f"{show}"
        )

    if measure_id == "renovatie_zonder_maatregel":
        return (
            '_renovatie = lden_vars["renovatie_totaal"]\n'
            f'_r_plus = _renovatie * {RENOVATIE_ISO_AANDEEL}\n'
            '_noemer = lden_vars["bewoonde_niet_geïsoleerde_woning"]\n'
            f'lden_flows["{bl}"] = {_notebook_rate("_r_plus", "_noemer")}\n'
            f'lden_flows["{act}"] = 0.0\n'
            f"{show}"
        )

    if measure_id == "verplicht_isoleren_renovatie":
        return (
            '_renovatie = lden_vars["renovatie_totaal"]\n'
            f'_r_plus = _renovatie * {RENOVATIE_ISO_AANDEEL}\n'
            f'_r_min = _renovatie * {1.0 - RENOVATIE_ISO_AANDEEL}\n'
            '_noemer = lden_vars["bewoonde_niet_geïsoleerde_woning"]\n'
            f'lden_flows["{bl}"] = 0.0\n'
            f'lden_flows["{act}"] = {_notebook_rate("_r_plus + _r_min", "_noemer")}\n'
            f"{show}"
        )

    if measure_id == "gesubsidieerd_isolatieprogramma":
        return (
            '_renovatie = lden_vars["renovatie_totaal"]\n'
            f'_r_plus = _renovatie * {RENOVATIE_ISO_AANDEEL}\n'
            f'_r_min = _renovatie * {1.0 - RENOVATIE_ISO_AANDEEL}\n'
            '_noemer = lden_vars["bewoonde_niet_geïsoleerde_woning"]\n'
            f'lden_flows["{bl}"] = 0.0\n'
            f'lden_flows["{act}"] = {_notebook_rate("2.0 * (_r_plus + _r_min)", "_noemer")}\n'
            f"{show}"
        )

    if measure_id == "gestuurd_isolatieprogramma":
        return (
            '_renovatie = lden_vars["renovatie_totaal"]\n'
            f'_r_plus = _renovatie * {RENOVATIE_ISO_AANDEEL}\n'
            f'_r_min = _renovatie * {1.0 - RENOVATIE_ISO_AANDEEL}\n'
            '_noemer = lden_vars["bewoonde_niet_geïsoleerde_woning"]\n'
            f'lden_flows["{bl}"] = 0.0\n'
            f'lden_flows["{act}"] = {_notebook_rate("4.0 * (_r_plus + _r_min)", "_noemer")}\n'
            f"{show}"
        )

    if measure_id == "aanleg_geluidsbuffers":
        return (
            '_noemer = lden_vars["bewoonde_niet_geïsoleerde_woning"]\n'
            '_teller = lden_vars["potentieel_isoleerbare_woningen"] / 5\n'
            f'lden_flows["{bl}"] = 0.0\n'
            f'lden_flows["{act}"] = {_notebook_rate("_teller", "_noemer")}\n'
            f"{show}"
        )

    raise KeyError(f"Geen notebook-code voor: {measure_id}")


def stap_definitie(measure_id: str) -> FlowStapDefinitie:
    """Metadata voor notebook-cel (uitleg + formules + aannames)."""
    if measure_id in FLOW_STAP_DEFINITIES:
        return FLOW_STAP_DEFINITIES[measure_id]
    return FlowStapDefinitie(
        measure_id=measure_id,
        titel=measure_id,
        uitleg="Zie STOCKS_EN_FLOWS_BEREKENEN.md §4.",
        formule_baseline=f"{kolom_baseline(measure_id)} = teller / noemer",
        formule_active=f"{kolom_active(measure_id)} = teller / noemer",
        variabelen=tuple(),
        aannames="Nog niet gedocumenteerd in flow_stap_docs.py.",
    )
