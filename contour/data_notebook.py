"""Expliciete notebook-code voor stapsgewijze opbouw lden/lnight (FLOW §2)."""

from __future__ import annotations

from dataclasses import dataclass

from contour.columns import (
    KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR,
    KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR,
)
from contour.vergunningen import (
    JAAR_TELLERS_VENSTER,
    VERGUNNINGEN_STAP_BEREKENING,
)

DATA_SETUP_CODE = '''\
from pathlib import Path
import pandas as pd

from contour.columns import (
    KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR,
    KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR,
    WOONGEBIED_KOLOMMEN,
)
from contour.consolidate import JAAR_TELLERS, PCT_GEISOLEERD, PCT_NIET_GEISOLEERD, series_op_index
from contour.vergunningen import gemiddelde_jaarlijkse_vergunningen, gem_wooneenheden_per_vergunning_gemiddelde
from contour.loaders import (
    lees_brussel_inwoners_per_db,
    lees_brussel_sector,
    lees_contour_vlaanderen,
    lees_sector_contour_beide,
    lees_transacties,
    lees_vergunningen,
)
from contour.schema import FLOW_KOLOMMEN, assert_flow_schema, init_lden_lnight_index
from contour.spatial import (
    conversietabel_gemeente_naar_db,
    koppel_conversie_aan_contourband,
    verdeel_gemeente_naar_contour,
)
from contour.vergunningen import (
    combineer_vergunningen_lang,
    gem_wooneenheden_per_vergunning_gemiddelde,
    gemiddelde_jaarlijkse_vergunningen,
)


def _naar_numeriek(df, kolommen):
    out = df.copy()
    for k in kolommen:
        if k in out.columns:
            out[k] = pd.to_numeric(out[k], errors="coerce").fillna(0)
    return out


raw_vlaanderen_lden, raw_vlaanderen_lnight = lees_contour_vlaanderen()
raw_vlaanderen_lden = _naar_numeriek(raw_vlaanderen_lden, WOONGEBIED_KOLOMMEN)
raw_vlaanderen_lnight = _naar_numeriek(raw_vlaanderen_lnight, WOONGEBIED_KOLOMMEN)
lden_bru_db, lnight_bru_db = lees_brussel_inwoners_per_db()
brussel_lden, _ = lees_brussel_sector()
transacties = lees_transacties()

lden, lnight = init_lden_lnight_index(raw_vlaanderen_lden, raw_vlaanderen_lnight)
'''


@dataclass(frozen=True)
class DataStapDefinitie:
    stap_nr: int
    stap_id: str
    titel: str
    uitleg: str
    berekening: str
    bronnen: str


DATA_STAP_VOLGORDE: tuple[str, ...] = (
    "0_index",
    "inwoners_per_contour",
    KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR,
    KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR,
    "bewoonde_niet_geïsoleerde_woning",
    "bewoonde_geïsoleerde_woning",
    "onbebouwde_bebouwbare_percelen",
    "onbebouwde_onbebouwbare_percelen",
    "nieuwe_woning",
    "perceel_eigendom_overheid",
    "woning_eigendom_overheid",
    "vergunde_wooneenheden_nieuwbouw",
    "gem_wooneenheden_per_vergunning",
    "vergunningen_kwetsbare_groep",
    "renovatie_totaal",
    "transacties_en_capakey_prijzen",
    "alle_transacties_percelen",
    "alle_verkopen_onbebouwde_bebouwbare_percelen",
    "alle_transacties_woningen",
    "alle_verkopen_woningen",
    "prijs_onbebouwde_bebouwbare_percelen",
    "prijs_onbebouwde_onbebouwbare_percelen",
    "prijs_bewoonde_niet_geïsoleerde_woning",
    "prijs_bewoonde_geïsoleerde_woning",
    "R+",
    "R−",
    "nieuwbouw_geïsoleerd",
    "nieuwbouw_niet_geïsoleerd",
    "potentieel_isoleerbare_woningen",
    "28_flow_volgorde",
)


def _md(info: DataStapDefinitie) -> str:
    return (
        f"### Stap {info.stap_nr} — `{info.stap_id}`\n\n"
        f"#### Uitleg\n\n{info.uitleg}\n\n"
        f"#### Bron\n\n{info.bronnen}\n\n"
        f"#### Berekenmethode\n\n{info.berekening}"
    )


def stap_definitie(stap_id: str) -> DataStapDefinitie:
    """Metadata voor één notebook-stap."""
    stap_nr = DATA_STAP_VOLGORDE.index(stap_id) if stap_id in DATA_STAP_VOLGORDE else -1
    defs: dict[str, DataStapDefinitie] = {
        "0_index": DataStapDefinitie(
            stap_nr,
            "db_ondergrens",
            "Index db_ondergrens",
            "Startdataframe met de 30 geluidsbanden (dB-ondergrens 45–74) als index. Nog geen FLOW-variabelen.",
            "De banden worden overgenomen uit de Vlaanderen Lden-contour; Lnight gebruikt dezelfde bandindeling.",
            "`data/contour_vlaanderen_stocks.xlsx` — kolom `db_ondergrens`",
        ),
        "inwoners_per_contour": DataStapDefinitie(
            stap_nr,
            "inwoners_per_contour",
            "inwoners_per_contour",
            "Totaal aantal inwoners per geluidscontourband (Vlaanderen + Brussel). KPI / kostengewicht; geen flow-teller.",
            "**Vlaanderen:** `inwoners` per band uit contour-Excel.\n\n"
            "**Brussel:** inwoners per sector → dB-band via `lees_brussel_inwoners_per_db()`.\n\n"
            "**Totaal:** `inwoners_vlaanderen + inwoners_brussel`.",
            "`contour_vlaanderen_stocks.xlsx`, `inwoners_brussel_sector_contour_2024.xlsx`",
        ),
        KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR: DataStapDefinitie(
            2,
            KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR,
            KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR,
            "Cumulatief aantal bebouwbare percelen gecreëerd door woongebied-aanduiding (5 jr).",
            "Waarde per `db_ondergrens` overnemen uit Vlaanderen-contour (`series_op_index`).",
            "`contour_vlaanderen_stocks.xlsx`",
        ),
        KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR: DataStapDefinitie(
            3,
            KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR,
            KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR,
            "Cumulatief aantal niet-bebouwbare percelen door woongebied-schrapping (5 jr).",
            "Waarde per `db_ondergrens` overnemen uit Vlaanderen-contour.",
            "`contour_vlaanderen_stocks.xlsx`",
        ),
        "bewoonde_niet_geïsoleerde_woning": DataStapDefinitie(
            4,
            "bewoonde_niet_geïsoleerde_woning",
            "bewoonde_niet_geïsoleerde_woning",
            "Stock bewoonde niet-geïsoleerde woningen per band.",
            "1. Woningen Vlaanderen uit Excel.\n"
            "2. Woningen Brussel = `inwoners_brussel / gem_inwoners_per_woning_vlaanderen` (fallback 2,0).\n"
            "3. Totaal × `PCT_NIET_GEISOLEERD` (0,80).",
            "`contour_vlaanderen_stocks.xlsx`, Brusselse inwoners per dB",
        ),
        "bewoonde_geïsoleerde_woning": DataStapDefinitie(
            5,
            "bewoonde_geïsoleerde_woning",
            "bewoonde_geïsoleerde_woning",
            "Stock bewoonde geïsoleerde woningen per band.",
            "`won_totaal_lden × PCT_GEISOLEERD` (0,20); idem lnight.",
            "Zelfde bronnen als stap 4",
        ),
        "prijs_bewoonde_niet_geïsoleerde_woning": DataStapDefinitie(
            stap_nr,
            "prijs_bewoonde_niet_geïsoleerde_woning",
            "prijs_bewoonde_niet_geïsoleerde_woning",
            "Eenheidsprijs bewoonde niet-geïsoleerde woning per band (€).",
            "1. Transactieprijs per CaPaKey: mediaan `avg_PriceP50`, anders `average_price_m2 × avg_ParcelsAreaP50`.\n"
            "2. Segmenten `woningen` + `appartementen`: gewogen gemiddelde prijs per CaPaKey (gewicht = aantal transacties).\n"
            "3. Koppel CaPaKey → `db_ondergrens` via `capakey_mapping` (ruimtelijk gewicht × transactiegewicht).\n"
            "4. Gewogen gemiddelde prijs per band; fallback = landelijk gewogen gemiddelde.",
            "`transacties_woningen.csv`, `transacties_appartementen.csv`, CaPaKey-contour mapping",
        ),
        "prijs_bewoonde_geïsoleerde_woning": DataStapDefinitie(
            stap_nr,
            "prijs_bewoonde_geïsoleerde_woning",
            "prijs_bewoonde_geïsoleerde_woning",
            "Eenheidsprijs bewoonde geïsoleerde woning per band (€).",
            "**Beleidsaanname:** geen isolatie-split in transactiedata → zelfde prijs als niet-geïsoleerde woning (stap daarvoor).",
            "Zelfde transacties als `prijs_bewoonde_niet_geïsoleerde_woning`",
        ),
        "transacties_en_capakey_prijzen": DataStapDefinitie(
            stap_nr,
            "transacties_en_capakey_prijzen",
            "Voorbereiding transacties, CaPaKey-prijzen en mapping",
            "Eénmalige voorbereiding voor transactietellers (stappen 16–19) en prijskolommen (stappen 20–23).",
            "1. Prijs per transactie (`prijs_euro`).\n"
            "2. Gewogen gemiddelde prijs per CaPaKey per prijstype.\n"
            "3. CaPaKey → contour via extern bestand + Brusselse sectorfallback.",
            "`data/transacties_vastgoed/`, optioneel `data/capakey_contour_lden.csv`, Brussel sectorbestand",
        ),
        "vergunde_wooneenheden_nieuwbouw": DataStapDefinitie(
            stap_nr,
            "vergunde_wooneenheden_nieuwbouw",
            "Vergunde wooneenheden (nieuwbouw)",
            f"**Jaarlijks gemiddelde** ({JAAR_TELLERS_VENSTER}) van vergunde wooneenheden nieuwbouw per dB-band. "
            "Input voor flow rate `verbod_kleine_woning`.",
            VERGUNNINGEN_STAP_BEREKENING
            + "\n\nFilter: `handeling == 'Nieuwbouw'` en `metriek == 'Aantal wooneenheden'`.",
            "`vergunningen_omgevingsloket_2026_lang.csv`",
        ),
        "gem_wooneenheden_per_vergunning": DataStapDefinitie(
            stap_nr,
            "gem_wooneenheden_per_vergunning",
            "Gem. wooneenheden per vergunning",
            f"**Landelijk hulpcijfer** (zelfde waarde in elke band): gemiddelde over {JAAR_TELLERS_VENSTER} "
            "van de jaarlijkse ratio wooneenheden/projecten (omgevingsloket). Nog niet in flow-formules.",
            f"`gem_wooneenheden_per_vergunning_gemiddelde(verg_combined)` — gemiddelde van 6 jaarlijkse ratio's.",
            "`vergunningen_omgevingsloket_2026_lang.csv`",
        ),
        "vergunningen_kwetsbare_groep": DataStapDefinitie(
            stap_nr,
            "vergunningen_kwetsbare_groep",
            "Vergunningen kwetsbare groep",
            f"**Jaarlijks gemiddelde** ({JAAR_TELLERS_VENSTER}) kwetsbare-functievergunningen per band. "
            "Input voor `verbod_kwetsbare_groep`.",
            VERGUNNINGEN_STAP_BEREKENING + "\n\nFilter: `bron == 'kwetsbare_functies'`.",
            "`vergunningen_kwetsbare_functies_2026_lang.csv`",
        ),
        "renovatie_totaal": DataStapDefinitie(
            stap_nr,
            "renovatie_totaal",
            "Renovatievergunningen (totaal)",
            f"**Jaarlijks gemiddelde** ({JAAR_TELLERS_VENSTER}) renovatievergunningen per band. "
            "Basis voor R+ / R− en renovatiemaatregelen.",
            VERGUNNINGEN_STAP_BEREKENING
            + "\n\nFilter: `handeling == 'Verbouwen of hergebruik'`.",
            "`vergunningen_omgevingsloket_2026_lang.csv`",
        ),
        "28_flow_volgorde": DataStapDefinitie(
            stap_nr,
            "FLOW_KOLOMMEN",
            "FLOW-volgorde en schema-check",
            "Alle 27 variabelen ingevuld; kolommen ordenen volgens FLOW §2.0.",
            "Herschikken zonder waarden te wijzigen; `assert_flow_schema` valideert.",
            "`contour/schema.py` → `FLOW_KOLOMMEN`",
        ),
    }
    if stap_id in defs:
        info = defs[stap_id]
        return DataStapDefinitie(stap_nr, info.stap_id, info.titel, info.uitleg, info.berekening, info.bronnen)
    nr = DATA_STAP_VOLGORDE.index(stap_id) if stap_id in DATA_STAP_VOLGORDE else -1
    return DataStapDefinitie(
        nr,
        stap_id,
        stap_id,
        f"FLOW-variabele `{stap_id}`.",
        "Zie STOCKS_EN_FLOWS_BEREKENEN.md §2.",
        "Zie pipeline-bronnen in `contour/`",
    )


def stap_notebook_code(stap_id: str) -> str:
    """Expliciete pandas-code voor één data-stap."""
    show = lambda kol: f'lden[["{kol}"]].head()'

    if stap_id == "0_index":
        return (
            "lden, lnight = init_lden_lnight_index(raw_vlaanderen_lden, raw_vlaanderen_lnight)\n"
            "list(lden.columns)"
        )

    if stap_id == "inwoners_per_contour":
        return (
            "idx = lden.index\n"
            "_inw_vla_lden = series_op_index(raw_vlaanderen_lden, 'inwoners', idx)\n"
            "_inw_bru_lden = series_op_index(lden_bru_db, 'inwoners', idx)\n"
            "lden['inwoners_per_contour'] = _inw_vla_lden + _inw_bru_lden\n"
            "_inw_vla_lnight = series_op_index(raw_vlaanderen_lnight, 'inwoners', idx)\n"
            "_inw_bru_lnight = series_op_index(lnight_bru_db, 'inwoners', idx)\n"
            "lnight['inwoners_per_contour'] = _inw_vla_lnight + _inw_bru_lnight\n"
            + show("inwoners_per_contour")
        )

    if stap_id == KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR:
        k = KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR
        return (
            f"idx = lden.index\n"
            f"lden[{k!r}] = series_op_index(raw_vlaanderen_lden, {k!r}, idx)\n"
            f"lnight[{k!r}] = series_op_index(raw_vlaanderen_lnight, {k!r}, idx)\n"
            + show(k)
        )

    if stap_id == KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR:
        k = KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR
        return (
            f"idx = lden.index\n"
            f"lden[{k!r}] = series_op_index(raw_vlaanderen_lden, {k!r}, idx)\n"
            f"lnight[{k!r}] = series_op_index(raw_vlaanderen_lnight, {k!r}, idx)\n"
            + show(k)
        )

    if stap_id == "bewoonde_niet_geïsoleerde_woning":
        return (
            "idx = lden.index\n"
            "_inw_vla_lden = series_op_index(raw_vlaanderen_lden, 'inwoners', idx)\n"
            "_inw_bru_lden = series_op_index(lden_bru_db, 'inwoners', idx)\n"
            "_won_vla_lden = series_op_index(raw_vlaanderen_lden, 'aantal_woningen', idx)\n"
            "_gem_inw_per_huis_lden = (_inw_vla_lden / _won_vla_lden.replace(0, pd.NA)).fillna(2.0)\n"
            "_gem_inw_per_huis_lden = _gem_inw_per_huis_lden.where(_gem_inw_per_huis_lden > 0, 2.0)\n"
            "_won_bru_lden = _inw_bru_lden / _gem_inw_per_huis_lden\n"
            "won_totaal_lden = _won_vla_lden + _won_bru_lden\n"
            "lden['bewoonde_niet_geïsoleerde_woning'] = won_totaal_lden * PCT_NIET_GEISOLEERD\n"
            "_inw_vla_lnight = series_op_index(raw_vlaanderen_lnight, 'inwoners', idx)\n"
            "_inw_bru_lnight = series_op_index(lnight_bru_db, 'inwoners', idx)\n"
            "_won_vla_lnight = series_op_index(raw_vlaanderen_lnight, 'aantal_woningen', idx)\n"
            "_gem_inw_per_huis_lnight = (_inw_vla_lnight / _won_vla_lnight.replace(0, pd.NA)).fillna(2.0)\n"
            "_gem_inw_per_huis_lnight = _gem_inw_per_huis_lnight.where(_gem_inw_per_huis_lnight > 0, 2.0)\n"
            "_won_bru_lnight = _inw_bru_lnight / _gem_inw_per_huis_lnight\n"
            "won_totaal_lnight = _won_vla_lnight + _won_bru_lnight\n"
            "lnight['bewoonde_niet_geïsoleerde_woning'] = won_totaal_lnight * PCT_NIET_GEISOLEERD\n"
            + show("bewoonde_niet_geïsoleerde_woning")
        )

    if stap_id == "bewoonde_geïsoleerde_woning":
        return (
            "lden['bewoonde_geïsoleerde_woning'] = won_totaal_lden * PCT_GEISOLEERD\n"
            "lnight['bewoonde_geïsoleerde_woning'] = won_totaal_lnight * PCT_GEISOLEERD\n"
            + show("bewoonde_geïsoleerde_woning")
        )

    if stap_id in {
        "onbebouwde_bebouwbare_percelen",
        "onbebouwde_onbebouwbare_percelen",
        "nieuwe_woning",
        "perceel_eigendom_overheid",
        "woning_eigendom_overheid",
        "R+",
        "R−",
        "nieuwbouw_geïsoleerd",
        "nieuwbouw_niet_geïsoleerd",
        "potentieel_isoleerbare_woningen",
    }:
        return (
            f"lden[{stap_id!r}] = 0.0\n"
            f"lnight[{stap_id!r}] = 0.0\n"
            + show(stap_id)
        )

    if stap_id == "vergunde_wooneenheden_nieuwbouw":
        return (
            "sector_lden, _ = lees_sector_contour_beide()\n"
            "conversie_lden = conversietabel_gemeente_naar_db(sector_lden, indicator='lden')\n"
            "conversie_lden_band = koppel_conversie_aan_contourband(conversie_lden, lden)\n"
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
            "idx = lden.index\n"
            "df_verg = verg_contour[verg_contour['jaar_indiening'].astype(str) == str(JAAR_TELLERS)].copy()\n"
            "\n"
            "def som_per_band(mask):\n"
            "    subset = df_verg.loc[mask]\n"
            "    if subset.empty:\n"
            "        return pd.Series(0.0, index=idx)\n"
            "    return subset.groupby('db_ondergrens')['waarde'].sum().reindex(idx).fillna(0)\n"
            "\n"
            "_nieuwbouw_we = som_per_band(\n"
            "    (df_verg['handeling'] == 'Nieuwbouw') & (df_verg['metriek'] == 'Aantal wooneenheden')\n"
            ")\n"
            "lden['vergunde_wooneenheden_nieuwbouw'] = _nieuwbouw_we\n"
            "lnight['vergunde_wooneenheden_nieuwbouw'] = _nieuwbouw_we\n"
            + show("vergunde_wooneenheden_nieuwbouw")
        )

    if stap_id == "gem_wooneenheden_per_vergunning":
        return (
            "_gem_we = gem_wooneenheden_per_vergunning_gemiddelde(verg_combined)\n"
            "lden['gem_wooneenheden_per_vergunning'] = _gem_we\n"
            "lnight['gem_wooneenheden_per_vergunning'] = _gem_we\n"
            "pd.DataFrame({'gem_wooneenheden_per_vergunning': [_gem_we], 'periode': [str(JAAR_TELLERS)]})"
        )

    if stap_id == "vergunningen_kwetsbare_groep":
        return (
            "_kwetsbaar = som_per_band(df_verg['bron'] == 'kwetsbare_functies')\n"
            "lden['vergunningen_kwetsbare_groep'] = _kwetsbaar\n"
            "lnight['vergunningen_kwetsbare_groep'] = _kwetsbaar\n"
            + show("vergunningen_kwetsbare_groep")
        )

    if stap_id == "renovatie_totaal":
        return (
            "_renovatie = som_per_band(df_verg['handeling'] == 'Verbouwen of hergebruik')\n"
            "lden['renovatie_totaal'] = _renovatie\n"
            "lnight['renovatie_totaal'] = _renovatie\n"
            + show("renovatie_totaal")
        )

    if stap_id == "transacties_en_capakey_prijzen":
        return (
            "from contour.prices import (\n"
            "    SEGMENTEN_PER_PRIJSKOLOM,\n"
            "    bouw_capakey_contour_mapping,\n"
            ")\n"
            "\n"
            "# 1) Prijs per transactie\n"
            "tx = transacties.copy()\n"
            "tx['capakey'] = tx['capakey'].astype(str)\n"
            "tx['aantal_transacties'] = pd.to_numeric(tx['sum_ParcelsNumber'], errors='coerce').fillna(0)\n"
            "p50 = pd.to_numeric(tx['avg_PriceP50'], errors='coerce')\n"
            "m2 = pd.to_numeric(tx['average_price_m2'], errors='coerce')\n"
            "opp = pd.to_numeric(tx['avg_ParcelsAreaP50'], errors='coerce')\n"
            "tx['prijs_euro'] = p50.where(p50 > 0, m2 * opp)\n"
            "tx['prijs_euro'] = tx['prijs_euro'].where(tx['prijs_euro'] > 0)\n"
            "\n"
            "# 2) Gewogen gemiddelde prijs per CaPaKey (per prijstype)\n"
            "capakey_prijzen = pd.DataFrame({'capakey': tx['capakey'].unique()})\n"
            "for _prijs_kolom, _segmenten in SEGMENTEN_PER_PRIJSKOLOM.items():\n"
            "    seg = tx[tx['segment'].isin(_segmenten)]\n"
            "    _gewicht_kolom = f'gewicht_{_prijs_kolom}'\n"
            "    totaal_tx = seg.groupby('capakey', as_index=False)['aantal_transacties'].sum()\n"
            "    totaal_tx = totaal_tx.rename(columns={'aantal_transacties': _gewicht_kolom})\n"
            "    met_prijs = seg[seg['prijs_euro'].notna() & (seg['aantal_transacties'] > 0)].copy()\n"
            "    if met_prijs.empty:\n"
            "        met_prijs = seg[seg['prijs_euro'].notna()].copy()\n"
            "    if met_prijs.empty:\n"
            "        capakey_prijzen = capakey_prijzen.merge(\n"
            "            totaal_tx.assign(**{_prijs_kolom: pd.NA}), on='capakey', how='left'\n"
            "        )\n"
            "        continue\n"
            "    met_prijs['_w'] = met_prijs['aantal_transacties'].clip(lower=1)\n"
            "    prijs_agg = (\n"
            "        met_prijs.assign(_pw=met_prijs['prijs_euro'] * met_prijs['_w'])\n"
            "        .groupby('capakey', as_index=False)\n"
            "        .agg(_pw=('_pw', 'sum'), _w=('_w', 'sum'))\n"
            "    )\n"
            "    prijs_agg[_prijs_kolom] = prijs_agg['_pw'] / prijs_agg['_w']\n"
            "    capakey_prijzen = capakey_prijzen.merge(\n"
            "        totaal_tx.merge(prijs_agg[['capakey', _prijs_kolom]], on='capakey', how='left'),\n"
            "        on='capakey',\n"
            "        how='left',\n"
            "    )\n"
            "\n"
            "# Geen iso-split: geïsoleerde woning = zelfde prijs\n"
            "capakey_prijzen['prijs_bewoonde_geïsoleerde_woning'] = capakey_prijzen[\n"
            "    'prijs_bewoonde_niet_geïsoleerde_woning'\n"
            "]\n"
            "capakey_prijzen['gewicht_prijs_bewoonde_geïsoleerde_woning'] = capakey_prijzen[\n"
            "    'gewicht_prijs_bewoonde_niet_geïsoleerde_woning'\n"
            "]\n"
            "\n"
            "# 3) CaPaKey → db_ondergrens\n"
            "capakey_mapping = bouw_capakey_contour_mapping(transacties, brussel_lden, lden)\n"
            "\n"
            "def agg_transacties(segmenten):\n"
            "    gekoppeld = tx.merge(capakey_mapping[['capakey', 'db_ondergrens']], on='capakey', how='inner')\n"
            "    subset = gekoppeld[gekoppeld['segment'].isin(segmenten)]\n"
            "    if subset.empty:\n"
            "        return pd.Series(0.0, index=lden.index)\n"
            "    return subset.groupby('db_ondergrens')['aantal_transacties'].sum().reindex(lden.index).fillna(0)\n"
            "\n"
            "capakey_prijzen.head()"
        )

    if stap_id == "alle_transacties_percelen":
        return (
            "tx_percelen = agg_transacties(['industrie_terrein', 'industrie_bebouwd'])\n"
            "lden['alle_transacties_percelen'] = tx_percelen\n"
            "lnight['alle_transacties_percelen'] = tx_percelen\n"
            + show("alle_transacties_percelen")
        )

    if stap_id == "alle_verkopen_onbebouwde_bebouwbare_percelen":
        return (
            "lden['alle_verkopen_onbebouwde_bebouwbare_percelen'] = tx_percelen\n"
            "lnight['alle_verkopen_onbebouwde_bebouwbare_percelen'] = tx_percelen\n"
            + show("alle_verkopen_onbebouwde_bebouwbare_percelen")
        )

    if stap_id == "alle_transacties_woningen":
        return (
            "tx_woningen = agg_transacties(['woningen', 'appartementen'])\n"
            "lden['alle_transacties_woningen'] = tx_woningen\n"
            "lnight['alle_transacties_woningen'] = tx_woningen\n"
            + show("alle_transacties_woningen")
        )

    if stap_id == "alle_verkopen_woningen":
        return (
            "lden['alle_verkopen_woningen'] = tx_woningen\n"
            "lnight['alle_verkopen_woningen'] = tx_woningen\n"
            + show("alle_verkopen_woningen")
        )

    if stap_id in {
        "prijs_onbebouwde_bebouwbare_percelen",
        "prijs_onbebouwde_onbebouwbare_percelen",
        "prijs_bewoonde_niet_geïsoleerde_woning",
    }:
        return _prijs_naar_contour_code(stap_id)

    if stap_id == "prijs_bewoonde_geïsoleerde_woning":
        return (
            "lden['prijs_bewoonde_geïsoleerde_woning'] = lden['prijs_bewoonde_niet_geïsoleerde_woning']\n"
            "lnight['prijs_bewoonde_geïsoleerde_woning'] = lden['prijs_bewoonde_geïsoleerde_woning']\n"
            + show("prijs_bewoonde_geïsoleerde_woning")
        )

    if stap_id == "28_flow_volgorde":
        return (
            "lden = lden[list(FLOW_KOLOMMEN)]\n"
            "lnight = lnight[list(FLOW_KOLOMMEN)]\n"
            "assert_flow_schema(lden)\n"
            "assert_flow_schema(lnight)\n"
            "list(lden.columns)"
        )

    raise KeyError(f"Geen notebook-code voor data-stap: {stap_id}")


def _prijs_naar_contour_code(prijs_kolom: str) -> str:
    """Expliciete aggregatie CaPaKey-prijzen → contourband."""
    return (
        f"_prijs_kolom = {prijs_kolom!r}\n"
        f"_gewicht_tx = f'gewicht_{{_prijs_kolom}}'\n"
        "_gekoppeld = capakey_mapping.merge(\n"
        "    capakey_prijzen[['capakey', _prijs_kolom, _gewicht_tx]],\n"
        "    on='capakey',\n"
        "    how='inner',\n"
        ")\n"
        "_gekoppeld = _gekoppeld[_gekoppeld[_prijs_kolom].notna()].copy()\n"
        "_gekoppeld['w'] = _gekoppeld['gewicht_ruimtelijk'] * _gekoppeld[_gewicht_tx].clip(lower=1)\n"
        "\n"
        "def _gewogen_gem(prijzen, gewichten):\n"
        "    mask = prijzen.notna() & (gewichten > 0)\n"
        "    if not mask.any():\n"
        "        return None\n"
        "    return float((prijzen[mask] * gewichten[mask]).sum() / gewichten[mask].sum())\n"
        "\n"
        "_fallback = _gewogen_gem(\n"
        "    capakey_prijzen[_prijs_kolom],\n"
        "    capakey_prijzen[_gewicht_tx].clip(lower=1),\n"
        ")\n"
        "_per_band = _gekoppeld.groupby('db_ondergrens').apply(\n"
        "    lambda g: _gewogen_gem(g[_prijs_kolom], g['w']),\n"
        "    include_groups=False,\n"
        ")\n"
        f"lden[_prijs_kolom] = _per_band.reindex(lden.index)\n"
        "if _fallback is not None:\n"
        f"    lden[_prijs_kolom] = lden[_prijs_kolom].fillna(_fallback)\n"
        f"lnight[_prijs_kolom] = lden[_prijs_kolom]\n"
        f'lden[[{prijs_kolom!r}]].head()'
    )


def stap_grafiek_code(stap_id: str) -> str:
    """Altair-staafdiagram per db_ondergrens na elke data-stap."""
    info = stap_definitie(stap_id)
    titel = f"Stap {info.stap_nr} — {info.titel}"

    if stap_id == "0_index":
        return (
            "from contour.notebook_viz import staafdiagram_reeks\n\n"
            "staafdiagram_reeks(\n"
            "    pd.Series(1, index=lden.index),\n"
            f"    titel={titel!r} + ' (30 banden)',\n"
            "    y_label='band aanwezig',\n"
            ")"
        )

    if stap_id == "transacties_en_capakey_prijzen":
        return (
            "from contour.notebook_viz import staafdiagram_reeks\n\n"
            "_gemapt = capakey_mapping.groupby('db_ondergrens').size().reindex(lden.index).fillna(0)\n"
            f"staafdiagram_reeks(_gemapt, titel={titel!r} + ' — CaPaKeys gemapt', y_label='aantal CaPaKeys')"
        )

    if stap_id == "28_flow_volgorde":
        return (
            "from contour.notebook_viz import toon_staaf_per_contour\n\n"
            f"toon_staaf_per_contour(lden, 'inwoners_per_contour', lnight=lnight, titel={titel!r} + ' — controle')"
        )

    return (
        "from contour.notebook_viz import toon_staaf_per_contour\n\n"
        f"toon_staaf_per_contour(lden, {stap_id!r}, lnight=lnight, titel={titel!r})"
    )
