"""Build FLOW-schema lden / lnight master tables (27 kolommen, index db_ondergrens)."""

from __future__ import annotations

import pandas as pd

from contour.columns import (
    KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR,
    KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR,
    WOONGEBIED_KOLOMMEN,
)
from contour.loaders import lees_brussel_inwoners_per_db, lees_contour_vlaanderen
from contour.prices import PRIJS_KOLOMMEN
from contour.schema import (
    FLOW_STOCKS,
    REGIONAL_INWONERS_KOLOMMEN,
    REGIONAL_KOLOMMEN,
    init_contour_shell,
    leeg_contour,
    regional_stock_kolom,
)

from contour.vergunningen import (
    JAAR_TELLERS_EIND,
    JAAR_TELLERS_LABEL,
    JAAR_TELLERS_START,
    gem_wooneenheden_per_vergunning_gemiddelde,
)

JAAR_TELLERS = JAAR_TELLERS_LABEL
PCT_GEISOLEERD = 0.20
PCT_NIET_GEISOLEERD = 0.80


def _naar_numeriek(df: pd.DataFrame, kolommen: list[str]) -> pd.DataFrame:
    out = df.copy()
    for kolom in kolommen:
        if kolom in out.columns:
            out[kolom] = pd.to_numeric(out[kolom], errors="coerce").fillna(0)
    return out


def series_op_index(df: pd.DataFrame, kolom: str, index: pd.Index) -> pd.Series:
    if kolom not in df.columns:
        return pd.Series(0.0, index=index)
    if "db_ondergrens" in df.columns:
        keyed = df.set_index("db_ondergrens")[kolom]
    elif "db" in df.columns:
        keyed = df.set_index("db")[kolom]
    else:
        keyed = df[kolom]
    return keyed.reindex(index).fillna(0).astype(float)


def _bereken_regio_basis(
    vlaanderen_df: pd.DataFrame,
    brussel_db: pd.DataFrame,
    index: pd.Index,
) -> dict[str, pd.Series]:
    """Inwoners/woningen per regio per band (zelfde logica als vroeger samenvoegen_vlaanderen_brussel)."""
    inw_vla = series_op_index(vlaanderen_df, "inwoners", index)
    inw_bru = series_op_index(brussel_db, "inwoners", index)
    won_vla = series_op_index(vlaanderen_df, "aantal_woningen", index)
    gem = (inw_vla / won_vla.replace(0, pd.NA)).fillna(2.0)
    gem = gem.where(gem > 0, 2.0)  # 0 inwoners maar wel woningen → fallback
    won_bru = inw_bru / gem
    return {
        "inwoners_vlaanderen": inw_vla,
        "inwoners_brussel": inw_bru,
        "aantal_woningen_vlaanderen": won_vla,
        "aantal_woningen_brussel": won_bru,
        "gemiddeld_aantal_inwoners_per_huis": gem,
    }


def bouw_regional_layer(
    index: pd.Index,
    vlaanderen_df: pd.DataFrame,
    brussel_db: pd.DataFrame,
) -> pd.DataFrame:
    """
    Regionale sidecar: inwoners/woningen + stocks per Vlaanderen/Brussel.

    Niet onderdeel van FLOW_KOLOMMEN; wordt apart geëxporteerd voor StockManager/simulatie.
    """
    basis = _bereken_regio_basis(vlaanderen_df, brussel_db, index)
    out = pd.DataFrame(
        {kolom: basis[kolom] for kolom in REGIONAL_INWONERS_KOLOMMEN},
        index=index.astype(int),
    )
    out.index.name = "db_ondergrens"

    won_vla = basis["aantal_woningen_vlaanderen"]
    won_bru = basis["aantal_woningen_brussel"]
    stock_vla = {
        "bewoonde_niet_geïsoleerde_woning": won_vla * PCT_NIET_GEISOLEERD,
        "bewoonde_geïsoleerde_woning": won_vla * PCT_GEISOLEERD,
        "onbebouwde_bebouwbare_percelen": 0.0,
        "onbebouwde_onbebouwbare_percelen": 0.0,
        "nieuwe_woning": 0.0,
        "perceel_eigendom_overheid": 0.0,
        "woning_eigendom_overheid": 0.0,
    }
    stock_bru = {
        "bewoonde_niet_geïsoleerde_woning": won_bru * PCT_NIET_GEISOLEERD,
        "bewoonde_geïsoleerde_woning": won_bru * PCT_GEISOLEERD,
        "onbebouwde_bebouwbare_percelen": 0.0,
        "onbebouwde_onbebouwbare_percelen": 0.0,
        "nieuwe_woning": 0.0,
        "perceel_eigendom_overheid": 0.0,
        "woning_eigendom_overheid": 0.0,
    }
    for stock in FLOW_STOCKS:
        out[regional_stock_kolom(stock, "vlaanderen")] = stock_vla.get(stock, 0.0)
        out[regional_stock_kolom(stock, "brussel")] = stock_bru.get(stock, 0.0)

    for kolom in REGIONAL_KOLOMMEN:
        if kolom not in out.columns:
            out[kolom] = 0.0
    return out[list(REGIONAL_KOLOMMEN)]


def bouw_lden_regional() -> pd.DataFrame:
    """Regionale lden-laag uit dezelfde bronnen als bouw_lden."""
    lden_vla, _ = lees_contour_vlaanderen()
    lden_bru = lees_brussel_inwoners_per_db()[0]
    lden_vla = _naar_numeriek(lden_vla, WOONGEBIED_KOLOMMEN)
    index = lden_vla["db_ondergrens"].astype(int)
    return bouw_regional_layer(index, lden_vla, lden_bru)


def bouw_lnight_regional() -> pd.DataFrame:
    """Regionale lnight-laag."""
    _, lnight_vla = lees_contour_vlaanderen()
    lnight_bru = lees_brussel_inwoners_per_db()[1]
    lnight_vla = _naar_numeriek(lnight_vla, WOONGEBIED_KOLOMMEN)
    index = lnight_vla["db_ondergrens"].astype(int)
    return bouw_regional_layer(index, lnight_vla, lnight_bru)


def stap_woongebied_inwoners(
    contour: pd.DataFrame,
    vlaanderen_df: pd.DataFrame,
    brussel_db: pd.DataFrame,
) -> pd.DataFrame:
    """Woongebied-tellers + inwoners_per_contour."""
    out = contour.copy()
    idx = out.index
    out[KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR] = series_op_index(
        vlaanderen_df, KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR, idx
    )
    out[KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR] = series_op_index(
        vlaanderen_df, KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR, idx
    )
    inw_vla = series_op_index(vlaanderen_df, "inwoners", idx)
    inw_bru = series_op_index(brussel_db, "inwoners", idx)
    out["inwoners_per_contour"] = inw_vla + inw_bru
    return out


def stap_stocks_placeholder(
    contour: pd.DataFrame,
    vlaanderen_df: pd.DataFrame,
    brussel_db: pd.DataFrame,
) -> pd.DataFrame:
    """Placeholder stocks: woningen 80/20; percelen/overheid 0."""
    out = contour.copy()
    idx = out.index
    basis = _bereken_regio_basis(vlaanderen_df, brussel_db, idx)
    won_totaal = basis["aantal_woningen_vlaanderen"] + basis["aantal_woningen_brussel"]

    out["bewoonde_niet_geïsoleerde_woning"] = won_totaal * PCT_NIET_GEISOLEERD
    out["bewoonde_geïsoleerde_woning"] = won_totaal * PCT_GEISOLEERD
    out["onbebouwde_bebouwbare_percelen"] = 0.0
    out["onbebouwde_onbebouwbare_percelen"] = 0.0
    out["nieuwe_woning"] = 0.0
    out["perceel_eigendom_overheid"] = 0.0
    out["woning_eigendom_overheid"] = 0.0
    return out


def stap_vergunning_tellers(
    contour: pd.DataFrame,
    verg_contour: pd.DataFrame,
    *,
    jaartal: str | int = JAAR_TELLERS,
    verg_lang_raw: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Vergunning-tellers per db_ondergrens (jaarlijks gemiddelde uit verg_contour)."""
    out = contour.copy()
    if verg_contour.empty:
        return out

    df = verg_contour.copy()
    df = df[df["jaar_indiening"].astype(str) == str(jaartal)]

    def _som_per_band(mask) -> pd.Series:
        subset = df.loc[mask]
        if subset.empty:
            return pd.Series(0.0, index=out.index)
        agg = subset.groupby("db_ondergrens")["waarde"].sum()
        return agg.reindex(out.index).fillna(0)

    nieuwbouw = _som_per_band(
        (df["handeling"] == "Nieuwbouw") & (df["metriek"] == "Aantal wooneenheden")
    )
    kwetsbaar = _som_per_band(df["bron"] == "kwetsbare_functies")
    renovatie = _som_per_band(df["handeling"] == "Verbouwen of hergebruik")

    out["vergunde_wooneenheden_nieuwbouw"] = nieuwbouw
    out["vergunningen_kwetsbare_groep"] = kwetsbaar
    out["renovatie_totaal"] = renovatie

    if verg_lang_raw is not None:
        gem = gem_wooneenheden_per_vergunning_gemiddelde(verg_lang_raw)
    else:
        omg = df[df["bron"] == "omgevingsloket"]
        proj = omg.loc[omg["metriek"] == "Aantal projecten", "waarde"].sum()
        we = omg.loc[omg["metriek"] == "Aantal wooneenheden", "waarde"].sum()
        gem = float(we / proj) if proj > 0 else 0.0
    out["gem_wooneenheden_per_vergunning"] = gem
    return out


def stap_transactie_tellers(
    contour: pd.DataFrame,
    transacties: pd.DataFrame,
    mapping: pd.DataFrame,
) -> pd.DataFrame:
    """Transactietellers per band via capakey-mapping."""
    out = contour.copy()
    if transacties.empty or mapping.empty:
        return out

    tx = transacties.copy()
    tx["sum_ParcelsNumber"] = pd.to_numeric(tx["sum_ParcelsNumber"], errors="coerce").fillna(0)
    gekoppeld = tx.merge(mapping[["capakey", "db_ondergrens"]], on="capakey", how="inner")

    def _agg_segment(segmenten: list[str]) -> pd.Series:
        subset = gekoppeld[gekoppeld["segment"].isin(segmenten)]
        if subset.empty:
            return pd.Series(0.0, index=out.index)
        agg = subset.groupby("db_ondergrens")["sum_ParcelsNumber"].sum()
        return agg.reindex(out.index).fillna(0)

    out["alle_transacties_percelen"] = _agg_segment(["industrie_terrein", "industrie_bebouwd"])
    out["alle_verkopen_onbebouwde_bebouwbare_percelen"] = out["alle_transacties_percelen"]
    out["alle_transacties_woningen"] = _agg_segment(["woningen", "appartementen"])
    out["alle_verkopen_woningen"] = out["alle_transacties_woningen"]
    return out


def stap_prijzen(contour: pd.DataFrame, prijzen_contour: pd.DataFrame) -> pd.DataFrame:
    """Vier prijskolommen per db_ondergrens."""
    out = contour.copy()
    if prijzen_contour.empty:
        return out
    prijzen = prijzen_contour.set_index("db_ondergrens")
    for kolom in PRIJS_KOLOMMEN:
        if kolom in prijzen.columns:
            out[kolom] = prijzen[kolom].reindex(out.index)
    return out


def stap_tellers_placeholder(contour: pd.DataFrame) -> pd.DataFrame:
    """Placeholder voor tellers zonder bron (R+, iso-split nieuwbouw, buffers)."""
    out = contour.copy()
    for kolom in (
        "R+",
        "R−",
        "nieuwbouw_geïsoleerd",
        "nieuwbouw_niet_geïsoleerd",
        "potentieel_isoleerbare_woningen",
    ):
        out[kolom] = 0.0
    return out


def bouw_lden(
    *,
    verg_contour: pd.DataFrame | None = None,
    transacties: pd.DataFrame | None = None,
    capakey_mapping: pd.DataFrame | None = None,
    prijzen_contour: pd.DataFrame | None = None,
    jaartal_vergunningen: str | int = JAAR_TELLERS,
    verg_lang_raw: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Volledige FLOW-lden tabel."""
    lden_vla, _ = lees_contour_vlaanderen()
    lden_bru = lees_brussel_inwoners_per_db()[0]
    lden_vla = _naar_numeriek(lden_vla, WOONGEBIED_KOLOMMEN)

    lden = init_contour_shell(lden_vla)
    lden = stap_woongebied_inwoners(lden, lden_vla, lden_bru)
    lden = stap_stocks_placeholder(lden, lden_vla, lden_bru)
    if verg_contour is not None:
        lden = stap_vergunning_tellers(
            lden,
            verg_contour,
            jaartal=jaartal_vergunningen,
            verg_lang_raw=verg_lang_raw,
        )
    if transacties is not None and capakey_mapping is not None:
        lden = stap_transactie_tellers(lden, transacties, capakey_mapping)
    if prijzen_contour is not None:
        lden = stap_prijzen(lden, prijzen_contour)
    lden = stap_tellers_placeholder(lden)
    return lden


def bouw_lnight(
    *,
    verg_contour: pd.DataFrame | None = None,
    transacties: pd.DataFrame | None = None,
    capakey_mapping: pd.DataFrame | None = None,
    prijzen_contour: pd.DataFrame | None = None,
    jaartal_vergunningen: str | int = JAAR_TELLERS,
    verg_lang_raw: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Volledige FLOW-lnight tabel (zelfde tellers/prijzen als lden)."""
    _, lnight_vla = lees_contour_vlaanderen()
    lnight_bru = lees_brussel_inwoners_per_db()[1]
    lnight_vla = _naar_numeriek(lnight_vla, WOONGEBIED_KOLOMMEN)

    lnight = init_contour_shell(lnight_vla)
    lnight = stap_woongebied_inwoners(lnight, lnight_vla, lnight_bru)
    lnight = stap_stocks_placeholder(lnight, lnight_vla, lnight_bru)
    if verg_contour is not None:
        lnight = stap_vergunning_tellers(
            lnight,
            verg_contour,
            jaartal=jaartal_vergunningen,
            verg_lang_raw=verg_lang_raw,
        )
    if transacties is not None and capakey_mapping is not None:
        lnight = stap_transactie_tellers(lnight, transacties, capakey_mapping)
    if prijzen_contour is not None:
        lnight = stap_prijzen(lnight, prijzen_contour)
    lnight = stap_tellers_placeholder(lnight)
    return lnight


# Aliassen voor backwards-compat
bouw_contour_lden = bouw_lden
bouw_contour_lnight = bouw_lnight


def vergunningen_gemeente_tabel(df_lang: pd.DataFrame) -> pd.DataFrame:
    """Aggregate long permits to gemeente x jaar x handeling x metriek."""
    df = df_lang.copy()
    df = df[df["gemeente"].notna() & ~df["gemeente"].isin(["-", "Totalen", ""])]
    dim = ["bron", "gemeente", "jaar_indiening", "handeling", "gebouw_functie", "metriek"]
    return df.groupby(dim, dropna=False)["waarde"].sum().reset_index()
