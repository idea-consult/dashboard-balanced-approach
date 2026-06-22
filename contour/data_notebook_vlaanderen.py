"""Expliciete notebook-code: FLOW-variabelen per db-band, alleen Vlaanderen."""

from __future__ import annotations

from dataclasses import dataclass

from contour.columns import (
    KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR,
    KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR,
)
from contour.data_notebook import DATA_STAP_VOLGORDE
from contour.vergunningen import JAAR_TELLERS_VENSTER, VERGUNNINGEN_STAP_BEREKENING

REGIO = "vlaanderen"
TABEL = "vla"

VLAANDEREN_SETUP_CODE = '''\
from pathlib import Path
import pandas as pd

from contour.columns import WOONGEBIED_KOLOMMEN
from contour.consolidate import JAAR_TELLERS, PCT_GEISOLEERD, PCT_NIET_GEISOLEERD, series_op_index
from contour.vergunningen import gemiddelde_jaarlijkse_vergunningen, gem_wooneenheden_per_vergunning_gemiddelde
from contour.loaders import (
    lees_contour_vlaanderen,
    lees_sector_contour_beide,
    lees_transacties,
    lees_vergunningen,
)
from contour.schema import FLOW_KOLOMMEN, assert_flow_schema, init_contour_index
from contour.spatial import (
    conversietabel_gemeente_naar_db,
    koppel_conversie_aan_contourband,
    verdeel_gemeente_naar_contour,
)
from contour.vergunningen import combineer_vergunningen_lang, gemiddelde_jaarlijkse_vergunningen


def _naar_numeriek(df, kolommen):
    out = df.copy()
    for k in kolommen:
        if k in out.columns:
            out[k] = pd.to_numeric(out[k], errors="coerce").fillna(0)
    return out


raw_vla_lden, _raw_vla_lnight = lees_contour_vlaanderen()
raw_vla_lden = _naar_numeriek(raw_vla_lden, WOONGEBIED_KOLOMMEN)
transacties = lees_transacties()

vla = init_contour_index(raw_vla_lden)
'''


@dataclass(frozen=True)
class VlaStapDefinitie:
    stap_nr: int
    stap_id: str
    titel: str
    uitleg: str
    berekening: str
    bron: str


def md_vla(info: VlaStapDefinitie) -> str:
    return (
        f"### Stap {info.stap_nr} — `{info.stap_id}`\n\n"
        f"#### Uitleg\n\n{info.uitleg}\n\n"
        f"#### Bron (Vlaanderen)\n\n{info.bron}\n\n"
        f"#### Berekening\n\n{info.berekening}"
    )


def stap_definitie_vla(stap_id: str) -> VlaStapDefinitie:
    stap_nr = DATA_STAP_VOLGORDE.index(stap_id) if stap_id in DATA_STAP_VOLGORDE else -1
    defs: dict[str, VlaStapDefinitie] = {
        "0_index": VlaStapDefinitie(
            stap_nr, "db_ondergrens", "Index db_ondergrens",
            "30 geluidsbanden (dB 45–74) uit de Vlaanderen-contour.",
            "Index uit `contour_vlaanderen_stocks.xlsx` (sheet `lden`).",
            "`data/contour_vlaanderen_stocks.xlsx`",
        ),
        "inwoners_per_contour": VlaStapDefinitie(
            stap_nr, "inwoners_per_contour", "Inwoners Vlaanderen",
            "Inwoners **in Vlaanderen** per geluidsband (geen Brussel).",
            "`vla['inwoners_per_contour'] = inwoners` uit Vlaanderen-contour.",
            "`contour_vlaanderen_stocks.xlsx` → `inwoners`",
        ),
        KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR: VlaStapDefinitie(
            stap_nr, KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR, "Woongebied-aanduiding (5 jr)",
            "Bebouwbare percelen door woongebied-aanduiding (cumulatief 5 jaar).",
            "Rechtstreeks uit Vlaanderen-contour.",
            "`contour_vlaanderen_stocks.xlsx`",
        ),
        KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR: VlaStapDefinitie(
            stap_nr, KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR, "Woongebied-schrapping (5 jr)",
            "Niet-bebouwbare percelen door woongebied-schrapping (cumulatief 5 jaar).",
            "Rechtstreeks uit Vlaanderen-contour.",
            "`contour_vlaanderen_stocks.xlsx`",
        ),
        "bewoonde_niet_geïsoleerde_woning": VlaStapDefinitie(
            stap_nr, "bewoonde_niet_geïsoleerde_woning", "Niet-geïsoleerde woningen",
            "Stock niet-geïsoleerde woningen in Vlaanderen.",
            "`aantal_woningen` × 0,80 (placeholder isolatiesplit).",
            "`contour_vlaanderen_stocks.xlsx` → `aantal_woningen`",
        ),
        "bewoonde_geïsoleerde_woning": VlaStapDefinitie(
            stap_nr, "bewoonde_geïsoleerde_woning", "Geïsoleerde woningen",
            "Stock geïsoleerde woningen in Vlaanderen.",
            "`aantal_woningen` × 0,20.",
            "Zelfde bron als stap 4",
        ),
        "transacties_en_capakey_prijzen": VlaStapDefinitie(
            stap_nr, "transacties_en_capakey_prijzen", "Transacties & prijzen",
            "Voorbereiding transactietellers en prijskolommen.",
            "Prijs per transactie → per CaPaKey → koppeling via `capakey_contour_lden.csv`.",
            "`data/transacties_vastgoed/`, `data/capakey_contour_lden.csv`",
        ),
        "prijs_bewoonde_niet_geïsoleerde_woning": VlaStapDefinitie(
            stap_nr, "prijs_bewoonde_niet_geïsoleerde_woning", "Prijs woning",
            "Gewogen gemiddelde transactieprijs woningen per band.",
            "CaPaKey-prijs gewogen naar contourband.",
            "`transacties_woningen.csv`, `transacties_appartementen.csv`",
        ),
        "vergunde_wooneenheden_nieuwbouw": VlaStapDefinitie(
            stap_nr,
            "vergunde_wooneenheden_nieuwbouw",
            "Vergunde wooneenheden (nieuwbouw)",
            f"**Jaarlijks gemiddelde** ({JAAR_TELLERS_VENSTER}) van vergunde wooneenheden nieuwbouw per dB-band. "
            "Input voor flow rate `verbod_kleine_woning`.",
            VERGUNNINGEN_STAP_BEREKENING
            + "\n\nFilter: `handeling == 'Nieuwbouw'` en `metriek == 'Aantal wooneenheden'`.",
            "`vergunningen_omgevingsloket_2026_lang.csv` (+ kwetsbare/verkaveling in `verg_combined`)",
        ),
        "gem_wooneenheden_per_vergunning": VlaStapDefinitie(
            stap_nr,
            "gem_wooneenheden_per_vergunning",
            "Gem. wooneenheden per vergunning",
            f"**Landelijk hulpcijfer** (zelfde waarde in elke dB-band): gemiddelde over {JAAR_TELLERS_VENSTER} "
            "van de jaarlijkse ratio `(som wooneenheden / som projecten)` voor omgevingsloket. "
            "Nog niet gebruikt in flow-formules.",
            f"`gem_wooneenheden_per_vergunning_gemiddelde(verg_combined)` — per kalenderjaar ratio, "
            f"daarna gemiddelde over 6 jaren (jaren zonder data = ratio 0).",
            "`vergunningen_omgevingsloket_2026_lang.csv`",
        ),
        "vergunningen_kwetsbare_groep": VlaStapDefinitie(
            stap_nr,
            "vergunningen_kwetsbare_groep",
            "Vergunningen kwetsbare groep",
            f"**Jaarlijks gemiddelde** ({JAAR_TELLERS_VENSTER}) kwetsbare-functievergunningen per band. "
            "Input voor `verbod_kwetsbare_groep`.",
            VERGUNNINGEN_STAP_BEREKENING + "\n\nFilter: `bron == 'kwetsbare_functies'`.",
            "`vergunningen_kwetsbare_functies_2026_lang.csv`",
        ),
        "renovatie_totaal": VlaStapDefinitie(
            stap_nr,
            "renovatie_totaal",
            "Renovatievergunningen (totaal)",
            f"**Jaarlijks gemiddelde** ({JAAR_TELLERS_VENSTER}) renovatievergunningen per band. "
            "Basis voor R+ / R− en renovatiemaatregelen.",
            VERGUNNINGEN_STAP_BEREKENING
            + "\n\nFilter: `handeling == 'Verbouwen of hergebruik'` (alle metrieken; zie FLOW §2.3).",
            "`vergunningen_omgevingsloket_2026_lang.csv`",
        ),
    }
    if stap_id in defs:
        d = defs[stap_id]
        return VlaStapDefinitie(stap_nr, d.stap_id, d.titel, d.uitleg, d.berekening, d.bron)
    return VlaStapDefinitie(
        stap_nr, stap_id, stap_id,
        f"FLOW-variabele `{stap_id}` — Vlaanderen per db-band.",
        "Zie STOCKS_EN_FLOWS_BEREKENEN.md §2.",
        "Vlaanderen-contour / vergunningen Vlaamse ring / transacties",
    )


def _show(kol: str) -> str:
    return f'vla[[{kol!r}]].head()'


def stap_notebook_code_vla(stap_id: str) -> str:
    if stap_id == "0_index":
        return "vla = init_contour_index(raw_vla_lden)\nlist(vla.columns)"

    if stap_id == "inwoners_per_contour":
        return (
            "idx = vla.index\n"
            "vla['inwoners_per_contour'] = series_op_index(raw_vla_lden, 'inwoners', idx)\n"
            + _show("inwoners_per_contour")
        )

    if stap_id in (KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR, KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR):
        return (
            f"idx = vla.index\n"
            f"vla[{stap_id!r}] = series_op_index(raw_vla_lden, {stap_id!r}, idx)\n"
            + _show(stap_id)
        )

    if stap_id == "bewoonde_niet_geïsoleerde_woning":
        return (
            "idx = vla.index\n"
            "_woningen = series_op_index(raw_vla_lden, 'aantal_woningen', idx)\n"
            "vla['bewoonde_niet_geïsoleerde_woning'] = _woningen * PCT_NIET_GEISOLEERD\n"
            + _show("bewoonde_niet_geïsoleerde_woning")
        )

    if stap_id == "bewoonde_geïsoleerde_woning":
        return (
            "vla['bewoonde_geïsoleerde_woning'] = _woningen * PCT_GEISOLEERD\n"
            + _show("bewoonde_geïsoleerde_woning")
        )

    if stap_id in {
        "onbebouwde_bebouwbare_percelen", "onbebouwde_onbebouwbare_percelen", "nieuwe_woning",
        "perceel_eigendom_overheid", "woning_eigendom_overheid", "R+", "R−",
        "nieuwbouw_geïsoleerd", "nieuwbouw_niet_geïsoleerd", "potentieel_isoleerbare_woningen",
    }:
        return f"vla[{stap_id!r}] = 0.0  # placeholder\n" + _show(stap_id)

    if stap_id == "vergunde_wooneenheden_nieuwbouw":
        return (
            "sector_lden, _ = lees_sector_contour_beide()\n"
            "conversie_lden = conversietabel_gemeente_naar_db(sector_lden, indicator='lden')\n"
            "conversie_lden_band = koppel_conversie_aan_contourband(conversie_lden, vla)\n"
            "verg_omg, verg_kwets, verg_verk = lees_vergunningen()\n"
            "verg_combined = combineer_vergunningen_lang(\n"
            "    verg_omg.assign(bron='omgevingsloket'),\n"
            "    verg_kwets.assign(bron='kwetsbare_functies'),\n"
            "    verg_verk.assign(bron='verkaveling'),\n"
            ")\n"
            "verg_gem = gemiddelde_jaarlijkse_vergunningen(verg_combined)\n"
            "verg_contour, _verg_niet = verdeel_gemeente_naar_contour(\n"
            "    verg_gem, conversie_lden_band, jaartal=JAAR_TELLERS\n"
            ")\n"
            "idx = vla.index\n"
            "df_verg = verg_contour[verg_contour['jaar_indiening'].astype(str) == str(JAAR_TELLERS)].copy()\n"
            "\n"
            "def som_per_band(mask):\n"
            "    subset = df_verg.loc[mask]\n"
            "    if subset.empty:\n"
            "        return pd.Series(0.0, index=idx)\n"
            "    return subset.groupby('db_ondergrens')['waarde'].sum().reindex(idx).fillna(0)\n"
            "\n"
            "vla['vergunde_wooneenheden_nieuwbouw'] = som_per_band(\n"
            "    (df_verg['handeling'] == 'Nieuwbouw') & (df_verg['metriek'] == 'Aantal wooneenheden')\n"
            ")\n"
            + _show("vergunde_wooneenheden_nieuwbouw")
        )

    if stap_id == "gem_wooneenheden_per_vergunning":
        return (
            "_gem_we = gem_wooneenheden_per_vergunning_gemiddelde(verg_combined)\n"
            "vla['gem_wooneenheden_per_vergunning'] = _gem_we\n"
            "pd.DataFrame({'gem_wooneenheden_per_vergunning': [_gem_we], 'periode': [str(JAAR_TELLERS)]})"
        )

    if stap_id == "vergunningen_kwetsbare_groep":
        return (
            "vla['vergunningen_kwetsbare_groep'] = som_per_band(df_verg['bron'] == 'kwetsbare_functies')\n"
            + _show("vergunningen_kwetsbare_groep")
        )

    if stap_id == "renovatie_totaal":
        return (
            "vla['renovatie_totaal'] = som_per_band(df_verg['handeling'] == 'Verbouwen of hergebruik')\n"
            + _show("renovatie_totaal")
        )

    if stap_id == "transacties_en_capakey_prijzen":
        return (
            "from contour.prices import SEGMENTEN_PER_PRIJSKOLOM, laad_capakey_contour_extern\n"
            "\n"
            "tx = transacties.copy()\n"
            "tx['capakey'] = tx['capakey'].astype(str)\n"
            "tx['aantal_transacties'] = pd.to_numeric(tx['sum_ParcelsNumber'], errors='coerce').fillna(0)\n"
            "p50 = pd.to_numeric(tx['avg_PriceP50'], errors='coerce')\n"
            "m2 = pd.to_numeric(tx['average_price_m2'], errors='coerce')\n"
            "opp = pd.to_numeric(tx['avg_ParcelsAreaP50'], errors='coerce')\n"
            "tx['prijs_euro'] = p50.where(p50 > 0, m2 * opp)\n"
            "tx['prijs_euro'] = tx['prijs_euro'].where(tx['prijs_euro'] > 0)\n"
            "\n"
            "capakey_prijzen = pd.DataFrame({'capakey': tx['capakey'].unique()})\n"
            "for _pk, _seg in SEGMENTEN_PER_PRIJSKOLOM.items():\n"
            "    _s = tx[tx['segment'].isin(_seg)]\n"
            "    _gw = f'gewicht_{_pk}'\n"
            "    _tot = _s.groupby('capakey', as_index=False)['aantal_transacties'].sum().rename(\n"
            "        columns={'aantal_transacties': _gw}\n"
            "    )\n"
            "    _mp = _s[_s['prijs_euro'].notna() & (_s['aantal_transacties'] > 0)]\n"
            "    if _mp.empty:\n"
            "        _mp = _s[_s['prijs_euro'].notna()]\n"
            "    if _mp.empty:\n"
            "        capakey_prijzen = capakey_prijzen.merge(_tot.assign(**{_pk: pd.NA}), on='capakey', how='left')\n"
            "        continue\n"
            "    _mp = _mp.assign(_w=_mp['aantal_transacties'].clip(lower=1))\n"
            "    _agg = _mp.assign(_pw=_mp['prijs_euro'] * _mp['_w']).groupby('capakey', as_index=False).agg(\n"
            "        _pw=('_pw', 'sum'), _w=('_w', 'sum')\n"
            "    )\n"
            "    _agg[_pk] = _agg['_pw'] / _agg['_w']\n"
            "    capakey_prijzen = capakey_prijzen.merge(\n"
            "        _tot.merge(_agg[['capakey', _pk]], on='capakey', how='left'), on='capakey', how='left'\n"
            "    )\n"
            "capakey_prijzen['prijs_bewoonde_geïsoleerde_woning'] = capakey_prijzen['prijs_bewoonde_niet_geïsoleerde_woning']\n"
            "capakey_prijzen['gewicht_prijs_bewoonde_geïsoleerde_woning'] = capakey_prijzen[\n"
            "    'gewicht_prijs_bewoonde_niet_geïsoleerde_woning'\n"
            "]\n"
            "\n"
            "capakey_mapping = laad_capakey_contour_extern()\n"
            "if not capakey_mapping.empty:\n"
            "    capakey_mapping['capakey'] = capakey_mapping['capakey'].astype(str)\n"
            "    capakey_mapping['gewicht_ruimtelijk'] = capakey_mapping['gewicht_ruimtelijk'].fillna(1.0)\n"
            "\n"
            "def agg_transacties(segmenten):\n"
            "    _map = capakey_mapping[['capakey', 'db_ondergrens']] if not capakey_mapping.empty else capakey_mapping\n"
            "    gekoppeld = tx.merge(_map, on='capakey', how='inner')\n"
            "    subset = gekoppeld[gekoppeld['segment'].isin(segmenten)]\n"
            "    if subset.empty:\n"
            "        return pd.Series(0.0, index=vla.index)\n"
            "    return subset.groupby('db_ondergrens')['aantal_transacties'].sum().reindex(vla.index).fillna(0)\n"
            "\n"
            "capakey_prijzen.head()"
        )

    if stap_id == "alle_transacties_percelen":
        return (
            "tx_percelen = agg_transacties(['industrie_terrein', 'industrie_bebouwd'])\n"
            "vla['alle_transacties_percelen'] = tx_percelen\n"
            + _show("alle_transacties_percelen")
        )

    if stap_id == "alle_verkopen_onbebouwde_bebouwbare_percelen":
        return (
            "vla['alle_verkopen_onbebouwde_bebouwbare_percelen'] = tx_percelen\n"
            + _show("alle_verkopen_onbebouwde_bebouwbare_percelen")
        )

    if stap_id == "alle_transacties_woningen":
        return (
            "tx_woningen = agg_transacties(['woningen', 'appartementen'])\n"
            "vla['alle_transacties_woningen'] = tx_woningen\n"
            + _show("alle_transacties_woningen")
        )

    if stap_id == "alle_verkopen_woningen":
        return (
            "vla['alle_verkopen_woningen'] = tx_woningen\n"
            + _show("alle_verkopen_woningen")
        )

    if stap_id in {
        "prijs_onbebouwde_bebouwbare_percelen",
        "prijs_onbebouwde_onbebouwbare_percelen",
        "prijs_bewoonde_niet_geïsoleerde_woning",
    }:
        return _prijs_code_vla(stap_id)

    if stap_id == "prijs_bewoonde_geïsoleerde_woning":
        return (
            "vla['prijs_bewoonde_geïsoleerde_woning'] = vla['prijs_bewoonde_niet_geïsoleerde_woning']\n"
            + _show("prijs_bewoonde_geïsoleerde_woning")
        )

    if stap_id == "28_flow_volgorde":
        return (
            "vla = vla[list(FLOW_KOLOMMEN)]\n"
            "assert_flow_schema(vla)\n"
            "list(vla.columns)"
        )

    raise KeyError(stap_id)


def _prijs_code_vla(prijs_kolom: str) -> str:
    return (
        f"_pk = {prijs_kolom!r}\n"
        "_gw = f'gewicht_{_pk}'\n"
        "_gek = capakey_mapping.merge(capakey_prijzen[['capakey', _pk, _gw]], on='capakey', how='inner')\n"
        "_gek = _gek[_gek[_pk].notna()].copy()\n"
        "_gek['w'] = _gek['gewicht_ruimtelijk'] * _gek[_gw].clip(lower=1)\n"
        "\n"
        "def _gewogen_gem(p, g):\n"
        "    m = p.notna() & (g > 0)\n"
        "    return None if not m.any() else float((p[m] * g[m]).sum() / g[m].sum())\n"
        "\n"
        "_fb = _gewogen_gem(capakey_prijzen[_pk], capakey_prijzen[_gw].clip(lower=1))\n"
        "_band = _gek.groupby('db_ondergrens').apply(\n"
        "    lambda r: _gewogen_gem(r[_pk], r['w']), include_groups=False\n"
        ")\n"
        f"vla[_pk] = _band.reindex(vla.index)\n"
        "if _fb is not None:\n"
        f"    vla[_pk] = vla[_pk].fillna(_fb)\n"
        + _show(prijs_kolom)
    )


def stap_grafiek_code_vla(stap_id: str) -> str:
    info = stap_definitie_vla(stap_id)
    titel = f"Vlaanderen — stap {info.stap_nr}: {info.titel}"

    if stap_id == "0_index":
        return (
            "from contour.notebook_viz import staafdiagram_reeks\n\n"
            f"staafdiagram_reeks(pd.Series(1, index=vla.index), titel={titel!r}, y_label='band')"
        )
    if stap_id == "transacties_en_capakey_prijzen":
        return (
            "from contour.notebook_viz import staafdiagram_reeks\n\n"
            "_n = capakey_mapping.groupby('db_ondergrens').size().reindex(vla.index).fillna(0) if not capakey_mapping.empty else pd.Series(0, index=vla.index)\n"
            f"staafdiagram_reeks(_n, titel={titel!r} + ' — CaPaKeys', y_label='aantal')"
        )
    if stap_id == "28_flow_volgorde":
        return (
            "from contour.notebook_viz import toon_staaf_per_contour\n\n"
            f"toon_staaf_per_contour(vla, 'inwoners_per_contour', titel={titel!r})"
        )
    if stap_id == "gem_wooneenheden_per_vergunning":
        return (
            "from contour.notebook_viz import staafdiagram_reeks\n\n"
            f"_c = pd.Series(vla['gem_wooneenheden_per_vergunning'].iloc[0], index=vla.index)\n"
            f"staafdiagram_reeks(_c, titel={titel!r}, y_label='gem. WE/vergunning')"
        )
    return (
        "from contour.notebook_viz import toon_staaf_per_contour\n\n"
        f"toon_staaf_per_contour(vla, {stap_id!r}, titel={titel!r})"
    )
