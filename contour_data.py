import marimo

__generated_with = "0.23.9"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Contour data — laden en consolidatie

    Dit notebook laadt alle bronnen uit `data/`, consolideert master-tabellen en schrijft parquet naar `output/intermediate/`.

    Referentie: [STOCKS_EN_FLOWS_BEREKENEN.md §2](../STOCKS_EN_FLOWS_BEREKENEN.md). Logica zit in het package `contour/`.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Deel A — Data-inventaris (FLOW §2)

    #### Kolomoverzicht (`df_data_inventory`)

    | Kolom | Beschrijving |
    |-------|----------------|
    | `bestand` | Bestandsnaam in `data/` |
    | `pad` | Volledig pad naar bron |
    | `beschrijving` | Korte inhoud (lden/lnight, vergunningen, ...) |
    | `rijen` | Aantal rijen (CSV) of `None` (Excel) |
    | `kolommen` | Kolomnamen of tabbladen |
    | `status` | `ok` / `deels` t.o.v. FLOW §2 |
    """)
    return


@app.cell
def _():
    from contour.inventory import maak_data_inventory

    df_data_inventory = maak_data_inventory()
    df_data_inventory
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Deel B — Laden ruwe bronnen

    #### Kolomoverzicht (ruwe bronnen na laden)

    **`raw_vlaanderen_lden` / `raw_vlaanderen_lnight`** — na `hernoem_vlaanderen_kolommen()`:

    | Kolom | Beschrijving |
    |-------|----------------|
    | `geluidscontour` | Bandlabel (bv. `45-46`) |
    | `db_ondergrens` / `db_bovengrens` | dB-grenzen van de band |
    | `inwoners` | Inwoners Vlaanderen (+ rest land) in contour |
    | `aantal_woningen` | Woningen Vlaanderen in contour |
    | `aantal bebouwbare percelen die werden gecreëerd door woongebieden aan te duiden` | Flow-teller woongebied-aanduiding (cumulatief 5 jr; Excel-naam ongewijzigd) |
    | `aantal niet-bebouwbarepercelen die worden gecreëerd door woongebied te schrappen` | Woongebied-schrapping (Excel-naam ongewijzigd) |

    **`raw_brussel_lden`** (sector, selectie kolommen):

    | Kolom | Beschrijving |
    |-------|----------------|
    | `dB` | dB-waarde van de contour |
    | `Population dans le contour` | Inwoners sector in contour |
    | `T_MUN_NL` | Gemeentenaam (NL) |

    **`vergunningen_*` (lang CSV)** — kolommen `bron`, `jaar_indiening`, `gemeente`, `handeling`, `gebouw_functie`, `metriek`, `waarde`.

    **`transacties`** — per segment samengevoegd:

    | Kolom | Beschrijving |
    |-------|----------------|
    | `capakey` | Kadastraal perceel (hernoemd uit `NISCode`) |
    | `sum_ParcelsNumber` | Aantal transacties op perceel |
    | `avg_PriceP25` / `avg_PriceP50` / `avg_PriceP75` | Prijspercentielen |
    | `avg_ParcelsAreaP50` | Mediane perceeloppervlakte |
    | `average_price_m2` | Gemiddelde prijs per m² |
    | `segment` | `woningen`, `appartementen`, `handel`, ... |
    """)
    return


@app.cell
def _():
    from contour.loaders import (
        lees_contour_vlaanderen,
        lees_brussel_sector,
        lees_vergunningen,
        lees_transacties,
    )

    raw_vlaanderen_lden, raw_vlaanderen_lnight = lees_contour_vlaanderen()
    raw_brussel_lden, raw_brussel_lnight = lees_brussel_sector()
    vergunningen_omgevingsloket, kwetsbare, verkaveling = lees_vergunningen()
    transacties = lees_transacties()

    print('Vlaanderen lden:', raw_vlaanderen_lden.shape)
    print('Brussel lden:', raw_brussel_lden.shape)
    print('Vergunningen omg:', len(vergunningen_omgevingsloket))
    print('Transacties:', len(transacties))
    return (
        lees_brussel_sector,
        lees_contour_vlaanderen,
        lees_transacties,
        lees_vergunningen,
        raw_brussel_lden,
        raw_vlaanderen_lden,
    )


@app.cell
def _(raw_vlaanderen_lden):
    raw_vlaanderen_lden
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Deel B2 — Traceerbare opbouw `lden` / `lnight`

    Elke kolom uit FLOW §2.0 (27 variabelen) krijgt **één eigen stap**: eerst documentatie (beschrijving, bron, berekenmethode), daarna de code die `lden["…"]` en `lnight["…"]` vult.

    - **Stap 0**: alleen index `db_ondergrens` (nog geen kolommen)
    - **Stappen 1–27**: één variabele per stap
    - **Stap 28**: kolomvolgorde FLOW + schema-check

    Na elke stap: `toon_stap(...)` toont welke kolom nieuw is.
    """)
    return


@app.cell
def _(lees_brussel_sector, lees_contour_vlaanderen, lees_transacties):
    # Setup — laad ruwe bronnen (idempotent)
    from pathlib import Path
    import pandas as pd
    from contour.columns import KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR, KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR, WOONGEBIED_KOLOMMEN
    from contour.consolidate import JAAR_TELLERS, PCT_GEISOLEERD, PCT_NIET_GEISOLEERD, series_op_index
    from contour.loaders import lees_brussel_inwoners_per_db, lees_sector_contour_beide
    from contour.prices import bereken_prijzen_uit_transacties
    from contour.schema import assert_flow_schema, init_lden_lnight_index, toon_stap
    from contour.spatial import conversietabel_gemeente_naar_db, koppel_conversie_aan_contourband, verdeel_gemeente_naar_contour
    from contour.vergunningen import combineer_vergunningen_lang

    def _naar_numeriek(df, kolommen):
        out = df.copy()
        for k in kolommen:
            if k in out.columns:
                out[k] = pd.to_numeric(out[k], errors='coerce').fillna(0)
        return out
    raw_vlaanderen_lden_1, raw_vlaanderen_lnight_1 = lees_contour_vlaanderen()
    raw_vlaanderen_lden_1 = _naar_numeriek(raw_vlaanderen_lden_1, WOONGEBIED_KOLOMMEN)
    raw_vlaanderen_lnight_1 = _naar_numeriek(raw_vlaanderen_lnight_1, WOONGEBIED_KOLOMMEN)
    lden_bru_db, lnight_bru_db = lees_brussel_inwoners_per_db()
    brussel_lden, _ = lees_brussel_sector()
    # Ruwe bronnen — nog geen aggregatie naar lden-kolommen
    transacties_1 = lees_transacties()
    return (
        JAAR_TELLERS,
        KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR,
        KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR,
        PCT_GEISOLEERD,
        PCT_NIET_GEISOLEERD,
        assert_flow_schema,
        bereken_prijzen_uit_transacties,
        brussel_lden,
        combineer_vergunningen_lang,
        conversietabel_gemeente_naar_db,
        init_lden_lnight_index,
        koppel_conversie_aan_contourband,
        lden_bru_db,
        lees_sector_contour_beide,
        lnight_bru_db,
        pd,
        raw_vlaanderen_lden_1,
        raw_vlaanderen_lnight_1,
        series_op_index,
        toon_stap,
        transacties_1,
        verdeel_gemeente_naar_contour,
    )




@app.cell
def _(mo):
    """Gedeelde B2-state (marimo: één definitie per variabele)."""
    lden_b2, set_lden_b2 = mo.state(None)
    lnight_b2, set_lnight_b2 = mo.state(None)
    vorige_kolommen, set_vorige_kolommen = mo.state(None)
    return (
        lden_b2,
        lnight_b2,
        set_lden_b2,
        set_lnight_b2,
        set_vorige_kolommen,
        vorige_kolommen,
    )

@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 0 — Index `db_ondergrens`

    #### Beschrijving

    Startdataframe met de 30 geluidsbanden (dB-ondergrens 45–74) als index. Nog geen FLOW-variabelen.

    #### Bron

    - `data/contour_vlaanderen_stocks.xlsx` — kolom `db_ondergrens` (via `lees_contour_vlaanderen()`)

    #### Berekenmethode

    De banden worden overgenomen uit de Vlaanderen Lden-contour; Lnight gebruikt dezelfde bandindeling.
    """)
    return


@app.cell
def _(
    init_lden_lnight_index,
    raw_vlaanderen_lden_1,
    raw_vlaanderen_lnight_1,
    set_lden_b2,
    set_lnight_b2,
    set_vorige_kolommen,
    toon_stap,
):
    _lden, _lnight = init_lden_lnight_index(raw_vlaanderen_lden_1, raw_vlaanderen_lnight_1)
    _kolommen_na_stap = toon_stap('0 index', _lden, _lnight)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    list(_lden.columns)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 1 — `inwoners_per_contour`

    #### Beschrijving

    Totaal aantal inwoners per geluidscontourband rond de luchthaven (Vlaanderen + Brussel). Gebruikt voor KPI's en kostengewichting in de simulator; geen flow-teller.

    #### Bron

    - `data/contour_vlaanderen_stocks.xlsx` — inwoners Vlaanderen per 1 dB-band (`lden` / `lnight` sheet)
    - `data/inwoners_brussel_sector_contour_2024.xlsx` — inwoners Brussel per statistische sector, geaggregeerd naar dB via `lees_brussel_inwoners_per_db()`

    #### Berekenmethode

    **Vlaanderen:** waarde `inwoners` per `db_ondergrens` rechtstreeks overnemen uit de contour-Excel.

    **Brussel:** enkel inwoners per statistische sector beschikbaar; deze worden via de sector–contour-koppeling (`population 2024 par bout de secteur stat.xlsx`) naar dB-banden vertaald en gesommeerd.

    **Totaal:** `inwoners_per_contour = inwoners_vlaanderen + inwoners_brussel` per band.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, lden_bru_db, lnight_bru_db, raw_vlaanderen_lden_1, raw_vlaanderen_lnight_1, series_op_index, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'inwoners_per_contour'
    _idx = _lden.index
    _inw_vla_lden = series_op_index(raw_vlaanderen_lden_1, 'inwoners', _idx)
    _inw_bru_lden = series_op_index(lden_bru_db, 'inwoners', _idx)
    _lden[_KOL] = _inw_vla_lden + _inw_bru_lden
    _inw_vla_lnight = series_op_index(raw_vlaanderen_lnight_1, 'inwoners', _idx)
    _inw_bru_lnight = series_op_index(lnight_bru_db, 'inwoners', _idx)
    _lnight[_KOL] = _inw_vla_lnight + _inw_bru_lnight
    _kolommen_na_stap = toon_stap(f'1 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 2 — `bebouwbare_percelen_woongebied(5jr)`

    #### Beschrijving

    Cumulatief aantal **bebouwbare percelen** dat in de laatste 5 jaar werd gecreëerd door woongebieden aan te duiden. Flow-teller (jaarlijks = waarde / 5); geen stock.

    #### Bron

    - `data/contour_vlaanderen_stocks.xlsx` — kolom *aantal bebouwbare percelen die werden gecreëerd door woongebieden aan te duiden* (hernoemd bij laden)

    #### Berekenmethode

    Waarde per `db_ondergrens` overnemen uit de Vlaanderen-contour (`series_op_index`). Brussel: geen aparte bron → 0 waar geen Vlaanderen-data.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR, raw_vlaanderen_lden_1, raw_vlaanderen_lnight_1, series_op_index, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR
    _idx = _lden.index
    _lden[_KOL] = series_op_index(raw_vlaanderen_lden_1, _KOL, _idx)
    _lnight[_KOL] = series_op_index(raw_vlaanderen_lnight_1, _KOL, _idx)
    _kolommen_na_stap = toon_stap(f'2 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 3 — `niet_bebouwbare_percelen_woongebied_schrapping(5jr)`

    #### Beschrijving

    Cumulatief aantal **niet-bebouwbare percelen** door schrapping van woongebied (laatste 5 jaar). Flow-teller; geen stock.

    #### Bron

    - `data/contour_vlaanderen_stocks.xlsx` — kolom *aantal niet-bebouwbare percelen die worden gecreëerd door woongebied te schrappen*

    #### Berekenmethode

    Waarde per `db_ondergrens` overnemen uit de Vlaanderen-contour.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR, raw_vlaanderen_lden_1, raw_vlaanderen_lnight_1, series_op_index, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR
    _idx = _lden.index
    _lden[_KOL] = series_op_index(raw_vlaanderen_lden_1, _KOL, _idx)
    _lnight[_KOL] = series_op_index(raw_vlaanderen_lnight_1, _KOL, _idx)
    _kolommen_na_stap = toon_stap(f'3 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 4 — `bewoonde_niet_geïsoleerde_woning`

    #### Beschrijving

    Stock bewoonde **niet-geïsoleerde** woningen per geluidsband.

    #### Bron

    - `data/contour_vlaanderen_stocks.xlsx` — `aantal_woningen` (huizen) per band
    - `data/inwoners_brussel_sector_contour_2024.xlsx` + Brusselse inwoners per dB (stap 1) — geschatte woningen Brussel

    #### Berekenmethode

    1. Woningen Vlaanderen per band uit contour-Excel.
    2. Woningen Brussel = `inwoners_brussel / gemiddeld_inwoners_per_woning_vlaanderen` (fallback **2,0** bij ontbrekende data of wanneer het gemiddelde 0 is — bv. 0 inwoners maar wel woningen in Vlaanderen per band).
    3. Totaal woningen = Vlaanderen + Brussel.
    4. **Beleidsaanname (placeholder):** 80% van totaal = niet-geïsoleerd (`PCT_NIET_GEISOLEERD = 0,80`).
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, PCT_NIET_GEISOLEERD, lden_bru_db, lnight_bru_db, pd, raw_vlaanderen_lden_1, raw_vlaanderen_lnight_1, series_op_index, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'bewoonde_niet_geïsoleerde_woning'
    _idx = _lden.index
    _inw_vla_lden = series_op_index(raw_vlaanderen_lden_1, 'inwoners', _idx)
    _inw_bru_lden = series_op_index(lden_bru_db, 'inwoners', _idx)
    _won_vla_lden = series_op_index(raw_vlaanderen_lden_1, 'aantal_woningen', _idx)
    _gem_inw_per_huis_lden = (_inw_vla_lden / _won_vla_lden.replace(0, pd.NA)).fillna(2.0)
    _gem_inw_per_huis_lden = _gem_inw_per_huis_lden.where(_gem_inw_per_huis_lden > 0, 2.0)
    _won_bru_lden = _inw_bru_lden / _gem_inw_per_huis_lden
    won_totaal_lden = _won_vla_lden + _won_bru_lden
    _lden[_KOL] = won_totaal_lden * PCT_NIET_GEISOLEERD
    _inw_vla_lnight = series_op_index(raw_vlaanderen_lnight_1, 'inwoners', _idx)
    _inw_bru_lnight = series_op_index(lnight_bru_db, 'inwoners', _idx)
    _won_vla_lnight = series_op_index(raw_vlaanderen_lnight_1, 'aantal_woningen', _idx)
    _gem_inw_per_huis_lnight = (_inw_vla_lnight / _won_vla_lnight.replace(0, pd.NA)).fillna(2.0)
    _gem_inw_per_huis_lnight = _gem_inw_per_huis_lnight.where(_gem_inw_per_huis_lnight > 0, 2.0)
    _won_bru_lnight = _inw_bru_lnight / _gem_inw_per_huis_lnight
    won_totaal_lnight = _won_vla_lnight + _won_bru_lnight
    _lnight[_KOL] = won_totaal_lnight * PCT_NIET_GEISOLEERD
    _kolommen_na_stap = toon_stap(f'4 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 5 — `bewoonde_geïsoleerde_woning`

    #### Beschrijving

    Stock bewoonde **geïsoleerde** woningen per geluidsband.

    #### Bron

    Zelfde bronnen als stap 4 (woningen Vlaanderen + geschat Brussel).

    #### Berekenmethode

    **Beleidsaanname (placeholder):** 20% van totaal woningen per band (`PCT_GEISOLEERD = 0,20`). Gebruikt `won_totaal_lden` / `won_totaal_lnight` uit stap 4.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, PCT_GEISOLEERD, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'bewoonde_geïsoleerde_woning'
    _lden[_KOL] = won_totaal_lden * PCT_GEISOLEERD
    _lnight[_KOL] = won_totaal_lnight * PCT_GEISOLEERD
    _kolommen_na_stap = toon_stap(f'5 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 6 — `onbebouwde_bebouwbare_percelen`

    #### Beschrijving

    Stock **onbebouwde bebouwbare percelen** per geluidsband (noemer voor o.a. aankoop/voorkoop percelen).

    #### Bron

    Nog geen betrouwbare kadastrale/ruimtelijke stock per contour in de pipeline.

    #### Berekenmethode

    **Placeholder 0** tot gedetailleerde perceel-stock per band beschikbaar is. Niet afleiden uit woongebied-tellers.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'onbebouwde_bebouwbare_percelen'
    _lden[_KOL] = 0.0
    _lnight[_KOL] = 0.0
    _kolommen_na_stap = toon_stap(f'6 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 7 — `onbebouwde_onbebouwbare_percelen`

    #### Beschrijving

    Stock **onbebouwde onbebouwbare percelen** per band (o.a. noemer woongebiedverbod).

    #### Bron

    Nog geen directe bron per contour.

    #### Berekenmethode

    **Placeholder 0.**
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'onbebouwde_onbebouwbare_percelen'
    _lden[_KOL] = 0.0
    _lnight[_KOL] = 0.0
    _kolommen_na_stap = toon_stap(f'7 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 8 — `nieuwe_woning`

    #### Beschrijving

    Stock **nieuwe woningen** (bv. in aanbouw) per band.

    #### Bron

    Nog niet gemodelleerd in beschikbare data.

    #### Berekenmethode

    **Placeholder 0.**
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'nieuwe_woning'
    _lden[_KOL] = 0.0
    _lnight[_KOL] = 0.0
    _kolommen_na_stap = toon_stap(f'8 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 9 — `perceel_eigendom_overheid`

    #### Beschrijving

    Aandeel onbebouwde percelen in **overheidsbezit** per band.

    #### Bron

    Nog geen eigendomsregister per contour.

    #### Berekenmethode

    **Placeholder 0.**
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'perceel_eigendom_overheid'
    _lden[_KOL] = 0.0
    _lnight[_KOL] = 0.0
    _kolommen_na_stap = toon_stap(f'9 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 10 — `woning_eigendom_overheid`

    #### Beschrijving

    Aandeel woningen in **overheidsbezit** per band.

    #### Bron

    Nog geen eigendomsregister per contour.

    #### Berekenmethode

    **Placeholder 0.**
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'woning_eigendom_overheid'
    _lden[_KOL] = 0.0
    _lnight[_KOL] = 0.0
    _kolommen_na_stap = toon_stap(f'10 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 11 — `vergunde_wooneenheden_nieuwbouw`

    #### Beschrijving

    Aantal **vergunde wooneenheden nieuwbouw** per geluidsband (teller o.a. verbod kleine woning).

    #### Bron

    - `data/vergunningen_omgevingsloket_2026_lang.csv`
    - `data/vergunningen_kwetsbare_functies_2026_lang.csv`
    - `data/vergunningen_verkaveling_2026_lang.csv`
    - `data/population 2024 par bout de secteur stat.xlsx` — gemeente → contour conversie

    #### Berekenmethode

    1. Vergunningen per gemeente combineren en naar contour verdelen (`verdeel_gemeente_naar_contour`, jaar = `JAAR_TELLERS`).
    2. Filter: `handeling == "Nieuwbouw"` en `metriek == "Aantal wooneenheden"`.
    3. Som per `db_ondergrens`.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, JAAR_TELLERS, combineer_vergunningen_lang, conversietabel_gemeente_naar_db, koppel_conversie_aan_contourband, lees_sector_contour_beide, lees_vergunningen, pd, toon_stap, verdeel_gemeente_naar_contour):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'vergunde_wooneenheden_nieuwbouw'
    sector_lden, _ = lees_sector_contour_beide()
    # Eenmalige voorbereiding vergunningen → contour (hergebruikt in stappen 12–14)
    conversie_lden = conversietabel_gemeente_naar_db(sector_lden, indicator='lden')
    conversie_lden_band = koppel_conversie_aan_contourband(conversie_lden, _lden)
    verg_omg, verg_kwets, verg_verk = lees_vergunningen()
    verg_combined = combineer_vergunningen_lang(verg_omg.assign(bron='omgevingsloket'), verg_kwets.assign(bron='kwetsbare_functies'), verg_verk.assign(bron='verkaveling'))
    verg_contour, _verg_niet = verdeel_gemeente_naar_contour(verg_combined, conversie_lden_band, jaartal=JAAR_TELLERS)
    _idx = _lden.index
    df_verg = verg_contour[verg_contour['jaar_indiening'].astype(str) == str(JAAR_TELLERS)].copy()

    def som_per_band(mask):
        subset = df_verg.loc[mask]
        if subset.empty:
            return pd.Series(0.0, index=_idx)
        return subset.groupby('db_ondergrens')['waarde'].sum().reindex(_idx).fillna(0)
    _nieuwbouw_we = som_per_band((df_verg['handeling'] == 'Nieuwbouw') & (df_verg['metriek'] == 'Aantal wooneenheden'))
    _lden[_KOL] = _nieuwbouw_we
    _lnight[_KOL] = _nieuwbouw_we
    _kolommen_na_stap = toon_stap(f'11 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()  # zelfde bron; vergunningen niet Lnight-specifiek


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 12 — `gem_wooneenheden_per_vergunning`

    #### Beschrijving

    Gemiddeld aantal wooneenheden per vergunningsaanvraag (nationaal cijfer, geen splitsing per contour).

    #### Bron

    - `data/vergunningen_omgevingsloket_2026_lang.csv` — `Aantal projecten` en `Aantal wooneenheden`

    #### Berekenmethode

    `gem = som(wooneenheden) / som(projecten)` over omgevingsloket, jaar `JAAR_TELLERS`. Zelfde constante in elke band (lden en lnight).
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, df_verg, pd, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'gem_wooneenheden_per_vergunning'
    omg = df_verg[df_verg['bron'] == 'omgevingsloket']
    _aantal_projecten = omg.loc[omg['metriek'] == 'Aantal projecten', 'waarde'].sum()
    _aantal_wooneenheden = omg.loc[omg['metriek'] == 'Aantal wooneenheden', 'waarde'].sum()
    _gem_we = float(_aantal_wooneenheden / _aantal_projecten) if _aantal_projecten > 0 else 0.0
    _lden[_KOL] = _gem_we
    _lnight[_KOL] = _gem_we
    _kolommen_na_stap = toon_stap(f'12 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    pd.DataFrame({_KOL: [_lden[_KOL].iloc[0]]})
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 13 — `vergunningen_kwetsbare_groep`

    #### Beschrijving

    Aantal vergunningen / projecten voor **kwetsbare functies** per contourband.

    #### Bron

    - `data/vergunningen_kwetsbare_functies_2026_lang.csv` (via `df_verg`, bron = `kwetsbare_functies`)

    #### Berekenmethode

    Som `waarde` per `db_ondergrens` waar `bron == "kwetsbare_functies"`, jaar `JAAR_TELLERS`.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, df_verg, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'vergunningen_kwetsbare_groep'
    _kwetsbaar = som_per_band(df_verg['bron'] == 'kwetsbare_functies')
    _lden[_KOL] = _kwetsbaar
    _lnight[_KOL] = _kwetsbaar
    _kolommen_na_stap = toon_stap(f'13 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 14 — `renovatie_totaal`

    #### Beschrijving

    Totaal aantal vergunningen **verbouwen of hergebruik** per band (renovatie-teller).

    #### Bron

    - Vergunningsbestanden (omgevingsloket e.a.) via `df_verg`

    #### Berekenmethode

    Filter `handeling == "Verbouwen of hergebruik"`, som `waarde` per `db_ondergrens`.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, df_verg, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'renovatie_totaal'
    _renovatie = som_per_band(df_verg['handeling'] == 'Verbouwen of hergebruik')
    _lden[_KOL] = _renovatie
    _lnight[_KOL] = _renovatie
    _kolommen_na_stap = toon_stap(f'14 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 15 — `alle_transacties_percelen`

    #### Beschrijving

    Totaal aantal **perceeltransacties** per geluidsband (industrie/onbebouwd segmenten).

    #### Bron

    - `data/transacties_vastgoed/transacties_industrie_terrein.csv`
    - `data/transacties_vastgoed/transacties_industrie_bebouwd.csv`
    - `data/capakey_contour_lden.csv` — koppeling CaPaKey → `db_ondergrens`

    #### Berekenmethode

    1. Transacties laden; `sum_ParcelsNumber` numeriek.
    2. Koppelen aan contour via capakey-mapping (`bereken_prijzen_uit_transacties` levert ook `capakey_mapping`).
    3. Segmenten `industrie_terrein` + `industrie_bebouwd`: som per band.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, bereken_prijzen_uit_transacties, brussel_lden, pd, toon_stap, transacties_1):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'alle_transacties_percelen'
    _, capakey_mapping, prijzen_contour = bereken_prijzen_uit_transacties(transacties_1, brussel_lden, _lden)
    _idx = _lden.index
    tx = transacties_1.copy()
    tx['sum_ParcelsNumber'] = pd.to_numeric(tx['sum_ParcelsNumber'], errors='coerce').fillna(0)
    gekoppeld = tx.merge(capakey_mapping[['capakey', 'db_ondergrens']], on='capakey', how='inner')

    def agg_transacties(segmenten):
        subset = gekoppeld[gekoppeld['segment'].isin(segmenten)]
        if subset.empty:
            return pd.Series(0.0, index=_idx)
        return subset.groupby('db_ondergrens')['sum_ParcelsNumber'].sum().reindex(_idx).fillna(0)
    tx_percelen = agg_transacties(['industrie_terrein', 'industrie_bebouwd'])
    _lden[_KOL] = tx_percelen
    _lnight[_KOL] = tx_percelen
    _kolommen_na_stap = toon_stap(f'15 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 16 — `alle_verkopen_onbebouwde_bebouwbare_percelen`

    #### Beschrijving

    Teller **verkopen van onbebouwde bebouwbare percelen** per band (o.a. voorkooprecht percelen).

    #### Bron

    Zelfde transactiebestanden als stap 15.

    #### Berekenmethode

    **Beleidsaanname:** geen aparte filter op bebouwbare vs. andere percelen in de transactiedata → voorlopig **gelijk aan** `alle_transacties_percelen` (stap 15).
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'alle_verkopen_onbebouwde_bebouwbare_percelen'
    _lden[_KOL] = tx_percelen
    _lnight[_KOL] = tx_percelen
    _kolommen_na_stap = toon_stap(f'16 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 17 — `alle_transacties_woningen`

    #### Beschrijving

    Totaal aantal **woningtransacties** per band.

    #### Bron

    - `data/transacties_vastgoed/transacties_woningen.csv`
    - `data/transacties_vastgoed/transacties_appartementen.csv`
    - CaPaKey → contour mapping

    #### Berekenmethode

    Segmenten `woningen` + `appartementen`: som `sum_ParcelsNumber` per `db_ondergrens`.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'alle_transacties_woningen'
    tx_woningen = agg_transacties(['woningen', 'appartementen'])
    _lden[_KOL] = tx_woningen
    _lnight[_KOL] = tx_woningen
    _kolommen_na_stap = toon_stap(f'17 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 18 — `alle_verkopen_woningen`

    #### Beschrijving

    Teller **woningverkopen** per band (o.a. voorkooprecht woningen).

    #### Bron

    Zelfde als stap 17.

    #### Berekenmethode

    **Beleidsaanname:** geen publiek/privé-split in data → voorlopig **gelijk aan** `alle_transacties_woningen`.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'alle_verkopen_woningen'
    _lden[_KOL] = tx_woningen
    _lnight[_KOL] = tx_woningen
    _kolommen_na_stap = toon_stap(f'18 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 19 — `prijs_onbebouwde_bebouwbare_percelen`

    #### Beschrijving

    Gewogen gemiddelde **transactieprijs per onbebouwd bebouwbare perceel** per band (€).

    #### Bron

    - Vastgoedtransacties industrie/onbebouwd (`contour/prices.py` → `prijzen_contour`)
    - Brusselse sectorverdeling voor gewichten

    #### Berekenmethode

    Mediaan/gewogen prijs per `db_ondergrens` uit `bereken_prijzen_uit_transacties` (segmenten industrie_terrein + industrie_bebouwd).
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, prijzen_contour, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'prijs_onbebouwde_bebouwbare_percelen'
    _idx = _lden.index
    prijzen_idx = prijzen_contour.set_index('db_ondergrens')
    _lden[_KOL] = prijzen_idx[_KOL].reindex(_idx)
    _lnight[_KOL] = prijzen_idx[_KOL].reindex(_idx)
    _kolommen_na_stap = toon_stap(f'19 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 20 — `prijs_onbebouwde_onbebouwbare_percelen`

    #### Beschrijving

    Eenheidsprijs **onbebouwd onbebouwbaar perceel** per band (€).

    #### Bron

    - `transacties_industrie_terrein.csv` (primair segment)

    #### Berekenmethode

    Gewogen gemiddelde prijs per band uit `prijzen_contour`.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'prijs_onbebouwde_onbebouwbare_percelen'
    _lden[_KOL] = prijzen_idx[_KOL].reindex(_lden.index)
    _lnight[_KOL] = prijzen_idx[_KOL].reindex(_lnight.index)
    _kolommen_na_stap = toon_stap(f'20 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 21 — `prijs_bewoonde_niet_geïsoleerde_woning`

    #### Beschrijving

    Eenheidsprijs **bewoonde niet-geïsoleerde woning** per band (€).

    #### Bron

    - `transacties_woningen.csv` + `transacties_appartementen.csv`

    #### Berekenmethode

    Gewogen gemiddelde transactieprijs woningen/appartementen per `db_ondergrens`.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'prijs_bewoonde_niet_geïsoleerde_woning'
    _lden[_KOL] = prijzen_idx[_KOL].reindex(_lden.index)
    _lnight[_KOL] = prijzen_idx[_KOL].reindex(_lnight.index)
    _kolommen_na_stap = toon_stap(f'21 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 22 — `prijs_bewoonde_geïsoleerde_woning`

    #### Beschrijving

    Eenheidsprijs **bewoonde geïsoleerde woning** per band (€).

    #### Bron

    Zelfde woningtransacties als stap 21.

    #### Berekenmethode

    **Beleidsaanname:** geen isolatie-split in transactiedata → zelfde prijs als niet-geïsoleerde woning.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'prijs_bewoonde_geïsoleerde_woning'
    _lden[_KOL] = prijzen_idx[_KOL].reindex(_lden.index)
    _lnight[_KOL] = prijzen_idx[_KOL].reindex(_lnight.index)
    _kolommen_na_stap = toon_stap(f'22 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 23 — `R+`

    #### Beschrijving

    Teller renovaties **met** akoestische maatregel (R+), baseline renovatiestroom.

    #### Bron

    Nog niet afgeleid uit vergunningen of andere bron (geen isolatie-split in renovatiedata).

    #### Berekenmethode

    **Placeholder 0** tot renovatiemodel gekoppeld is.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'R+'
    _lden[_KOL] = 0.0
    _lnight[_KOL] = 0.0
    _kolommen_na_stap = toon_stap(f'23 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 24 — `R−`

    #### Beschrijving

    Teller renovaties **zonder** akoestische maatregel (R−).

    #### Bron

    Nog niet beschikbaar per contour.

    #### Berekenmethode

    **Placeholder 0.**
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'R−'
    _lden[_KOL] = 0.0
    _lnight[_KOL] = 0.0
    _kolommen_na_stap = toon_stap(f'24 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 25 — `nieuwbouw_geïsoleerd`

    #### Beschrijving

    Jaarlijkse stroom nieuwbouw die **wel** aan isolatienorm voldoet.

    #### Bron

    Nog niet gemodelleerd.

    #### Berekenmethode

    **Placeholder 0.**
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'nieuwbouw_geïsoleerd'
    _lden[_KOL] = 0.0
    _lnight[_KOL] = 0.0
    _kolommen_na_stap = toon_stap(f'25 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 26 — `nieuwbouw_niet_geïsoleerd`

    #### Beschrijving

    Jaarlijkse stroom nieuwbouw **zonder** isolatienorm.

    #### Bron

    Nog niet gemodelleerd.

    #### Berekenmethode

    **Placeholder 0.**
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'nieuwbouw_niet_geïsoleerd'
    _lden[_KOL] = 0.0
    _lnight[_KOL] = 0.0
    _kolommen_na_stap = toon_stap(f'26 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 27 — `potentieel_isoleerbare_woningen`

    #### Beschrijving

    Woningen die akoestisch isoleerbaar zijn via **geluidsbuffers** (stock/teller aanleg buffers).

    #### Bron

    Ruimtelijk bufferpotentieel nog niet berekend in pipeline.

    #### Berekenmethode

    **Placeholder 0.**
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    _KOL = 'potentieel_isoleerbare_woningen'
    _lden[_KOL] = 0.0
    _lnight[_KOL] = 0.0
    _kolommen_na_stap = toon_stap(f'27 {_KOL}', _lden, _lnight, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    _lden[[_KOL]].head()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 28 — FLOW-volgorde en schema-check

    #### Beschrijving

    Alle 27 variabelen zijn ingevuld. Kolommen worden geordend volgens FLOW §2.0 en gevalideerd.

    #### Bron

    Interne schema-definitie (`contour/schema.py` → `FLOW_KOLOMMEN`).

    #### Berekenmethode

    Herschikken zonder waarden te wijzigen; `assert_flow_schema` controleert kolommen en index.
    """)
    return


@app.cell
def _(lden_b2, lnight_b2, set_lden_b2, set_lnight_b2, set_vorige_kolommen, vorige_kolommen, assert_flow_schema, toon_stap):
    if lden_b2 is None or lnight_b2 is None:
        raise RuntimeError('Voer eerst stap 0 (index) uit.')
    _lden = lden_b2
    _lnight = lnight_b2
    from contour.schema import FLOW_KOLOMMEN
    lden_1 = _lden[list(FLOW_KOLOMMEN)]
    lnight_1 = _lnight[list(FLOW_KOLOMMEN)]
    _kolommen_na_stap = toon_stap('28 FLOW-volgorde', lden_1, lnight_1, vorige_kolommen)
    set_lden_b2(_lden)
    set_lnight_b2(_lnight)
    set_vorige_kolommen(_kolommen_na_stap)
    assert_flow_schema(lden_1)
    assert_flow_schema(lnight_1)
    list(lden_1.columns)
    return (lden_1, lnight_1)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Stap 29 — Eindresultaat Deel B2
    """)
    return


@app.cell
def _(lden_1, lnight_1):
    lden_handmatig_1, _lnight_handmatig = (lden_1.copy(), lnight_1.copy())
    print(f'lden: {lden_handmatig_1.shape}, lnight: {_lnight_handmatig.shape}')
    lden_handmatig_1.head(3)
    return (lden_handmatig_1,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Deel C - Geconsolideerde master-tabellen -> parquet

    Voer **eerst Deel B2** uit (stappen 0–29) om elke tussenstap te zien. De cel hieronder roept daarna de volledige pipeline aan (schrijft parquet + zelfde resultaat als stap8).

    #### Kolomoverzicht (`tables` na `run_data_pipeline()`)

    **`contour_lden` / `contour_lnight`** — volledige kolomlijst (lden = onderstaand; lnight idem structuur):

    | Kolom | Beschrijving |
    |-------|----------------|
    | `geluidscontour` | Bandlabel (bv. `45-46`) |
    | `db_ondergrens` | Ondergrens dB-band |
    | `db_bovengrens` | Bovengrens dB-band |
    | `inwoners` | Totaal inwoners Vlaanderen + Brussel in band |
    | `aantal_woningen` | Woningen Vlaanderen (bron Excel) |
    | `aantal bebouwbare percelen die werden gecreëerd door woongebieden aan te duiden` | Flow-teller woongebied-aanduiding, cumulatief 5 jr (Vlaanderen) |
    | `aantal niet-bebouwbarepercelen die worden gecreëerd door woongebied te schrappen` | Woongebied-schrapping (Vlaanderen) |
    | `gemiddeld_aantal_inwoners_per_huis` | Vlaanderen: `inwoners` / `aantal_woningen` |
    | `inwoners_brussel` | Brussel: som sectoren per `db_ondergrens` |
    | `inwoners_vlaanderen` | Kopie Vlaanderen-`inwoners` vóór merge |
    | `aantal_woningen_vlaanderen` | Gelijk aan Excel `aantal_woningen` |
    | `aantal_woningen_brussel` | Geschat: `inwoners_brussel` / gem. inw./woning |
    | `aantal_woningen_totaal` | Som Vlaanderen + Brussel |
    | `db_midden` | Middelpunt band: (`db_ondergrens` + `db_bovengrens`) / 2 |
    | `dosis_effect_relatie` | % ernstig gehinderden (lookup lden/lnight) |
    | `aantal_ernstig_gehinderden_vlaanderen_2026` | Ernstig gehinderden (vlaanderen): inwoners x dosis-effect / 100 |
    | `aantal_ernstig_gehinderden_brussel_2026` | Ernstig gehinderden (brussel): inwoners x dosis-effect / 100 |
    | `aantal_ernstig_gehinderden_totaal_2026` | Ernstig gehinderden (totaal): inwoners x dosis-effect / 100 |
    | `aantal_bewoonde_geïsoleerde_huizen_vlaanderen_2026` | Placeholder 20% woningen (vlaanderen) |
    | `aantal_bewoonde_geïsoleerde_huizen_brussel_2026` | Placeholder 20% woningen (brussel) |
    | `aantal_bewoonde_geïsoleerde_huizen_totaal_2026` | Placeholder 20% woningen (totaal) |
    | `aantal_bewoonde_niet_geïsoleerde_huizen_vlaanderen_2026` | Placeholder 20% woningen (vlaanderen) |
    | `aantal_bewoonde_niet_geïsoleerde_huizen_brussel_2026` | Placeholder 20% woningen (brussel) |
    | `aantal_bewoonde_niet_geïsoleerde_huizen_totaal_2026` | Placeholder 20% woningen (totaal) |
    | `aantal_onbebouwde_bebouwbare_percelen_*_2026` | Placeholder **0** (stock; niet = woongebied-flow-kolom) |
    | `aantal_onbebouwde_onbebouwbare_percelen_*_2026` | Placeholder **0** (idem) |
    | `aantal_perceel_eigendom_overheid_vlaanderen_2026` | Startwaarde 0 (nog geen bron) |
    | `aantal_perceel_eigendom_overheid_brussel_2026` | Startwaarde 0 (nog geen bron) |
    | `aantal_perceel_eigendom_overheid_totaal_2026` | Startwaarde 0 (nog geen bron) |
    | `aantal_woning_eigendom_overheid_vlaanderen_2026` | Startwaarde 0 (nog geen bron) |
    | `aantal_woning_eigendom_overheid_brussel_2026` | Startwaarde 0 (nog geen bron) |
    | `aantal_woning_eigendom_overheid_totaal_2026` | Startwaarde 0 (nog geen bron) |
    | `prijs_onbebouwde_bebouwbare_percelen` | €/eenheid uit transacties industrie |
    | `prijs_onbebouwde_onbebouwbare_percelen` | €/eenheid uit transacties industrie-terrein |
    | `prijs_bewoonde_niet_geïsoleerde_woning` | €/woning uit woningen + appartementen |
    | `prijs_bewoonde_geïsoleerde_woning` | Idem (zelfde transactiebron) |

    **Overige parquet-bestanden:**

    | Sleutel | Belangrijkste kolommen |
    |---------|------------------------|
    | `conversie_gemeente_db` | `gemeente`, `db`, `aandeel`, `indicator` |
    | `vergunningen_gemeente` | gemeente x handeling x metriek |
    | `vergunningen_contour` | vergunningen per `geluidscontour` |
    | `vergunningen_niet_toewijsbaar` | gemeenten zonder match |
    | `transacties_capakey` | ruwe transacties + `segment` |
    | `capakey_prijzen` | prijs per capakey |
    | `capakey_contour_mapping` | capakey -> contour |
    | `prijs_dekking` | dekkingsstatistiek prijsberekening |
    """)
    return


@app.cell
def _():
    from contour.pipeline import run_data_pipeline
    tables = run_data_pipeline()
    lden_2 = tables['lden']
    lnight_2 = tables['lnight']
    contour_lden = lden_2
    contour_lden = tables['contour_lden']  # alias
    contour_lnight = tables['contour_lnight']
    contour_lden.describe()
    return contour_lden, tables


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Overzicht berekende stocks en flows

    Na **Deel C** (`run_data_pipeline()`) staan de stocks en KPI's in `contour_lden` / `contour_lnight` (parquet in `output/intermediate/`). De **flow rates** worden berekend in [`contour_flows.ipynb`](contour_flows.ipynb) (`run_flows_pipeline()` -> `flow_rates.parquet` + `input/flow_rules.csv`). Referentie: [STOCKS_EN_FLOWS_BEREKENEN.md](../STOCKS_EN_FLOWS_BEREKENEN.md).

    ### Stocks en KPI-kolommen (`contour_lden` / `contour_lnight`)

    | Kolom (patroon) | Simulator-stock | Bron / berekening | Status |
    |-----------------|-----------------|-------------------|--------|
    | `geluidscontour`, `db_ondergrens`, `db_bovengrens` | - | `contour_vlaanderen_stocks.xlsx` | Geladen |
    | `inwoners`, `aantal_woningen` | - | Excel (Vlaanderen, buiten Brussel) | Geladen |
    | Woongebied-kolommen (2x, volledige Excel-naam) | - | Excel: cumulatief effect aanwijzing/schrapping | Geladen |
    | `inwoners_brussel`, `inwoners_vlaanderen`, `inwoners` | - | Brussel-sector + som | Berekend |
    | `gemiddeld_aantal_inwoners_per_huis` | - | `inwoners` / `aantal_woningen` (Vlaanderen) | Berekend |
    | `aantal_woningen_vlaanderen`, `_brussel`, `_totaal` | - | Inwoners per regio / gemiddelde bezetting | Berekend |
    | `db_midden`, `dosis_effect_relatie` | - | Midden band; lookup-tabel lden/lnight | Berekend |
    | `aantal_ernstig_gehinderden_{vlaanderen,brussel,totaal}_2026` | - | `inwoners` x dosis-effect / 100 | Berekend |
    | `aantal_bewoonde_geïsoleerde_huizen_{vlaanderen,brussel,totaal}_2026` | `bewoonde_geïsoleerde_woning` | Placeholder: 20% van woningen per regio | Placeholder |
    | `aantal_bewoonde_niet_geïsoleerde_huizen_*_2026` | `bewoonde_niet_geïsoleerde_woning` | Placeholder: 80% van woningen per regio | Placeholder |
    | `aantal_onbebouwde_bebouwbare_percelen_*_2026` | `onbebouwde_bebouwbare_percelen` | Placeholder **0** | Placeholder **0** |
    | `aantal_onbebouwde_onbebouwbare_percelen_*_2026` | `onbebouwde_onbebouwbare_percelen` | Placeholder **0** | Placeholder **0** |
    | `aantal_perceel_eigendom_overheid_*_2026` | `perceel_eigendom_overheid` | Start 0 | Placeholder |
    | `aantal_woning_eigendom_overheid_*_2026` | `woning_eigendom_overheid` | Start 0 | Placeholder |
    | `prijs_onbebouwde_bebouwbare_percelen`, `prijs_onbebouwde_onbebouwbare_percelen` | - | Transactieprijs per contour | Berekend |
    | `prijs_bewoonde_niet_geïsoleerde_woning`, `prijs_bewoonde_geïsoleerde_woning` | - | Idem (woningen + appartementen) | Berekend |
    | `nieuwe_woning` | `nieuwe_woning` | Alleen in `stocks_contour`: start 0 | Vast |

    *Tussenproducten in parquet:* `vergunningen_contour`, `vergunningen_gemeente`, `transacties_capakey`, `capakey_prijzen`, `conversie_gemeente_db`.

    ### Flow rates (`measure_id` -> `input/flow_rules.csv`)

    Formule: `flow_rate = teller / noemer` (landelijk geaggregeerd, tenzij anders vermeld).

    | `measure_id` | Teller (indicatief) | Noemer (stock) | Baseline | Active | Status |
    |--------------|---------------------|----------------|----------|--------|--------|
    | `verkavelingsverbod` | - | `onbebouwde_bebouwbare_percelen` | 0 | 0 | Geen hinder-effect |
    | `woongebiedverbod` | Woongebied-aanduiding / 5 | `onbebouwde_onbebouwbare_percelen` | berekend | = baseline | OK |
    | `aankoopbeleid_percelen` | 25% x transacties percelen | `onbebouwde_bebouwbare_percelen` | 0 | berekend | Deels |
    | `voorkooprecht_percelen` | Transacties percelen | `onbebouwde_bebouwbare_percelen` | 0 | berekend | Deels |
    | `onteigening_percelen` | Vast 5% | `onbebouwde_bebouwbare_percelen` | 0 | 0,05 | OK |
    | `verbod_kleine_woning` | Vergunde wooneenheden nieuwbouw | `onbebouwde_bebouwbare_percelen` | berekend | = baseline | Deels |
    | `verbod_grote_woning` | - | `onbebouwde_bebouwbare_percelen` | 0,01 | 0 | Beleidskeuze |
    | `verbod_kwetsbare_groep` | Vergunningen kwetsbare groep | `onbebouwde_bebouwbare_percelen` | berekend | = baseline | Deels |
    | `woonverdichtingsverbod_niet_geïsoleerde_woningen` | - | `bewoonde_niet_geïsoleerde_woning` | 0,01 | 0 | Beleidskeuze |
    | `woonverdichtingsverbod_geïsoleerde_woningen` | - | `bewoonde_geïsoleerde_woning` | 0,01 | 0 | Beleidskeuze |
    | `aankoopbeleid_niet_geïsoleerde_woningen` | 25% x transacties woningen | `bewoonde_niet_geïsoleerde_woning` | 0 | berekend | Deels |
    | `aankoopbeleid_geïsoleerde_woningen` | 25% x transacties woningen | `bewoonde_geïsoleerde_woning` | 0 | berekend | Deels |
    | `voorkooprecht_niet_geïsoleerde_woningen` | Transacties woningen | `bewoonde_niet_geïsoleerde_woning` | 0 | berekend | Deels |
    | `voorkooprecht_geïsoleerde_woningen` | Transacties woningen | `bewoonde_geïsoleerde_woning` | 0 | berekend | Deels |
    | `onteigening_niet_geïsoleerde_woningen` | Vast 5% | `bewoonde_niet_geïsoleerde_woning` | 0 | 0,05 | OK |
    | `onteigening_geïsoleerde_woningen` | Vast 5% | `bewoonde_geïsoleerde_woning` | 0 | 0,05 | OK |
    | `isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning` | - | dynamisch `nieuwe_woning` | 0,5 | 0 | Deels |
    | `isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning` | - | dynamisch `nieuwe_woning` | 1 | 1 | Deels |
    | `renovatie_zonder_maatregel` | 50% renovatievergunningen | `bewoonde_niet_geïsoleerde_woning` | berekend | 0 | Deels |
    | `verplicht_isoleren_renovatie` | Renovatie totaal | `bewoonde_niet_geïsoleerde_woning` | 0 | berekend | Deels |
    | `gesubsidieerd_isolatieprogramma` | 2x renovatie | `bewoonde_niet_geïsoleerde_woning` | 0 | berekend | Deels |
    | `gestuurd_isolatieprogramma` | 4x renovatie | `bewoonde_niet_geïsoleerde_woning` | 0 | berekend | Deels |
    | `aanleg_geluidsbuffers` | - | - | 0 | 0 | Placeholder |
    | `compensatie_buitenzone` | - | - | 0 | 0 | Nog niet gekoppeld |
    | `compensatie_verhuis` | - | - | 0 | 0 | Nog niet gekoppeld |
    | `versterken_sociale_cohesie` | - | - | 0 | 0 | Nog niet gekoppeld |
    | `vergroenen_leefomgeving` | - | - | 0 | 0 | Nog niet gekoppeld |

    **Legende:** *Geladen* = bronbestand; *Berekend* = afgeleid in `contour/`; *Placeholder* = voorlopige aannames; *Deels* = geen volledige contour-split; *OK* = formule toegepast met beschikbare data.
    """)
    return


@app.cell
def _(contour_lden, tables):
    # Prijsdekking en voorbeeldprijzen (na run_data_pipeline)
    prijs_kolommen = [
        "geluidscontour",
        "prijs_onbebouwde_bebouwbare_percelen",
        "prijs_onbebouwde_onbebouwbare_percelen",
        "prijs_bewoonde_niet_geïsoleerde_woning",
        "prijs_bewoonde_geïsoleerde_woning",
    ]

    if "tables" not in globals():
        raise NameError(
            "Voer eerst de cel hierboven uit (run_data_pipeline) voordat je prijsdekking bekijkt."
        )

    tables["prijs_dekking"]
    contour_lden[prijs_kolommen].head(10)
    return


@app.cell
def _(contour_lden):
    contour_lden
    return


@app.cell
def _():
    KOLommen = {
        'geluidscontour': 'Geluidsband',
        'inwoners_totaal': 'Inwoners Vlaanderen+Brussel',
        'aantal_woningen_totaal': 'Woningen totaal',
        'dosis_effect_relatie': 'Dosis-effect (% ernstig gehinderd)',
        'aantal_onbebouwde_bebouwbare_percelen_totaal_2026': 'Stock onbeb. bebouwbare percelen (placeholder)',
    }
    KOLommen
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Checklist variabelen (FLOW §2)

    1. `onbebouwde_bebouwbare_percelen`
    2. `onbebouwde_onbebouwbare_percelen`
    3. `bewoonde_niet_geïsoleerde_woning`
    4. `bewoonde_geïsoleerde_woning`
    5. Gemiddeld aantal wooneenheden per vergunningsaanvraag
    6. Aantal toegekende vergunningen voor kleine woningen
    7. Aantal toegekende vergunningen voor grote woningen
    8. Aantal toegekende vergunningen voor kwetsbare groepen
    9. Aantal toegekende vergunningen voor opsplitsen woningen
    10. Aantal niet-geïsoleerde woningen jaarlijks vergund
    11. Aantal geïsoleerde woningen jaarlijks vergund
    12. Aantal jaarlijkse vergunningen renovatie met isolatie
    13. Aantal jaarlijkse vergunningen renovatie zonder isolatie
    14. Aantal publieke verkopen van percelen
    15. Aantal prive en publieke verkopen van percelen
    16. Aantal publieke verkopen van woningen
    17. Aantal prive en publieke verkopen van woningen
    18. Aantal bebouwbare percelen woongebied-aanduiding (laatste 5 jaar)
    19. Woningen akoestisch isoleerbaar via geluidsbuffers
    20. Aantal inwoners per contour en per sector

    (Zie **Deel E** hieronder voor de uitgewerkte tabel Vlaanderen/Brussel.)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Deel E — Variabelenlijst: berekening per regio (Vlaanderen vs Brussel)

    Onderstaande tabel volgt de checklist uit FLOW §2. Per variabele: wat we **nu** doen voor Vlaanderen en Brussel, en de status.

    | # | Variabele | Vlaanderen | Brussel | Status |
    |---|-----------|------------|---------|--------|
    | 1 | `onbebouwde_bebouwbare_percelen` | Placeholder **0** (stock ontbreekt) | Placeholder **0** | Placeholder |
    | 2 | `onbebouwde_onbebouwbare_percelen` | Placeholder **0** (stock ontbreekt) | Placeholder **0** | Placeholder |
    | 3 | `bewoonde_niet_geïsoleerde_woning` | `0.8 * aantal_woningen_vlaanderen` | `0.8 * aantal_woningen_brussel` (woningen geschat uit inwoners) | Placeholder |
    | 4 | `bewoonde_geïsoleerde_woning` | `0.2 * aantal_woningen_vlaanderen` | `0.2 * aantal_woningen_brussel` | Placeholder |
    | 5 | Gem. wooneenheden per vergunningsaanvraag | `Aantal wooneenheden / Aantal projecten` per Vlaamse gemeente (omgevingsloket) | Geen data in huidige vergunningen-CSV (enkel Vlaamse gemeenten) | Deels |
    | 6 | Vergunningen kleine woningen | Niet identificeerbaar (geen MER/schaal-split) | — | Niet beschikbaar |
    | 7 | Vergunningen grote woningen | Niet identificeerbaar; `verbod_grote_woning` active=0 | — | Beleidskeuze |
    | 8 | Vergunningen kwetsbare groepen | `vergunningen_kwetsbare_functies_2026_lang.csv`, per gemeente | Geen | Deels |
    | 9 | Vergunningen opsplitsen woningen | Niet in omgevingsloket-data | — | Niet beschikbaar |
    | 10 | Niet-geïsoleerde woningen jaarlijks vergund | Geen iso-split; indirect via totaal nieuwbouw | — | Deels |
    | 11 | Geïsoleerde woningen jaarlijks vergund | Zelfde; aannames in flow (`isolatievoorschriften_*`) | — | Deels |
    | 12 | Renovatie met isolatie | `Verbouwen of hergebruik` niet gesplitst op isolatie | — | Deels |
    | 13 | Renovatie zonder isolatie | Idem; in flows: 50/50 split van totaal renovatie | — | Deels |
    | 14 | Publieke verkopen percelen | 50% van transacties `industrie_terrein` (aannname) | Zelfde, via NIS-filter Brussel | Deels |
    | 15 | Privé + publieke verkopen percelen | Som `sum_ParcelsNumber` industrie_terrein; landelijk, geen contour | Idem | Deels |
    | 16 | Publieke verkopen woningen | 50% van woningen+appartementen (aannname) | NIS-filter Brussel | Deels |
    | 17 | Privé + publieke verkopen woningen | Som transacties woningen+appartementen; landelijk | Idem | Deels |
    | 18 | Woongebied-aanduiding (5 jaar) | Excel-kolom ongewijzigd per contour | Geen: **0** | OK (Vlaanderen) |
    | 19 | Woningen akoestisch isoleerbaar (geluidsbuffers) | Nog niet gekoppeld (`aanleg_geluidsbuffers` rate=0) | Idem | Niet berekend |
    | 20 | Inwoners per contour en sector | Contour: `inwoners_vlaanderen` + `inwoners_brussel` | Sector: ruwe `raw_brussel_lden` (1033 sectoren) | OK / deels |

    Zie de codecel hieronder voor een **samenvattende dataframe** en voorbeeldwaarden uit de tussenstappen.
    """)
    return


@app.cell
def _(
    contour_lden,
    display,
    hernoem_brussel_kolommen,
    lden_handmatig_1,
    pd,
    raw_brussel_lden,
    stap5,
    tx_overzicht,
    verg_combined,
):
    JAAR = 2026

    def _col(df, basis):
        return {'vlaanderen': df.get(f'{basis}_vlaanderen_{JAAR}'), 'brussel': df.get(f'{basis}_brussel_{JAAR}'), 'totaal': df.get(f'{basis}_totaal_{JAAR}')}
    bron = lden_handmatig_1 if 'lden_handmatig' in dir() else contour_lden if 'contour_lden' in dir() else stap5
    stocks = pd.DataFrame({'variabele': ['onbebouwde_bebouwbare_percelen', 'onbebouwde_onbebouwbare_percelen', 'bewoonde_niet_geïsoleerde_woning', 'bewoonde_geïsoleerde_woning'], 'vlaanderen_som': [bron[f'aantal_onbebouwde_bebouwbare_percelen_vlaanderen_{JAAR}'].sum(), bron[f'aantal_onbebouwde_onbebouwbare_percelen_vlaanderen_{JAAR}'].sum(), bron[f'aantal_bewoonde_niet_geïsoleerde_huizen_vlaanderen_{JAAR}'].sum(), bron[f'aantal_bewoonde_geïsoleerde_huizen_vlaanderen_{JAAR}'].sum()], 'brussel_som': [bron[f'aantal_onbebouwde_bebouwbare_percelen_brussel_{JAAR}'].sum(), bron[f'aantal_onbebouwde_onbebouwbare_percelen_brussel_{JAAR}'].sum(), bron[f'aantal_bewoonde_niet_geïsoleerde_huizen_brussel_{JAAR}'].sum(), bron[f'aantal_bewoonde_geïsoleerde_huizen_brussel_{JAAR}'].sum()]})
    stocks['totaal_som'] = stocks['vlaanderen_som'] + stocks['brussel_som']
    print('=== Stocks (landelijke som over alle contouren) ===')
    display(stocks)
    if 'verg_combined' in dir():
        vg = verg_combined[verg_combined['jaar_indiening'].astype(str) == '2025']
    # Gebruik handmatige tabel als die bestaat, anders pipeline-output
        nieuwbouw_we = vg[(vg['handeling'] == 'Nieuwbouw') & (vg['metriek'] == 'Aantal wooneenheden')]['waarde'].sum()
        nieuwbouw_pr = vg[(vg['handeling'] == 'Nieuwbouw') & (vg['metriek'] == 'Aantal projecten')]['waarde'].sum()
        renovatie_pr = vg[(vg['handeling'] == 'Verbouwen of hergebruik') & (vg['metriek'] == 'Aantal projecten')]['waarde'].sum()
        kwetsbaar_pr = vg[(vg['bron'] == 'kwetsbare_functies') & (vg['metriek'] == 'Aantal projecten')]['waarde'].sum()
    # --- Stocks uit contour_lden ---
        print('=== Vergunningen 2025 (Vlaanderen, gemeente-niveau) ===')
        display(pd.DataFrame({'indicator': ['nieuwbouw wooneenheden', 'nieuwbouw projecten', 'gem. wooneenheden / project (nieuwbouw)', 'renovatie projecten', 'kwetsbare groep projecten'], 'waarde': [nieuwbouw_we, nieuwbouw_pr, nieuwbouw_we / max(nieuwbouw_pr, 1), renovatie_pr, kwetsbaar_pr], 'brussel': ['geen data'] * 5}))
    if 'tx_overzicht' in dir():
        print('=== Transacties per regio ===')
        display(tx_overzicht.pivot(index='segment', columns='regio', values='sum_ParcelsNumber').fillna(0))
    print('=== Inwoners per contour (Vlaanderen vs Brussel) ===')
    display(bron[['geluidscontour', 'inwoners_vlaanderen', 'inwoners_brussel', 'inwoners']].head(10))
    print('=== Inwoners per sector (Brussel, ruwe bron) ===')
    sector = hernoem_brussel_kolommen(raw_brussel_lden[['dB', 'Population dans le contour', 'T_MUN_NL']])
    sector = sector.rename(columns={'T_MUN_NL': 'gemeente'})
    display(sector.groupby(['gemeente', 'db'], as_index=False)['inwoners'].sum().head(12))
    from contour.columns import KOL_WOONGEBIED_AANDUIDING
    print('=== Woongebied-flow-teller (cumulatief 5 jr, Vlaanderen) ===')
    # --- Vergunningen (Vlaanderen; geen Brussel in bron) ---
    # --- Transacties per regio ---
    # --- Inwoners: contour vs sector ---
    # --- Woongebied (enkel Vlaanderen) ---
    display(bron[['geluidscontour', KOL_WOONGEBIED_AANDUIDING]].head(8))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Deel D — Validatie consolidatie
    """)
    return


@app.cell
def _(tables):
    from contour.pipeline import validatie_consolidatie

    checks = validatie_consolidatie(tables)
    checks
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Let op:** gemeenten zonder match op `T_MUN_NL` (bv. fusiegemeenten) blijven in `vergunningen_niet_toewijsbaar.parquet`. Overige ringgemeenten worden via `population 2024 par bout de secteur stat.xlsx` naar contour verdeeld.
    """)
    return


if __name__ == "__main__":
    app.run()
