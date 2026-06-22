"""Flow-rate calculation aligned with STOCKS_EN_FLOWS_BEREKENEN.md."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from contour.columns import KOL_WOONGEBIED_AANDUIDING
from contour.schema import FLOW_STOCKS, INDEX_NAME, band_metadata

from contour.vergunningen import JAAR_TELLERS_LABEL

JAAR_TELLERS = JAAR_TELLERS_LABEL
AANKOOP_AANDEEL = 0.25  # 50% publiek × 50% opkoopbaar
ONTEIGING_RATE = 0.05
RENOVATIE_ISO_AANDEEL = 0.5  # R+ share without iso-split in data


@dataclass
class FlowRateResult:
    measure_id: str
    flow_rate_baseline: float
    flow_rate_active: float
    teller: float
    noemer: float
    status: str
    opmerking: str = ""


def bereken_flow_rate(teller: float, noemer: float, *, cap: float = 1.0) -> float:
    """Safe teller/noemer with cap."""
    if noemer <= 0:
        return 0.0
    return min(float(teller) / float(noemer), cap)


def _contour_label(lden: pd.DataFrame) -> pd.Series:
    if "geluidscontour" in lden.columns:
        return lden["geluidscontour"]
    return band_metadata(lden.index)["geluidscontour"]


def bouw_stocks_contour(lden: pd.DataFrame) -> pd.DataFrame:
    """Wide stock table per contour (FLOW §2.1)."""
    meta = band_metadata(lden.index) if lden.index.name == INDEX_NAME else band_metadata(
        lden["db_ondergrens"]
    )
    stocks = meta.reset_index(drop=True)
    for kolom in FLOW_STOCKS:
        stocks[kolom] = lden[kolom].fillna(0) if kolom in lden.columns else 0.0
    stocks["placeholder_vastgoed"] = True
    return stocks


def _verg_totaal(
    verg_contour: pd.DataFrame,
    *,
    bron: str | None = None,
    handeling: str | None = None,
    metriek: str,
    jaartal: int = JAAR_TELLERS,
) -> float:
    df = verg_contour.copy()
    if bron:
        df = df[df["bron"] == bron]
    if handeling:
        df = df[df["handeling"] == handeling]
    df = df[df["metriek"] == metriek]
    df = df[df["jaar_indiening"].astype(str) == str(jaartal)]
    return float(df["waarde"].fillna(0).sum())


def _transactie_totaal(transacties: pd.DataFrame, segmenten: list[str]) -> float:
    df = transacties[transacties["segment"].isin(segmenten)]
    return float(pd.to_numeric(df["sum_ParcelsNumber"], errors="coerce").fillna(0).sum())


def bouw_tellers_contour(
    lden: pd.DataFrame,
    verg_contour: pd.DataFrame,
    transacties: pd.DataFrame,
    *,
    jaartal: int = JAAR_TELLERS,
) -> pd.DataFrame:
    """Long teller table (FLOW §2.2–2.4)."""
    records: list[dict] = []
    labels = _contour_label(lden)

    for contour, (_, row) in zip(labels, lden.iterrows()):
        records.append(
            {
                "contour": contour,
                "teller_id": "woongebied_percelen_jaar",
                "waarde": row[KOL_WOONGEBIED_AANDUIDING] / 5,
                "jaar": jaartal,
                "status": "ok",
            }
        )

    if not verg_contour.empty:
        nieuwbouw = verg_contour[
            (verg_contour["handeling"] == "Nieuwbouw")
            & (verg_contour["metriek"] == "Aantal wooneenheden")
            & (verg_contour["jaar_indiening"].astype(str) == str(jaartal))
        ]
        for contour, grp in nieuwbouw.groupby("geluidscontour"):
            records.append(
                {
                    "contour": contour,
                    "teller_id": "vergunde_wooneenheden_nieuwbouw",
                    "waarde": float(grp["waarde"].sum()),
                    "jaar": jaartal,
                    "status": "deels" if grp["waarde"].sum() == 0 else "ok",
                }
            )

    if "alle_transacties_percelen" in lden.columns:
        for contour, waarde in zip(labels, lden["alle_transacties_percelen"]):
            records.append(
                {
                    "contour": contour,
                    "teller_id": "transacties_percelen",
                    "waarde": float(waarde),
                    "jaar": jaartal,
                    "status": "ok" if waarde > 0 else "deels",
                }
            )
    if "alle_transacties_woningen" in lden.columns:
        for contour, waarde in zip(labels, lden["alle_transacties_woningen"]):
            records.append(
                {
                    "contour": contour,
                    "teller_id": "transacties_woningen",
                    "waarde": float(waarde),
                    "jaar": jaartal,
                    "status": "ok" if waarde > 0 else "deels",
                }
            )

    nat_records = [
        (
            "vergunde_wooneenheden_nieuwbouw_totaal",
            _verg_totaal(verg_contour, handeling="Nieuwbouw", metriek="Aantal wooneenheden", jaartal=jaartal),
            "deels",
        ),
        (
            "vergunningen_kwetsbare_groep",
            _verg_totaal(verg_contour, bron="kwetsbare_functies", metriek="Aantal projecten", jaartal=jaartal),
            "deels",
        ),
        (
            "renovatie_totaal",
            _verg_totaal(verg_contour, handeling="Verbouwen of hergebruik", metriek="Aantal projecten", jaartal=jaartal),
            "deels",
        ),
        ("transacties_percelen", _transactie_totaal(transacties, ["industrie_terrein"]), "deels"),
        ("transacties_woningen", _transactie_totaal(transacties, ["woningen", "appartementen"]), "deels"),
    ]
    for teller_id, waarde, status in nat_records:
        records.append(
            {"contour": "_totaal", "teller_id": teller_id, "waarde": waarde, "jaar": jaartal, "status": status}
        )

    return pd.DataFrame(records)


def bereken_alle_flow_rates(
    lden: pd.DataFrame,
    verg_contour: pd.DataFrame,
    transacties: pd.DataFrame,
    tellers: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Compute all measure flow rates (aggregate over contours)."""
    if tellers is None:
        tellers = bouw_tellers_contour(lden, verg_contour, transacties)

    stocks = bouw_stocks_contour(lden)

    def noemer(stock: str) -> float:
        return float(stocks[stock].sum())

    def teller_nat(teller_id: str) -> float:
        mask = (tellers["teller_id"] == teller_id) & (tellers["contour"] == "_totaal")
        if mask.any():
            return float(tellers.loc[mask, "waarde"].iloc[0])
        return float(tellers.loc[tellers["teller_id"] == teller_id, "waarde"].sum())

    woongebied_teller = float(lden[KOL_WOONGEBIED_AANDUIDING].sum() / 5)
    onbeb_onbeb = noemer("onbebouwde_onbebouwbare_percelen")
    onbeb_beb = noemer("onbebouwde_bebouwbare_percelen")
    niet_geo = noemer("bewoonde_niet_geïsoleerde_woning")
    geo = noemer("bewoonde_geïsoleerde_woning")

    nieuwbouw_we = teller_nat("vergunde_wooneenheden_nieuwbouw_totaal")
    kwetsbaar = teller_nat("vergunningen_kwetsbare_groep")
    renovatie = teller_nat("renovatie_totaal")
    r_plus = renovatie * RENOVATIE_ISO_AANDEEL
    r_min = renovatie * (1 - RENOVATIE_ISO_AANDEEL)
    trans_perc = teller_nat("transacties_percelen")
    trans_won = teller_nat("transacties_woningen")

    results: list[FlowRateResult] = [
        FlowRateResult("verkavelingsverbod", 0.0, 0.0, 0, onbeb_beb, "ok", "geen hinder-effect"),
        FlowRateResult(
            "woongebiedverbod",
            bereken_flow_rate(woongebied_teller, onbeb_onbeb),
            bereken_flow_rate(woongebied_teller, onbeb_onbeb),
            woongebied_teller,
            onbeb_onbeb,
            "ok",
        ),
        FlowRateResult(
            "aankoopbeleid_percelen",
            0.0,
            bereken_flow_rate(AANKOOP_AANDEEL * trans_perc, onbeb_beb),
            AANKOOP_AANDEEL * trans_perc,
            onbeb_beb,
            "deels",
            "geen contour-split transacties",
        ),
        FlowRateResult(
            "voorkooprecht_percelen",
            0.0,
            bereken_flow_rate(trans_perc, onbeb_beb),
            trans_perc,
            onbeb_beb,
            "deels",
        ),
        FlowRateResult("onteigening_percelen", 0.0, ONTEIGING_RATE, ONTEIGING_RATE, onbeb_beb, "ok", "vast 5%"),
        FlowRateResult(
            "verbod_kleine_woning",
            bereken_flow_rate(nieuwbouw_we, onbeb_beb),
            bereken_flow_rate(nieuwbouw_we, onbeb_beb),
            nieuwbouw_we,
            onbeb_beb,
            "deels",
        ),
        FlowRateResult("verbod_grote_woning", 0.01, 0.0, 0, onbeb_beb, "ok", "beleidskeuze active=0"),
        FlowRateResult(
            "verbod_kwetsbare_groep",
            bereken_flow_rate(kwetsbaar, onbeb_beb),
            bereken_flow_rate(kwetsbaar, onbeb_beb),
            kwetsbaar,
            onbeb_beb,
            "deels",
        ),
        FlowRateResult("woonverdichtingsverbod_niet_geïsoleerde_woningen", 0.01, 0.0, 0, niet_geo, "ok", "beleidskeuze"),
        FlowRateResult("woonverdichtingsverbod_geïsoleerde_woningen", 0.01, 0.0, 0, geo, "ok", "beleidskeuze"),
        FlowRateResult(
            "aankoopbeleid_niet_geïsoleerde_woningen",
            0.0,
            bereken_flow_rate(AANKOOP_AANDEEL * trans_won, niet_geo),
            AANKOOP_AANDEEL * trans_won,
            niet_geo,
            "deels",
        ),
        FlowRateResult(
            "aankoopbeleid_geïsoleerde_woningen",
            0.0,
            bereken_flow_rate(AANKOOP_AANDEEL * trans_won, geo),
            AANKOOP_AANDEEL * trans_won,
            geo,
            "deels",
        ),
        FlowRateResult(
            "voorkooprecht_niet_geïsoleerde_woningen",
            0.0,
            bereken_flow_rate(trans_won, niet_geo),
            trans_won,
            niet_geo,
            "deels",
        ),
        FlowRateResult(
            "voorkooprecht_geïsoleerde_woningen",
            0.0,
            bereken_flow_rate(trans_won, geo),
            trans_won,
            geo,
            "deels",
        ),
        FlowRateResult("onteigening_niet_geïsoleerde_woningen", 0.0, ONTEIGING_RATE, ONTEIGING_RATE, niet_geo, "ok"),
        FlowRateResult("onteigening_geïsoleerde_woningen", 0.0, ONTEIGING_RATE, ONTEIGING_RATE, geo, "ok"),
        FlowRateResult(
            "isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning",
            0.5,
            0.0,
            0,
            0,
            "deels",
            "dynamische noemer nieuwe_woning",
        ),
        FlowRateResult(
            "isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning",
            1.0,
            1.0,
            0,
            0,
            "deels",
            "dynamische noemer nieuwe_woning",
        ),
        FlowRateResult(
            "renovatie_zonder_maatregel",
            bereken_flow_rate(r_plus, niet_geo),
            0.0,
            r_plus,
            niet_geo,
            "deels",
        ),
        FlowRateResult(
            "verplicht_isoleren_renovatie",
            0.0,
            bereken_flow_rate(r_plus + r_min, niet_geo),
            r_plus + r_min,
            niet_geo,
            "deels",
        ),
        FlowRateResult(
            "gesubsidieerd_isolatieprogramma",
            0.0,
            bereken_flow_rate(2 * (r_plus + r_min), niet_geo),
            2 * (r_plus + r_min),
            niet_geo,
            "deels",
        ),
        FlowRateResult(
            "gestuurd_isolatieprogramma",
            0.0,
            bereken_flow_rate(4 * (r_plus + r_min), niet_geo),
            4 * (r_plus + r_min),
            niet_geo,
            "deels",
        ),
        FlowRateResult("aanleg_geluidsbuffers", 0.0, 0.0, 0, niet_geo, "placeholder"),
        FlowRateResult("compensatie_buitenzone", 0.0, 0.0, 0, niet_geo, "ok"),
        FlowRateResult("compensatie_verhuis", 0.0, 0.0, 0, niet_geo, "ok"),
        FlowRateResult("versterken_sociale_cohesie", 0.0, 0.0, 0, niet_geo, "ok"),
        FlowRateResult("vergroenen_leefomgeving", 0.0, 0.0, 0, niet_geo, "ok"),
    ]

    return pd.DataFrame([r.__dict__ for r in results])


def valideer_flow_rates(flow_rates: pd.DataFrame) -> pd.DataFrame:
    """Validation report: rates > 1 flagged."""
    rapport = flow_rates.copy()
    rapport["rate_ok"] = (
        (rapport["flow_rate_baseline"] <= 1)
        & (rapport["flow_rate_active"] <= 1)
        | rapport["measure_id"].str.startswith("onteigening")
    )
    return rapport
