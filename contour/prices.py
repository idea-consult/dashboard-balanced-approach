"""Derive contour unit prices from vastgoedtransactie CSVs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from contour.paths import CAPAKEY_CONTOUR_LDEN, DATA_DIR
from contour.schema import INDEX_NAME, banden_dataframe

PRIJS_KOLOMMEN = [
    "prijs_onbebouwde_bebouwbare_percelen",
    "prijs_onbebouwde_onbebouwbare_percelen",
    "prijs_bewoonde_niet_geïsoleerde_woning",
    "prijs_bewoonde_geïsoleerde_woning",
]

SEGMENTEN_PER_PRIJSKOLOM = {
    "prijs_onbebouwde_bebouwbare_percelen": ["industrie_terrein", "industrie_bebouwd"],
    "prijs_onbebouwde_onbebouwbare_percelen": ["industrie_terrein"],
    "prijs_bewoonde_niet_geïsoleerde_woning": ["woningen", "appartementen"],
    "prijs_bewoonde_geïsoleerde_woning": ["woningen", "appartementen"],
}

BRUSSEL_SECTOR_KOLOM = "CS01012022"
BRUSSEL_OPP_AANDEEL_KOLOM = "Part de la surface du qs dans le noise contour"


def _naar_getal(reeks: pd.Series) -> pd.Series:
    return pd.to_numeric(reeks, errors="coerce")


def transactie_prijs_euro(rij: pd.Series) -> float | None:
    """Median transaction price; fallback to price/m² × median area (enkel voor tests)."""
    p50 = _naar_getal(pd.Series([rij.get("avg_PriceP50")])).iloc[0]
    if pd.notna(p50) and p50 > 0:
        return float(p50)

    m2 = _naar_getal(pd.Series([rij.get("average_price_m2")])).iloc[0]
    opp = _naar_getal(pd.Series([rij.get("avg_ParcelsAreaP50")])).iloc[0]
    if pd.notna(m2) and pd.notna(opp) and m2 > 0 and opp > 0:
        return float(m2 * opp)
    return None


def _vector_prijs_euro(tx: pd.DataFrame) -> pd.Series:
    """Vectorized: avg_PriceP50, else average_price_m2 × avg_ParcelsAreaP50."""
    p50 = _naar_getal(tx["avg_PriceP50"])
    m2 = _naar_getal(tx["average_price_m2"])
    opp = _naar_getal(tx["avg_ParcelsAreaP50"])
    fallback = m2 * opp
    prijs = p50.where(p50 > 0, fallback)
    prijs = prijs.where(prijs > 0)
    return prijs


def _agg_prijs_per_capakey(seg: pd.DataFrame, prijs_kolom: str) -> pd.DataFrame:
    """Weighted average price per capakey for one segment subset."""
    gewicht_kolom = f"gewicht_{prijs_kolom}"
    totaal_tx = seg.groupby("capakey", as_index=False)["aantal_transacties"].sum()
    totaal_tx = totaal_tx.rename(columns={"aantal_transacties": gewicht_kolom})

    met_prijs = seg[seg["prijs_euro"].notna() & (seg["aantal_transacties"] > 0)]
    if met_prijs.empty:
        met_prijs = seg[seg["prijs_euro"].notna()]
    if met_prijs.empty:
        return totaal_tx.assign(**{prijs_kolom: pd.NA})

    met_prijs = met_prijs.assign(_w=met_prijs["aantal_transacties"].clip(lower=1))
    prijs_agg = (
        met_prijs.assign(_pw=met_prijs["prijs_euro"] * met_prijs["_w"])
        .groupby("capakey", as_index=False)
        .agg(_pw=("_pw", "sum"), _w=("_w", "sum"))
    )
    prijs_agg[prijs_kolom] = prijs_agg["_pw"] / prijs_agg["_w"]
    prijs_agg = prijs_agg[["capakey", prijs_kolom]]
    return totaal_tx.merge(prijs_agg, on="capakey", how="left")


def bereken_capakey_prijzen(transacties: pd.DataFrame) -> pd.DataFrame:
    """One row per CaPaKey with unit prices and transaction weights per price type."""
    tx = transacties.copy()
    tx["capakey"] = tx["capakey"].astype(str)
    tx["aantal_transacties"] = _naar_getal(tx["sum_ParcelsNumber"]).fillna(0)
    tx["prijs_euro"] = _vector_prijs_euro(tx)

    capakeys = pd.DataFrame({"capakey": tx["capakey"].unique()})
    for prijs_kolom, segmenten in SEGMENTEN_PER_PRIJSKOLOM.items():
        seg = tx[tx["segment"].isin(segmenten)]
        agg = _agg_prijs_per_capakey(seg, prijs_kolom)
        capakeys = capakeys.merge(agg, on="capakey", how="left")

    # Geen iso-split in transactiedata: geïsoleerde woning = zelfde prijs als niet-geïsoleerd
    if "prijs_bewoonde_niet_geïsoleerde_woning" in capakeys.columns:
        capakeys["prijs_bewoonde_geïsoleerde_woning"] = capakeys["prijs_bewoonde_niet_geïsoleerde_woning"]
        capakeys["gewicht_prijs_bewoonde_geïsoleerde_woning"] = capakeys[
            "gewicht_prijs_bewoonde_niet_geïsoleerde_woning"
        ]

    return capakeys


def laad_capakey_contour_extern(pad: Path | None = None) -> pd.DataFrame:
    """Optional data/capakey_contour_lden.csv: capakey × geluidscontour (of db_ondergrens)."""
    pad = pad or CAPAKEY_CONTOUR_LDEN
    if not pad.exists():
        return pd.DataFrame(columns=["capakey", "db_ondergrens", "geluidscontour", "gewicht_ruimtelijk"])

    df = pd.read_csv(pad, sep=";")
    df = df.rename(columns={c: c.strip() for c in df.columns})
    if "NISCode" in df.columns and "capakey" not in df.columns:
        df = df.rename(columns={"NISCode": "capakey"})
    df["capakey"] = df["capakey"].astype(str)
    if "gewicht_ruimtelijk" not in df.columns:
        df["gewicht_ruimtelijk"] = 1.0
    for kolom in ("db_ondergrens", "geluidscontour"):
        if kolom not in df.columns:
            df[kolom] = pd.NA
    return df[["capakey", "db_ondergrens", "geluidscontour", "gewicht_ruimtelijk"]].copy()


def brussel_capakey_naar_contour(
    capakeys: pd.Series,
    brussel_sector: pd.DataFrame,
    contour_lden: pd.DataFrame,
) -> pd.DataFrame:
    """Brussels parcels: sector prefix (6 tekens) × dB-gewicht uit sectorbestand."""
    br = brussel_sector.copy()
    br["sector"] = br[BRUSSEL_SECTOR_KOLOM].astype(str)
    br["key6"] = br["sector"].str[:6]
    if "db_ondergrens" in contour_lden.columns:
        banden = contour_lden[["db_ondergrens", "geluidscontour"]].drop_duplicates()
    else:
        banden = banden_dataframe(contour_lden.index)
    br = br.merge(banden[["db_ondergrens", "geluidscontour"]], left_on="dB", right_on="db_ondergrens", how="inner")

    uniek = pd.DataFrame({"capakey": capakeys.astype(str).unique()})
    uniek["key6"] = uniek["capakey"].str[:6]
    gekoppeld = uniek.merge(
        br[["key6", "geluidscontour", "db_ondergrens", BRUSSEL_OPP_AANDEEL_KOLOM]],
        on="key6",
        how="inner",
    )
    gekoppeld = gekoppeld.rename(columns={BRUSSEL_OPP_AANDEEL_KOLOM: "gewicht_ruimtelijk"})
    som = gekoppeld.groupby("capakey")["gewicht_ruimtelijk"].transform("sum")
    gekoppeld["gewicht_ruimtelijk"] = gekoppeld["gewicht_ruimtelijk"] / som
    gekoppeld["bron_mapping"] = "brussel_sector"
    return gekoppeld


def bouw_capakey_contour_mapping(
    transacties: pd.DataFrame,
    brussel_sector: pd.DataFrame,
    contour_lden: pd.DataFrame,
    extern_pad: Path | None = None,
) -> pd.DataFrame:
    """Combine external CaPaKey→contour file with Brussels sector fallback."""
    capakeys = transacties["capakey"].astype(str).unique()
    frames: list[pd.DataFrame] = []

    extern = laad_capakey_contour_extern(extern_pad)
    if not extern.empty:
        extern = extern[extern["capakey"].isin(capakeys)].copy()
        extern["bron_mapping"] = "extern_bestand"
        frames.append(extern)

    extern_keys = set(extern["capakey"]) if not extern.empty else set()
    rest = [c for c in capakeys if c not in extern_keys]
    if rest:
        bru = brussel_capakey_naar_contour(pd.Series(rest), brussel_sector, contour_lden)
        if not bru.empty:
            frames.append(bru)

    if not frames:
        return pd.DataFrame(
            columns=["capakey", "db_ondergrens", "geluidscontour", "gewicht_ruimtelijk", "bron_mapping"]
        )
    return pd.concat(frames, ignore_index=True)


def _gewogen_gemiddelde(prijzen: pd.Series, gewichten: pd.Series) -> float | None:
    mask = prijzen.notna() & (gewichten > 0)
    if not mask.any():
        return None
    p = prijzen[mask]
    w = gewichten[mask]
    return float((p * w).sum() / w.sum())


def aggregeer_prijzen_naar_contour(
    capakey_prijzen: pd.DataFrame,
    mapping: pd.DataFrame,
    contour_lden: pd.DataFrame,
) -> pd.DataFrame:
    """Weighted average unit price per 1 dB-contour band."""
    if "db_ondergrens" in contour_lden.columns:
        contour = contour_lden[["db_ondergrens"]].copy()
    else:
        contour = banden_dataframe(contour_lden.index)[["db_ondergrens"]]
    gekoppeld = mapping.merge(capakey_prijzen, on="capakey", how="inner")

    for prijs_kolom in PRIJS_KOLOMMEN:
        gewicht_tx = f"gewicht_{prijs_kolom}"
        if gewicht_tx not in gekoppeld.columns:
            continue

        subset = gekoppeld[gekoppeld[prijs_kolom].notna()].copy()
        subset["w"] = subset["gewicht_ruimtelijk"] * subset[gewicht_tx].clip(lower=1)

        fallback = _gewogen_gemiddelde(
            capakey_prijzen[prijs_kolom],
            capakey_prijzen.get(gewicht_tx, pd.Series(1.0, index=capakey_prijzen.index)).clip(lower=1),
        )

        if subset.empty:
            contour[prijs_kolom] = fallback
            continue

        per_band = subset.groupby("db_ondergrens").apply(
            lambda g: _gewogen_gemiddelde(g[prijs_kolom], g["w"]),
            include_groups=False,
        )
        per_band = per_band.rename(prijs_kolom).reset_index()
        contour = contour.drop(columns=[prijs_kolom], errors="ignore").merge(
            per_band, on="db_ondergrens", how="left"
        )

        if fallback is not None:
            contour[prijs_kolom] = contour[prijs_kolom].fillna(fallback)

    return contour


def _merge_prijzen_op_contour(contour: pd.DataFrame, prijzen_contour: pd.DataFrame) -> pd.DataFrame:
    from contour.consolidate import stap_prijzen

    return stap_prijzen(contour, prijzen_contour)


def bereken_prijzen_uit_transacties(
    transacties: pd.DataFrame,
    brussel_sector: pd.DataFrame,
    contour_lden: pd.DataFrame,
    *,
    extern_pad: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Bereken capakey-prijzen, mapping en geaggregeerde prijzen per band (één keer)."""
    print("  [prijzen] bereken_capakey_prijzen …")
    capakey_prijzen = bereken_capakey_prijzen(transacties)
    print(f"  [prijzen] capakey_prijzen: {len(capakey_prijzen):,} rijen")
    print("  [prijzen] bouw_capakey_contour_mapping …")
    mapping = bouw_capakey_contour_mapping(transacties, brussel_sector, contour_lden, extern_pad)
    print(f"  [prijzen] mapping: {len(mapping):,} rijen")
    print("  [prijzen] aggregeer_prijzen_naar_contour …")
    prijzen_contour = aggregeer_prijzen_naar_contour(capakey_prijzen, mapping, contour_lden)
    print("  [prijzen] klaar")
    return capakey_prijzen, mapping, prijzen_contour


def vervang_prijzen_uit_transacties(
    contour: pd.DataFrame,
    transacties: pd.DataFrame,
    brussel_sector: pd.DataFrame,
    *,
    extern_pad: Path | None = None,
    prijzen_contour: pd.DataFrame | None = None,
    capakey_prijzen: pd.DataFrame | None = None,
    capakey_mapping: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Replace dummy Excel prices with transaction-based prices.

    Returns (contour_met_prijzen, capakey_prijzen, capakey_contour_mapping).
    """
    if prijzen_contour is None:
        capakey_prijzen, capakey_mapping, prijzen_contour = bereken_prijzen_uit_transacties(
            transacties, brussel_sector, contour, extern_pad=extern_pad
        )
    else:
        capakey_prijzen = capakey_prijzen if capakey_prijzen is not None else pd.DataFrame()
        capakey_mapping = capakey_mapping if capakey_mapping is not None else pd.DataFrame()

    out = _merge_prijzen_op_contour(contour, prijzen_contour)
    return out, capakey_prijzen, capakey_mapping


def prijs_dekking_rapport(
    capakey_prijzen: pd.DataFrame,
    mapping: pd.DataFrame,
    transacties: pd.DataFrame,
) -> dict:
    """Summary of price and spatial mapping coverage."""
    totaal = transacties["capakey"].astype(str).nunique()
    gemapt = mapping["capakey"].nunique() if not mapping.empty else 0
    rapport: dict = {
        "capakeys_totaal": int(totaal),
        "capakeys_met_contour_mapping": int(gemapt),
        "pct_gemapt": round(100 * gemapt / totaal, 1) if totaal else 0.0,
    }
    if not mapping.empty:
        rapport["mapping_per_bron"] = mapping.groupby("bron_mapping")["capakey"].nunique().to_dict()
    for kolom in PRIJS_KOLOMMEN:
        if kolom in capakey_prijzen.columns:
            rapport[f"{kolom}_ingevuld"] = int(capakey_prijzen[kolom].notna().sum())
    return rapport
