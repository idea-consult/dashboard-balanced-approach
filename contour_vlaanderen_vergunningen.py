"""Hulpfuncties voor vergunningen-aggregatie en proportionele toewijzing."""

from __future__ import annotations

import polars as pl

GEMEENTE_UITSLUITING = ("Totalen", "-", "(deels) Niet in Vlaanderen")
VERGUNNINGEN_JAREN = (2021, 2025)


def vergunningen_gemiddeld_per_gemeente(
    df_vergunningen: pl.DataFrame,
    *,
    handeling: str,
    metriek: str = "Aantal wooneenheden",
    gebouw_functie: str | None = "Totalen",
    jaar_start: int = VERGUNNINGEN_JAREN[0],
    jaar_eind: int = VERGUNNINGEN_JAREN[1],
) -> pl.DataFrame:
    """Jaarlijks gemiddelde vergunningen per gemeente over ``jaar_start``–``jaar_eind``."""
    n_jaren = jaar_eind - jaar_start + 1
    filter_expr = (
        (pl.col("handeling") == handeling)
        & pl.col("jaar_indiening").cast(pl.Int64, strict=False).is_between(jaar_start, jaar_eind)
        & (pl.col("metriek") == metriek)
        & (~pl.col("gemeente").is_in(GEMEENTE_UITSLUITING))
    )
    if gebouw_functie is not None:
        filter_expr = filter_expr & (pl.col("gebouw_functie") == gebouw_functie)
    return (
        df_vergunningen.filter(filter_expr)
        .group_by("gemeente")
        .agg((pl.col("waarde").sum() / n_jaren).alias("gemiddeld_per_jaar"))
        .sort("gemeente")
    )


def wijs_proportioneel_toe(
    df: pl.DataFrame,
    df_bron: pl.DataFrame,
    *,
    groep_kolom: str,
    bron_waarde_kolom: str,
    gewicht_kolom: str,
    uitvoer_kolom: str,
    bron_groep_kolom: str | None = None,
    doorgeef_kolommen: tuple[str, ...] = (),
) -> pl.DataFrame:
    """Verdeel één totaalbedrag per groep proportioneel over meerdere rijen in ``df``.

    Deze functie lost een veelvoorkomend probleem op in onze contour-analyse: brondata
    liggen op een **hoger aggregatieniveau** (gemeente, statistische sector, …), terwijl
    onze werkdataset **intersectierijen** bevat (overlap statistische sector × db-contour).
    Meerdere intersectierijen delen dezelfde groepssleutel (bv. dezelfde gemeente of sector).

    **Kernidee**

    Voor elke groep ``G`` (bv. gemeente A) staat in ``df_bron`` één waarde ``V`` (bv. 100
    vergunningen per jaar). In ``df`` zijn er meerdere rijen met ``groep_kolom == G``, elk
    met een gewicht ``w_i`` (bv. aantal woningen of onbebouwde percelen in die intersectie).
    Rij ``i`` krijgt:

    .. math::

        \\text{uitvoer}_i = V \\times \\frac{w_i}{\\sum_j w_j}

    waarbij de som enkel over alle rijen in ``df`` loopt die tot dezelfde groep ``G`` behoren.

    **Voorbeeld**

    Gemeente X heeft gemiddeld 100 nieuwbouwvergunningen per jaar. De overlap-dataset heeft
    twee intersecties in gemeente X:

    - intersectie 1: 20 woningen  → 100 × 20/50 = **40** vergunningen
    - intersectie 2: 30 woningen  → 100 × 30/50 = **60** vergunningen

    De som over de intersecties is opnieuw 100 (**conservatie**).

    **Parameters**

    ``df``
        Intersectietabel: elke rij is één overlap sector–contour. Moet ``groep_kolom`` en
        ``gewicht_kolom`` bevatten.

    ``df_bron``
        Bronwaarden per groep: één rij per groep met het totaal dat verdeeld moet worden.
        Moet ``bron_groep_kolom`` (of ``groep_kolom``) en ``bron_waarde_kolom`` bevatten.

    ``groep_kolom``
        Kolom in ``df`` die intersecties groepeert (bv. ``naam_gemeente_nl``,
        ``nis_sector``).

    ``bron_waarde_kolom``
        Kolom in ``df_bron`` met het te verdelen bedrag per groep (bv.
        ``gemiddeld_per_jaar``, ``aantal_transacties_per_jaar``,
        ``gemiddelde_jaarlijkse_groei``).

    ``gewicht_kolom``
        Kolom in ``df`` die bepaalt hoe het bedrag over intersecties binnen dezelfde groep
        wordt gesplitst (bv. ``aantal_woningen``,
        ``aantal_percelen_onbebouwd_woongebied``).

    ``uitvoer_kolom``
        Naam van de nieuwe kolom in ``df`` waarin het toegewezen bedrag per intersectie
        wordt geschreven.

    ``bron_groep_kolom``
        Optioneel. Groepskolom in ``df_bron`` als die anders heet dan in ``df`` (bv.
        ``gemeente`` in de bron vs. ``naam_gemeente_nl`` in ``df``). Standaard gelijk aan
        ``groep_kolom``.

    ``doorgeef_kolommen``
        Optionele kolommen uit ``df_bron`` die **niet** proportioneel worden verdeeld,
        maar per groep ongewijzigd aan elke intersectierij worden gekoppeld (bv.
        ``gemiddelde_prijs_van_een_woning`` bij transacties: elke intersectie in dezelfde
        sector krijgt dezelfde sectorprijs).

    **Stappen in de implementatie**

    1. Per groep in ``df``: sommeer ``gewicht_kolom`` → ``_totaal_gewicht``.
    2. Koppel ``df_bron`` aan ``df`` via de groepssleutel.
    3. Bereken ``uitvoer_kolom`` met de formule hierboven.
    4. Als ``_totaal_gewicht == 0`` (geen gewicht in die groep): uitvoer = 0.

    **Randgevallen**

    - Ontbrekende bronwaarde voor een groep → behandeld als 0.
    - Ontbrekende gewichten → behandeld als 0 (via ``fill_null(0)``).
    - Groepen in ``df_bron`` zonder rijen in ``df`` → geen effect (worden niet toegewezen).
    - Groepen in ``df`` zonder rij in ``df_bron`` → uitvoer 0 voor die intersecties.

    **Retourwaarde**

    ``df`` met alle oorspronkelijke kolommen, plus ``uitvoer_kolom`` (en eventueel
    ``doorgeef_kolommen``). Tijdelijke hulpkolommen worden verwijderd.

    **Gebruik in dit project**

    - Vergunningen nieuwbouw/renovatie/kwetsbare groepen (Vlaanderen): groep = gemeente,
      gewicht = percelen of woningen.
    - Transacties: groep = statistische sector, gewicht = aantal woningen.
    - Nieuwbouw Brussel: groep = gemeente, gewicht = aantal woningen, bron = gemiddelde
      groei woningbestand.
    """
    bron_groep = bron_groep_kolom or groep_kolom
    bron_waarde_intern = f"_{bron_waarde_kolom}_bron"

    totaal_gewicht = df.group_by(groep_kolom).agg(
        pl.col(gewicht_kolom).fill_null(0).sum().alias("_totaal_gewicht")
    )
    bron_select = [bron_groep, bron_waarde_kolom, *doorgeef_kolommen]
    df_bron = df_bron.select(bron_select).rename({bron_waarde_kolom: bron_waarde_intern})

    result = (
        df.join(totaal_gewicht, on=groep_kolom, how="left")
        .join(df_bron, left_on=groep_kolom, right_on=bron_groep, how="left")
        .with_columns(
            pl.when(pl.col("_totaal_gewicht") > 0)
            .then(
                pl.col(bron_waarde_intern).fill_null(0)
                * pl.col(gewicht_kolom).fill_null(0)
                / pl.col("_totaal_gewicht")
            )
            .otherwise(0.0)
            .alias(uitvoer_kolom)
        )
        .drop("_totaal_gewicht", bron_waarde_intern, strict=False)
    )
    if bron_groep != groep_kolom:
        result = result.drop(bron_groep, strict=False)
    return result
