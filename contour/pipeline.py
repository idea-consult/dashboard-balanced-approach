"""End-to-end data consolidation and flow export pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from contour.consolidate import (
    bouw_lden,
    bouw_lden_regional,
    bouw_lnight,
    bouw_lnight_regional,
    vergunningen_gemeente_tabel,
)
from contour.export import (
    export_lden_contour,
    export_lden_contour_regional,
    export_lnight_contour,
    export_lnight_contour_regional,
    update_flow_rules_rates,
)
from contour.flows import bereken_alle_flow_rates, bouw_stocks_contour, bouw_tellers_contour, valideer_flow_rates
from contour.loaders import (
    lees_brussel_sector,
    lees_sector_contour_beide,
    lees_transacties,
    lees_vergunningen,
)
from contour.paths import INTERMEDIATE_DIR
from contour.prices import bereken_prijzen_uit_transacties, prijs_dekking_rapport
from contour.schema import assert_flow_schema
from contour.spatial import (
    conversietabel_gemeente_naar_db,
    koppel_conversie_aan_contourband,
    verdeel_gemeente_naar_contour,
)
from contour.vergunningen import (
    JAAR_TELLERS_LABEL,
    combineer_vergunningen_lang,
    gemiddelde_jaarlijkse_vergunningen,
)


def run_data_pipeline(
    intermediate_dir: Path | None = None,
    jaartal_vergunningen: str | int = JAAR_TELLERS_LABEL,
) -> dict[str, pd.DataFrame]:
    """Load, consolidate, write parquet; return master DataFrames."""
    out_dir = intermediate_dir or INTERMEDIATE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[pipeline] 1/10 lees_brussel_sector …")
    brussel_lden, brussel_lnight = lees_brussel_sector()
    print("[pipeline] 2/10 lees_transacties …")
    transacties = lees_transacties()
    print(f"[pipeline]    transacties: {len(transacties):,} rijen")

    print("[pipeline] 3/10 basis-shell lden (stappen 0-2) …")
    lden_shell = bouw_lden()
    print("[pipeline] 4/10 prijzen uit transacties …")
    capakey_prijzen, capakey_mapping, prijzen_contour = bereken_prijzen_uit_transacties(
        transacties, brussel_lden, lden_shell
    )

    print("[pipeline] 5/10 conversietabel gemeente -> db …")
    sector_lden, sector_lnight = lees_sector_contour_beide()
    conversie_lden = conversietabel_gemeente_naar_db(sector_lden, indicator="lden")
    conversie_lnight = conversietabel_gemeente_naar_db(sector_lnight, indicator="lnight")
    conversie_gemeente_db = pd.concat([conversie_lden, conversie_lnight], ignore_index=True)
    conversie_lden_band = koppel_conversie_aan_contourband(conversie_lden, lden_shell)

    print("[pipeline] 6/10 lees_vergunningen …")
    verg_omg, verg_kwets, verg_verk = lees_vergunningen()
    verg_omg = verg_omg.assign(bron="omgevingsloket")
    verg_kwets = verg_kwets.assign(bron="kwetsbare_functies")
    verg_verk = verg_verk.assign(bron="verkaveling")
    verg_combined = combineer_vergunningen_lang(verg_omg, verg_kwets, verg_verk)
    print(f"[pipeline]    vergunningen gecombineerd: {len(verg_combined):,} rijen")
    verg_gemeente = vergunningen_gemeente_tabel(verg_combined)
    verg_gem = gemiddelde_jaarlijkse_vergunningen(verg_combined)
    print(f"[pipeline]    vergunningen jaarlijks gemiddelde ({jaartal_vergunningen}): {len(verg_gem):,} rijen")
    verg_contour, verg_niet = verdeel_gemeente_naar_contour(
        verg_gem, conversie_lden_band, jaartal=jaartal_vergunningen
    )

    print("[pipeline] 7/10 bouw_lden + bouw_lnight (FLOW-schema) …")
    bouw_kwargs = dict(
        verg_contour=verg_contour,
        transacties=transacties,
        capakey_mapping=capakey_mapping,
        prijzen_contour=prijzen_contour,
        jaartal_vergunningen=jaartal_vergunningen,
        verg_lang_raw=verg_combined,
    )
    lden = bouw_lden(**bouw_kwargs)
    lnight = bouw_lnight(**bouw_kwargs)
    assert_flow_schema(lden)
    assert_flow_schema(lnight)

    print("[pipeline] 7b/10 bouw regional layers …")
    lden_regional = bouw_lden_regional()
    lnight_regional = bouw_lnight_regional()

    transacties_capakey = transacties.copy()

    tables = {
        "lden": lden,
        "lnight": lnight,
        "lden_regional": lden_regional,
        "lnight_regional": lnight_regional,
        "contour_lden": lden,
        "contour_lnight": lnight,
        "conversie_gemeente_db": conversie_gemeente_db,
        "vergunningen_gemeente": verg_gemeente,
        "vergunningen_contour": verg_contour,
        "vergunningen_niet_toewijsbaar": verg_niet,
        "transacties_capakey": transacties_capakey,
        "capakey_prijzen": capakey_prijzen,
        "capakey_contour_mapping": capakey_mapping,
        "prijs_dekking": pd.DataFrame([prijs_dekking_rapport(capakey_prijzen, capakey_mapping, transacties)]),
    }
    print("[pipeline] 8/10 schrijf parquet …")
    index_tables = {"lden", "lnight", "lden_regional", "lnight_regional", "contour_lden", "contour_lnight"}
    for naam, df in tables.items():
        print(f"[pipeline]    → {naam}.parquet ({len(df):,} rijen)")
        if naam in index_tables:
            df.to_parquet(out_dir / f"{naam}.parquet")
        else:
            df.to_parquet(out_dir / f"{naam}.parquet", index=False)

    print("[pipeline] klaar.")
    return tables


def run_flows_pipeline(
    tables: dict[str, pd.DataFrame] | None = None,
    intermediate_dir: Path | None = None,
    *,
    export_inputs: bool = True,
) -> dict[str, pd.DataFrame]:
    """Compute stocks, tellers, flow rates; optionally export to input/."""
    out_dir = intermediate_dir or INTERMEDIATE_DIR
    if tables is None:
        tables = {
            "lden": pd.read_parquet(out_dir / "lden.parquet"),
            "vergunningen_contour": pd.read_parquet(out_dir / "vergunningen_contour.parquet"),
            "transacties_capakey": pd.read_parquet(out_dir / "transacties_capakey.parquet"),
        }

    lden = tables.get("lden", tables.get("contour_lden"))
    stocks = bouw_stocks_contour(lden)
    tellers = bouw_tellers_contour(lden, tables["vergunningen_contour"], tables["transacties_capakey"])
    flow_rates = bereken_alle_flow_rates(
        lden, tables["vergunningen_contour"], tables["transacties_capakey"], tellers
    )
    validatie = valideer_flow_rates(flow_rates)

    stocks.to_parquet(out_dir / "stocks_contour.parquet", index=False)
    tellers.to_parquet(out_dir / "tellers_contour.parquet", index=False)
    flow_rates.to_parquet(out_dir / "flow_rates.parquet", index=False)
    validatie.to_parquet(out_dir / "flow_rates_validatie.parquet", index=False)

    if export_inputs:
        export_lden_contour(lden)
        lnight = tables.get("lnight", tables.get("contour_lnight"))
        if lnight is not None:
            export_lnight_contour(lnight)
        lden_regional = tables.get("lden_regional")
        if lden_regional is not None:
            export_lden_contour_regional(lden_regional)
        lnight_regional = tables.get("lnight_regional")
        if lnight_regional is not None:
            export_lnight_contour_regional(lnight_regional)
        update_flow_rules_rates(flow_rates)

    return {
        "stocks_contour": stocks,
        "tellers_contour": tellers,
        "flow_rates": flow_rates,
        "validatie": validatie,
    }


def validatie_consolidatie(tables: dict[str, pd.DataFrame]) -> dict:
    """Checklist for contour_data notebook."""
    lden = tables.get("lden", tables.get("contour_lden"))
    conversie = tables.get("conversie_gemeente_db")
    verg_niet = tables.get("vergunningen_niet_toewijsbaar")

    checks = {
        "aantal_contourbanden": len(lden),
        "conversie_aandeel_som_ok": True,
        "vergunningen_niet_toewijsbaar_pct": None,
    }
    if conversie is not None:
        som = conversie.groupby(["gemeente", "indicator"])["aandeel"].sum()
        checks["conversie_aandeel_som_ok"] = bool((som - 1.0).abs().max() < 1e-6)

    if verg_niet is not None and len(verg_niet):
        totaal = float(verg_niet["waarde"].sum())
        checks["vergunningen_niet_toewijsbaar_eenheden"] = totaal
        checks["vergunningen_niet_toewijsbaar_gemeenten"] = int(verg_niet["gemeente"].nunique())

    return checks
