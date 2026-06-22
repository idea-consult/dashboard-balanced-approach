"""FLOW §2.0 contour schema: 27 kolommen, index db_ondergrens."""

from __future__ import annotations

import pandas as pd

INDEX_NAME = "db_ondergrens"

FLOW_STOCKS: tuple[str, ...] = (
    "onbebouwde_bebouwbare_percelen",
    "onbebouwde_onbebouwbare_percelen",
    "bewoonde_niet_geïsoleerde_woning",
    "bewoonde_geïsoleerde_woning",
    "nieuwe_woning",
    "perceel_eigendom_overheid",
    "woning_eigendom_overheid",
)

FLOW_TELLERS: tuple[str, ...] = (
    "bebouwbare_percelen_woongebied(5jr)",
    "niet_bebouwbare_percelen_woongebied_schrapping(5jr)",
    "alle_transacties_percelen",
    "alle_verkopen_onbebouwde_bebouwbare_percelen",
    "alle_transacties_woningen",
    "alle_verkopen_woningen",
    "vergunde_wooneenheden_nieuwbouw",
    "gem_wooneenheden_per_vergunning",
    "vergunningen_kwetsbare_groep",
    "renovatie_totaal",
    "R+",
    "R−",
    "nieuwbouw_geïsoleerd",
    "nieuwbouw_niet_geïsoleerd",
    "potentieel_isoleerbare_woningen",
    "inwoners_per_contour",
)

FLOW_PRIJZEN: tuple[str, ...] = (
    "prijs_onbebouwde_bebouwbare_percelen",
    "prijs_onbebouwde_onbebouwbare_percelen",
    "prijs_bewoonde_niet_geïsoleerde_woning",
    "prijs_bewoonde_geïsoleerde_woning",
)

FLOW_KOLOMMEN: tuple[str, ...] = FLOW_STOCKS + FLOW_TELLERS + FLOW_PRIJZEN

REGIONS: tuple[str, ...] = ("vlaanderen", "brussel")

REGIONAL_INWONERS_KOLOMMEN: tuple[str, ...] = (
    "inwoners_vlaanderen",
    "inwoners_brussel",
    "aantal_woningen_vlaanderen",
    "aantal_woningen_brussel",
    "gemiddeld_aantal_inwoners_per_huis",
)


def regional_stock_kolom(stock: str, regio: str) -> str:
    """Kolomnaam in regional sidecar: `{stock}_{regio}`."""
    return f"{stock}_{regio}"


def regional_stock_kolommen(stocks: tuple[str, ...] = FLOW_STOCKS) -> tuple[str, ...]:
    """Alle regionale stock-kolommen (Vlaanderen + Brussel)."""
    return tuple(
        regional_stock_kolom(stock, regio) for stock in stocks for regio in REGIONS
    )


REGIONAL_KOLOMMEN: tuple[str, ...] = REGIONAL_INWONERS_KOLOMMEN + regional_stock_kolommen()


def band_metadata(index: pd.Index) -> pd.DataFrame:
    """Technische bandinfo voor ruimtelijke joins (niet opgeslagen in FLOW-contour)."""
    db = index.astype(int)
    meta = pd.DataFrame(
        {
            "db_bovengrens": db + 1,
            "geluidscontour": db.astype(str) + "-" + (db + 1).astype(str),
        },
        index=pd.Index(db, name=INDEX_NAME),
    )
    return meta


def banden_dataframe(index: pd.Index) -> pd.DataFrame:
    """Bandmetadata met db_ondergrens als kolom (voor merges)."""
    return band_metadata(index).reset_index()


def leeg_contour(index: pd.Index) -> pd.DataFrame:
    """Leeg FLOW-contour met alle 27 kolommen op 0."""
    return pd.DataFrame(0.0, index=index.astype(int), columns=list(FLOW_KOLOMMEN))


def init_contour_shell(vlaanderen_df: pd.DataFrame) -> pd.DataFrame:
    """Start-shell op db_ondergrens uit geladen Vlaanderen-contour."""
    index = vlaanderen_df["db_ondergrens"].astype(int)
    df = leeg_contour(index)
    df.index.name = INDEX_NAME
    return df


def init_contour_index(vlaanderen_df: pd.DataFrame) -> pd.DataFrame:
    """Lege contour-shell: alleen index db_ondergrens, nog geen FLOW-kolommen."""
    index = vlaanderen_df["db_ondergrens"].astype(int)
    df = pd.DataFrame(index=index)
    df.index.name = INDEX_NAME
    return df


def init_lden_lnight(
    vlaanderen_lden: pd.DataFrame,
    vlaanderen_lnight: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lege lden/lnight shells met index db_ondergrens."""
    return init_contour_shell(vlaanderen_lden), init_contour_shell(vlaanderen_lnight)


def init_lden_lnight_index(
    vlaanderen_lden: pd.DataFrame,
    vlaanderen_lnight: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """lden/lnight met alleen index (kolommen worden stapsgewijs toegevoegd)."""
    return init_contour_index(vlaanderen_lden), init_contour_index(vlaanderen_lnight)


def assert_flow_schema(df: pd.DataFrame) -> None:
    """Valideer exact FLOW-schema (kolommen + index)."""
    if list(df.columns) != list(FLOW_KOLOMMEN):
        missing = set(FLOW_KOLOMMEN) - set(df.columns)
        extra = set(df.columns) - set(FLOW_KOLOMMEN)
        raise AssertionError(f"Kolom mismatch. Ontbreekt: {missing}. Extra: {extra}")
    if df.index.name != INDEX_NAME:
        raise AssertionError(f"Index moet '{INDEX_NAME}' zijn, got {df.index.name!r}")


def toon_stap(
    stap_naam: str,
    lden: pd.DataFrame,
    lnight: pd.DataFrame | None = None,
    vorige_kolommen: list[str] | None = None,
) -> list[str]:
    """Print kolomoverzicht na een bouwstap; retourneert huidige kolomlijst."""
    cols = list(lden.columns)
    nieuw = [c for c in cols if vorige_kolommen is None or c not in vorige_kolommen]
    print(f"=== {stap_naam} ===")
    print(f"lden.shape: {lden.shape}")
    print(f"lden.columns ({len(cols)}): {cols}")
    if nieuw:
        print(f"  + nieuw: {nieuw}")
    if lnight is not None:
        print(f"lnight.columns ({len(lnight.columns)}): {list(lnight.columns)}")
    return cols


def contour_voor_export(df: pd.DataFrame) -> pd.DataFrame:
    """Zet index db_ondergrens als kolom voor CSV-export."""
    assert_flow_schema(df)
    out = df.copy()
    out.insert(0, INDEX_NAME, out.index)
    return out


def regional_voor_export(df: pd.DataFrame) -> pd.DataFrame:
    """Zet index db_ondergrens als kolom voor regional CSV-export."""
    out = df.copy()
    out.insert(0, INDEX_NAME, out.index)
    return out


def regional_uit_export(df: pd.DataFrame) -> pd.DataFrame:
    """Lees geëxporteerde regional CSV terug (index db_ondergrens)."""
    work = df.copy()
    if INDEX_NAME in work.columns:
        work = work.set_index(INDEX_NAME)
    work.index = work.index.astype(int)
    work.index.name = INDEX_NAME
    return work


def contour_uit_export(df: pd.DataFrame) -> pd.DataFrame:
    """Lees geëxporteerde CSV terug naar FLOW-contour."""
    work = df.copy()
    if INDEX_NAME in work.columns:
        work = work.set_index(INDEX_NAME)
    work.index = work.index.astype(int)
    work.index.name = INDEX_NAME
    assert_flow_schema(work)
    return work
