# Stocks en flows berekenen

Dit document beschrijft welke **basisdata** nodig is om de **stocks** en **flow rates** van het dashboard te berekenen, en hoe die outputs worden afgeleid. De huidige waarden in `input/flow_rules.csv` zijn **placeholders**; dit document is de referentie voor de berekening in `contour_data.ipynb` / `contour_flows.ipynb` (of `contour.pipeline`) en export naar `input/`.

> **Notatie:** Formules als leesbare tekst, bijv. **r_f** = (0,25 × `teller`) / `noemer`. Vermenigvuldiging: ×. Renovatie-tellers: R⁺ (met isolatie), R⁻ (zonder isolatie). Geen LaTeX — dat rendert niet in de Markdown-preview.

---

## Leeswijzer

| § | Onderwerp | Inhoud |
| - | --------- | ------ |
| [1](#1-inleiding-en-notatie) | Inleiding en notatie | Doel, algemene formules, ruimtelijk niveau |
| [2](#2-basisdata) | Basisdata | Alle invoervariabelen: stocks, tellers, prijzen, bronnen |
| [3](#3-outputs-stocks) | Outputs: stocks | Welke simulatorstocks we nodig hebben en hoe ze uit basisdata komen |
| [4](#4-outputs-flows) | Outputs: flows | Alle flows, formules en koppeling aan basisdata |
| [5](#5-kostenberekening) | Kostenberekening | Eenheidsprijzen en kosten per maatregel |
| [6](#6-workflow) | Workflow | Notebooks, `contour/` package, uitvoeringsvolgorde |
| [7](#7-bronbestanden) | Bronbestanden | Overzicht databestanden in dit project |
| [8](#8-openstaande-definities) | Openstaande definities | Beleidskeuzes en blokkades voor volgende iteratie |

**Leesvolgorde:** eerst §2 (wat we nodig hebben), dan §3–§4 (wat we berekenen en hoe), daarna §5–§8 (kosten, pipeline, bronnen).

---

## 1. Inleiding en notatie

Elke flow is een **jaarlijkse overgang** tussen twee stocks (`inflow_stock` → `outflow_stock`). De simulator past per jaar toe:

`Flow_f = Stock_inflow × r_f`

waarbij **r_f** de **flow rate** is (aandeel van de inflow-stock dat jaarlijks overgaat).

**Algemene vorm:**

**r_f = Teller_f / Noemer_f**

- **Teller:** jaarlijkse activiteit (vergunningen, verkopen, gecreëerde percelen, …)
- **Noemer:** relevante stock op hetzelfde ruimtelijk niveau (contour/zone)

In `input/flow_rules.csv`:

| Kolom | Betekenis |
| ----- | --------- |
| `flow_rate_baseline` | Rate **zonder** maatregel (referentiescenario / achtergronddynamiek) |
| `flow_rate_active` | Rate **met** geactiveerde maatregel |
| `flow_mode` | `transfer` (uit inflow, naar outflow) of `growth` (zelfde stock groeit/krimpt) |

**Ruimtelijk niveau:** stocks in het dashboard zijn per **geluidszone** (A–F), afgeleid van contourrijen (`input/lden_contour.csv`). Omgevingsloket-data zijn per **gemeente** → koppeling via ruimtelijke overlay (gemeente ∩ contour) is nog uit te werken.

**Contour-datastructuur:** `lden` / `lnight` in `contour/consolidate.py` en `output/intermediate/*.parquet` hebben **index** `db_ondergrens` (integer, 30 banden) en **exact 27 kolommen** — geen `geluidscontour`, `db_midden`, regionale stock-suffixen of `dosis_effect_relatie`. Export naar `input/lden_contour.csv` zet `db_ondergrens` als eerste kolom. Zone A–F wordt bij inladen afgeleid uit `db_ondergrens` + `input/lden_zones.csv`.

### Statuslegenda

| Status | Betekenis |
| ------ | --------- |
| ✅ | Beschikbaar, direct bruikbaar |
| 🟡 | Gedeeltelijk beschikbaar of afleidbaar met aannames |
| ❌ | Nog niet in project, externe bron nodig |

---

## 2. Basisdata

Onderstaande tabellen beschrijven **alle invoer** die nodig is om stocks, flow rates en kosten te berekenen. Variabelen zijn gegroepeerd naar rol in de formules.

### 2.1 Stocks (noemers in flow-formules)

Deze variabelen zijn zelf **stocks** in de simulator én dienen als **noemer** in flow-formules.

| Variabele | Beschrijving | Status | Bron / opmerking |
| --------- | ------------ | ------ | ---------------- |
| `onbebouwde_bebouwbare_percelen` | Onbebouwde bebouwbare percelen per contour | 🟡 | `input/lden_contour.csv`; **placeholder 0** — nog geen echte bron |
| `onbebouwde_onbebouwbare_percelen` | Onbebouwde onbebouwbare percelen per contour | 🟡 | Idem; **placeholder 0** |
| `bewoonde_niet_geïsoleerde_woning` | Bewoonde niet-geïsoleerde woningen | ✅ | `input/lden_contour.csv`; placeholder **80%** van woningen per band |
| `bewoonde_geïsoleerde_woning` | Bewoonde geïsoleerde woningen | ✅ | Idem; placeholder **20%** |
| `nieuwe_woning` | Tussenstock nieuwbouw | ✅ | Simulatiestock; start **0**; gevuld door bouwflows |
| `perceel_eigendom_overheid` | Percelen in publiek bezit | ✅ | Start **0**; stijgt via aankoop/voorkoop/onteigening |
| `woning_eigendom_overheid` | Woningen in publiek bezit | ✅ | Start **0**; idem |

### 2.2 Tellers en overige invoer (geen stocks)

| Variabele | Beschrijving | Status | Bron / berekening |
| --------- | ------------ | ------ | ----------------- |
| `bebouwbare_percelen_woongebied(5jr)` | Cumulatief bebouwbare percelen door woongebied-aanduiding (laatste 5 jaar) | ✅ | `data/contour_vlaanderen_stocks.xlsx`; **jaarlijks** = waarde / 5 |
| `niet_bebouwbare_percelen_woongebied_schrapping(5jr)` | Cumulatief door schrapping woongebied (laatste 5 jaar) | ✅ | Zelfde bron; flow-teller, **geen stock** |
| `alle_transacties_percelen` | Totaal perceeltransacties | 🟡 | `data/transacties_vastgoed/` → `sum_ParcelsNumber` (o.a. `industrie_terrein`); annualisatie + CaPaKey→contour nog nodig |
| `alle_verkopen_onbebouwde_bebouwbare_percelen` | Perceelverkopen onbebouwde bebouwbare percelen | 🟡 | Zelfde bron, gefilterd; CaPaKey→contour nog te koppelen |
| `alle_transacties_woningen` | Totaal woningtransacties | 🟡 | `transacties_woningen.csv` + `transacties_appartementen.csv` → `sum_ParcelsNumber` |
| `alle_verkopen_woningen` | Alle woningverkopen | 🟡 | Zelfde bron; **geen iso-split** |
| `vergunde_wooneenheden_nieuwbouw` | Vergunde wooneenheden, handeling `Nieuwbouw` | 🟡 | `data/vergunningen_omgevingsloket_2026_lang.csv` |
| `gem_wooneenheden_per_vergunning` | Gemiddelde wooneenheden per project | 🟡 | `Aantal wooneenheden` / `Aantal projecten` (afgeleid) |
| `vergunningen_kwetsbare_groep` | Vergunningen kwetsbare functies | 🟡 | `data/vergunningen_kwetsbare_functies_2026_lang.csv` → `Aantal projecten` of wooneenheden |
| `renovatie_totaal` | Vergunningen `Verbouwen of hergebruik` | 🟡 | `Aantal projecten` uit omgevingsloket |
| R⁺ | Renovaties **met** isolatie (jaarlijks) | 🟡 | Af te leiden uit `renovatie_totaal`; **nog geen iso-split** in data |
| R⁻ | Renovaties **zonder** isolatie (jaarlijks) | 🟡 | Idem |
| `nieuwbouw_geïsoleerd` | Nieuwbouw geïsoleerd | 🟡 | Af te leiden; geen directe kolom |
| `nieuwbouw_niet_geïsoleerd` | Nieuwbouw niet geïsoleerd | 🟡 | Idem |
| `potentieel_isoleerbare_woningen` | Woningen akoestisch isoleerbaar via geluidsbuffers | ❌ | Nog niet gemodelleerd |
| `inwoners_per_contour` | Inwoners Vlaanderen + Brussel per band | ✅ | `input/lden_contour.csv`; KPI’s, **geen flow-noemer** |

### 2.3 Eenheidsprijzen (voor kostenberekening)

Vier prijskolommen op `input/lden_contour.csv`, per geluidsband. De simulator berekent kosten als:

`rijkost = |Δoutflow| × gewogen_gemiddelde_prijs`

(gewogen met `inwoners_per_contour` per band in de zone; fallback: woningen), vermenigvuldigd met `rel_cost_overheid` / `rel_cost_prive` uit `input/measure_costs.csv`.

| Stock (`kost_stock`) | Prijskolom | Beschrijving | Bron (pipeline) | Status |
| -------------------- | ---------- | ------------ | --------------- | ------ |
| `onbebouwde_bebouwbare_percelen` | `prijs_onbebouwde_bebouwbare_percelen` | € per onbebouwd bebouwbare perceel | `transacties_industrie_terrein.csv` + `transacties_industrie_bebouwd.csv` → CaPaKey → contour | 🟡 |
| `onbebouwde_onbebouwbare_percelen` | `prijs_onbebouwde_onbebouwbare_percelen` | € per onbebouwd onbebouwbaar perceel | `transacties_industrie_terrein.csv` → CaPaKey → contour | 🟡 |
| `bewoonde_niet_geïsoleerde_woning` | `prijs_bewoonde_niet_geïsoleerde_woning` | € per bewoonde niet-geïsoleerde woning | `transacties_woningen.csv` + `transacties_appartementen.csv` | 🟡 |
| `bewoonde_geïsoleerde_woning` | `prijs_bewoonde_geïsoleerde_woning` | € per bewoonde geïsoleerde woning | Zelfde transacties (geen iso-split → zelfde prijs als niet-geïsoleerd) | 🟡 |

`nieuwe_woning`, `perceel_eigendom_overheid` en `woning_eigendom_overheid` hebben **geen** prijskolom; kosten lopen via de **bron-stock** in `kost_stock`.

### 2.4 Detail: transactiedata

Bronmap: `data/transacties_vastgoed/` — zes tab-gescheiden CSV’s met vastgestelde vastgoedtransacties per kadastraal perceel (CaPaKey in kolom `NISCode`).

| Bestand | Segment | Relevantie |
| ------- | ------- | ---------- |
| `transacties_woningen.csv` | Eengezinswoningen | Woningverkopen (primair) |
| `transacties_appartementen.csv` | Appartementen | Woningverkopen (aanvullend) |
| `transacties_industrie_terrein.csv` | Industrieterrein (onbebouwd) | Proxy perceelverkopen |
| `transacties_industrie_bebouwd.csv` | Industrie bebouwd | Beperkt relevant |
| `transacties_handel.csv` / `transacties_kantoren.csv` | Handel / kantoren | Niet direct voor woon-flows |

**Belangrijke kolommen:** `NISCode` (CaPaKey), `sum_ParcelsNumber` (aantal transacties), `avg_PriceP50` (prijs). **Geen jaarkolom** — annualisatie nog te bepalen.

**Beleidsaanname publiek/privé:** geen split in data → **50%** van transacties publiek; voor aankoopbeleid **50%** daarvan opkoopbaar → **25%** van alle transacties als teller.

Prijzen worden berekend in `contour/prices.py` (gewogen mediane transactieprijs per CaPaKey → aggregatie per geluidsband).

### 2.5 Detail: vergunningsdata

| Variabele | Status | Bron | Opmerking |
| --------- | ------ | ---- | --------- |
| `vergunde_wooneenheden_nieuwbouw` | 🟡 | Omgevingsloket → `Nieuwbouw` | **Geen MER-split** mogelijk → totaal als teller |
| `gem_wooneenheden_per_vergunning` | 🟡 | Omgevingsloket | Per gemeente/jaar |
| `vergunningen_kwetsbare_groep` | 🟡 | `vergunningen_kwetsbare_functies_2026_lang.csv` | Geen contour-koppeling |
| `renovatie_totaal`, R⁺, R⁻ | 🟡 | `Verbouwen of hergebruik` | Niet gesplitst op isolatie |
| MER-plichtig / niet-MER-plichtig | ❌ | — | `verbod_grote_woning`: `flow_rate_active = 0` |
| Opsplitsingsvergunningen | ❌ | — | `woonverdichtingsverbod_*`: `flow_rate_active = 0` |

### 2.6 Detail: overige bronnen

| Variabele | Status | Bron |
| --------- | ------ | ---- |
| `inwoners_per_contour` | ✅ | `input/lden_contour.csv`; Brussel: `data/inwoners_brussel_sector_contour_2024.xlsx` |
| Verkavelingsdata | 🟡 | `data/vergunningen_verkaveling_2026_lang.csv`; `verkavelingsverbod` heeft rate 0 |

### 2.7 Samenvatting databeschikbaarheid

| Categorie | ✅ | 🟡 | ❌ |
| --------- | - | - | - |
| Stocks (contour) | 5 | 2 | 0 |
| Woongebied-percelen | 2 | 0 | 0 |
| Vergunningen | 0 | 6 | 2 |
| Transacties | 0 | 4 | 0 |
| Eenheidsprijzen | 0 | 4 | 0 |
| Overig | 1 | 1 | 1 |

**Knelpunten:** annualisatie transacties, iso-split woningen, gemeente→contour-koppeling omgevingsloket, CaPaKey→contour voor transactietellers.

---

## 3. Outputs: stocks

De simulator werkt met **zeven stocks** (§2.1). Onderstaande tabel beschrijft hoe elke stock wordt **ingevuld** vanuit basisdata vóór en tijdens de simulatie.

| Stock | Startwaarde (basisdata) | Dynamiek tijdens simulatie |
| ----- | ----------------------- | --------------------------- |
| `onbebouwde_bebouwbare_percelen` | Kolom op `input/lden_contour.csv` (nu placeholder 0) | Daalt via aankoop/voorkoop/onteigening; stijgt via `woongebiedverbod` (uit `onbebouwde_onbebouwbare_percelen`) |
| `onbebouwde_onbebouwbare_percelen` | Idem (placeholder 0) | Daalt via `woongebiedverbod` |
| `bewoonde_niet_geïsoleerde_woning` | 80% van woningen per band | Inflow uit `nieuwe_woning` (niet-geïsoleerd); outflow via renovatie/isolatieflows en aankoop/voorkoop/onteigening |
| `bewoonde_geïsoleerde_woning` | 20% van woningen per band | Inflow uit `nieuwe_woning` (geïsoleerd) en isolatieflows; outflow via aankoop/voorkoop/onteigening |
| `nieuwe_woning` | 0 | Gevuld door bouwverboden (`verbod_kleine_woning`, `verbod_kwetsbare_groep`, …); leegt via isolatievoorschriften nieuwbouw |
| `perceel_eigendom_overheid` | 0 | Stijgt via `aankoopbeleid_percelen`, `voorkooprecht_percelen`, `onteigening_percelen` |
| `woning_eigendom_overheid` | 0 | Stijgt via aankoop/voorkoop/onteigening woningen |

**Invoer voor stocks:** kolommen op `input/lden_contour.csv` (§2.1), afgeleid uit `contour/consolidate.py` ← `contour_data.ipynb`.

---

## 4. Outputs: flows

Elke rij in `input/flow_rules.csv` definieert een flow. **r_f** wordt berekend uit tellers (§2.2) en noemers (§2.1). Waar de noemer een stock is, geldt per zone de zone-totalen op **BEGINJAAR**.

### 4.1 Overzicht alle flows

| `measure_id` | Flow (`inflow` → `outflow`) | Mode | Formule **r_f** (actief) | Benodigde basisdata |
| ------------ | ----------------------------- | ---- | ------------------------ | ------------------- |
| `verkavelingsverbod` | — | — | `0` | Geen effect op hinder |
| `woongebiedverbod` | `onbebouwde_onbebouwbare_percelen` → `onbebouwde_bebouwbare_percelen` | transfer | `bebouwbare_percelen_woongebied(5jr)` / (5 × `onbebouwde_onbebouwbare_percelen`) | §2.2 woongebied / §2.1 noemer |
| `aankoopbeleid_percelen` | `onbebouwde_bebouwbare_percelen` → `perceel_eigendom_overheid` | transfer | (0,25 × `alle_transacties_percelen`) / `onbebouwde_bebouwbare_percelen` | §2.4 transacties |
| `voorkooprecht_percelen` | idem | transfer | `alle_verkopen_onbebouwde_bebouwbare_percelen` / `onbebouwde_bebouwbare_percelen` | §2.4 |
| `onteigening_percelen` | idem | transfer | **0,05** (vast) | Beleidsaanname |
| `verbod_kleine_woning` | `onbebouwde_bebouwbare_percelen` → `nieuwe_woning` | transfer | `vergunde_wooneenheden_nieuwbouw` / `onbebouwde_bebouwbare_percelen` | §2.5 omgevingsloket |
| `verbod_grote_woning` | idem | transfer | **0** | ❌ MER-split niet mogelijk |
| `verbod_kwetsbare_groep` | idem | transfer | (`gem_wooneenheden_per_vergunning` × `vergunningen_kwetsbare_groep`) / `onbebouwde_bebouwbare_percelen` | §2.5 |
| `woonverdichtingsverbod_niet_geïsoleerde_woningen` | `bewoonde_niet_geïsoleerde_woning` → zelfde | growth | **0** | ❌ opsplitsing niet identificeerbaar |
| `woonverdichtingsverbod_geïsoleerde_woningen` | `bewoonde_geïsoleerde_woning` → zelfde | growth | **0** | ❌ idem |
| `aankoopbeleid_niet_geïsoleerde_woningen` | `bewoonde_niet_geïsoleerde_woning` → `woning_eigendom_overheid` | transfer | (0,25 × `alle_transacties_woningen`) / `bewoonde_niet_geïsoleerde_woning` | §2.4 |
| `aankoopbeleid_geïsoleerde_woningen` | `bewoonde_geïsoleerde_woning` → `woning_eigendom_overheid` | transfer | (0,25 × `alle_transacties_woningen`) / `bewoonde_geïsoleerde_woning` | §2.4 |
| `voorkooprecht_niet_geïsoleerde_woningen` | idem | transfer | `alle_verkopen_woningen` / `bewoonde_niet_geïsoleerde_woning` | §2.4 |
| `voorkooprecht_geïsoleerde_woningen` | idem | transfer | `alle_verkopen_woningen` / `bewoonde_geïsoleerde_woning` | §2.4 |
| `onteigening_niet_geïsoleerde_woningen` | idem | transfer | **0,05** | Beleidsaanname |
| `onteigening_geïsoleerde_woningen` | idem | transfer | **0,05** | Beleidsaanname |
| `isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning` | `nieuwe_woning` → `bewoonde_niet_geïsoleerde_woning` | transfer | `nieuwbouw_niet_geïsoleerd` / `nieuwe_woning` | §2.2 iso-split |
| `isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning` | `nieuwe_woning` → `bewoonde_geïsoleerde_woning` | transfer | `nieuwbouw_geïsoleerd` / `nieuwe_woning` | §2.2 |
| `renovatie_zonder_maatregel` | `bewoonde_niet_geïsoleerde_woning` → `bewoonde_geïsoleerde_woning` | transfer | R⁺ / `bewoonde_niet_geïsoleerde_woning` (**baseline**) | §2.2; actief = 0 |
| `verplicht_isoleren_renovatie` | idem | transfer | (R⁺ + R⁻) / `bewoonde_niet_geïsoleerde_woning` | §2.2 |
| `gesubsidieerd_isolatieprogramma` | idem | transfer | (2 × (R⁺ + R⁻)) / `bewoonde_niet_geïsoleerde_woning` | §2.2 |
| `gestuurd_isolatieprogramma` | idem | transfer | (4 × (R⁺ + R⁻)) / `bewoonde_niet_geïsoleerde_woning` | §2.2 |
| `aanleg_geluidsbuffers` | idem | transfer | (`potentieel_isoleerbare_woningen` / 5) / `bewoonde_niet_geïsoleerde_woning` | ❌ §2.2 |
| `compensatie_buitenzone` | — | — | `0` | Alleen kosten |
| `compensatie_verhuis` | — | — | `0` | Alleen kosten |
| `versterken_sociale_cohesie` | — | — | `0` | Geen effect |
| `vergroenen_leefomgeving` | — | — | `0` | Geen effect |

### 4.2 Berekening per categorie

#### Percelen

**`woongebiedverbod`** — Teller: jaarlijks aandeel woongebied-creatie (`bebouwbare_percelen_woongebied(5jr)` / 5). Noemer: `onbebouwde_onbebouwbare_percelen`. Status: ✅ teller / 🟡 noemer (placeholder).

**`aankoopbeleid_percelen`** — Equivalent: (0,5 × 0,5 × `alle_transacties_percelen`) / `onbebouwde_bebouwbare_percelen`. Aanname §2.4.

**`voorkooprecht_percelen`** — Verkopen van **onbebouwde bebouwbare** percelen (niet onbebouwbare).

**`onteigening_percelen`** — Vaste rate 0,05 (30% reductie gehinderden over 5 jaar).

#### Nieuwbouw en bouwverboden

Gemeenschappelijke teller: `vergunde_wooneenheden` = `gem_wooneenheden_per_vergunning` × aantal vergunningen.

**`verbod_kleine_woning`** — Teller = **alle** vergunde wooneenheden nieuwbouw (geen MER-split). **`verbod_grote_woning`** — actief op nul.

#### Woningen — aankoop, voorkoop, onteigening

Zelfde 25%-aanname als percelen. **Geen iso-split** in transactiedata voor verdeling niet-geïsoleerd/geïsoleerd.

#### Isolatie — nieuwbouw

Noemer `nieuwe_woning` is dynamische tussenstock. Bij actieve maatregel: volledige nieuwbouwflow naar geïsoleerd; rest naar niet-geïsoleerd (prioriteit in `flow_rules.csv`).

#### Isolatie — renovatie

R⁺ en R⁻ afgeleid uit `renovatie_totaal` (§2.2). **`renovatie_zonder_maatregel`**: alleen baseline; bij actieve renovatiemaatregel `flow_rate_active = 0`.

#### Geluidsbuffers

Gefaseerd over 5 jaar: 20% per jaar van `potentieel_isoleerbare_woningen`.

### 4.3 Matrix data-afhankelijkheden

| `measure_id` | Teller OK? | Noemer OK? |
| ------------ | ---------- | ---------- |
| `woongebiedverbod` | ✅ | 🟡 |
| `aankoopbeleid_percelen` | 🟡 | 🟡 |
| `voorkooprecht_percelen` | 🟡 | 🟡 |
| `onteigening_percelen` | ✅ (aanname) | 🟡 |
| `verbod_kleine_woning` | 🟡 | 🟡 |
| `verbod_grote_woning` | ✅ (beleidskeuze) | 🟡 |
| `verbod_kwetsbare_groep` | 🟡 | 🟡 |
| `woonverdichtingsverbod_*` | ✅ (beleidskeuze) | ✅ |
| `aankoopbeleid_*_woningen` | 🟡 | ✅ |
| `voorkooprecht_*_woningen` | 🟡 | ✅ |
| `onteigening_*_woningen` | ✅ (aanname) | ✅ |
| `isolatievoorschriften_nieuwbouw_*` | 🟡 | ✅ |
| `renovatie_*` / isolatieprogramma's | 🟡 | ✅ |
| `aanleg_geluidsbuffers` | ❌ | ✅ |

---

## 5. Kostenberekening

### 5.1 Eenheidsprijzen

Zie §2.3. Vier prijzen per contour via `contour/prices.py` → `input/lden_contour.csv`.

### 5.2 Per maatregel

Kolommen `rel_cost_overheid` en `rel_cost_prive` in `input/measure_costs.csv` zijn **vermenigvuldigers** op de rijkost. `kost_stock = -` → geen eenheidsprijs.

| Maatregel | Teller (flow) | Noemer (stock) | `kost_stock` | Prijskolom |
| --------- | ------------- | -------------- | ------------ | ---------- |
| `verkavelingsverbod` | — | `onbebouwde_bebouwbare_percelen` | `-` | — |
| `woongebiedverbod` | woongebied / 5 | `onbebouwde_onbebouwbare_percelen` | `-` | — |
| `aankoopbeleid_percelen` | 0,25 × transacties percelen | `onbebouwde_bebouwbare_percelen` | `onbebouwde_bebouwbare_percelen` | `prijs_onbebouwde_bebouwbare_percelen` |
| `voorkooprecht_percelen` | verkoop bebouwbare percelen | `onbebouwde_bebouwbare_percelen` | idem | idem |
| `onteigening_percelen` | vast 0,05 | `onbebouwde_bebouwbare_percelen` | idem | idem |
| `verbod_kleine_woning` | vergunde wooneenheden | `onbebouwde_bebouwbare_percelen` | idem | idem |
| `verbod_grote_woning` | — (active = 0) | idem | idem | idem |
| `verbod_kwetsbare_groep` | gem. WE × kwetsbaar | idem | idem | idem |
| `woonverdichtingsverbod_*` | — (active = 0) | bewoonde *_woning | `-` | — |
| `aankoopbeleid_*_woningen` | 0,25 × transacties woningen | bewoonde *_woning | bewoonde *_woning | `prijs_bewoonde_*_woning` |
| `voorkooprecht_*_woningen` | alle verkoop woningen | bewoonde *_woning | idem | idem |
| `onteigening_*_woningen` | vast 0,05 | bewoonde *_woning | idem | idem |
| `isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning` | nieuwbouw niet-iso | `nieuwe_woning` | `-` | — |
| `isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning` | nieuwbouw geïsoleerd | `nieuwe_woning` | `bewoonde_geïsoleerde_woning` | `prijs_bewoonde_geïsoleerde_woning` |
| `renovatie_zonder_maatregel` | R⁺ (baseline) | `bewoonde_niet_geïsoleerde_woning` | idem | `prijs_bewoonde_niet_geïsoleerde_woning` |
| `verplicht_isoleren_renovatie` | R⁺ + R⁻ | idem | idem | idem |
| `gesubsidieerd_isolatieprogramma` | 2 × (R⁺ + R⁻) | idem | idem | idem |
| `gestuurd_isolatieprogramma` | 4 × (R⁺ + R⁻) | idem | idem | idem |
| `aanleg_geluidsbuffers` | potentieel / 5 | idem | idem | idem |
| `compensatie_buitenzone` / `compensatie_verhuis` | — | — | `bewoonde_niet_geïsoleerde_woning` | `prijs_bewoonde_niet_geïsoleerde_woning` |
| `versterken_sociale_cohesie` / `vergroenen_leefomgeving` | — | — | `-` | — |

**Kostenvermenigvuldigers** (uit `measure_costs.csv`): aankoop/voorkoop/onteigening 1,0–1,5× overheid; isolatie renovatie 0,15× privé; gesubsidieerd 0,05 overheid + 0,1 privé; compensatie 0,01× overheid.

---

## 6. Workflow

| Component | Doel |
| --------- | ---- |
| [`contour_data.ipynb`](contour_data.ipynb) | §2 basisdata laden → master DataFrames → parquet in `output/intermediate/` |
| [`contour_flows.ipynb`](contour_flows.ipynb) | §3–§4 stocks, tellers, flow rates → export `input/flow_rules.csv` |
| [`contour/`](contour/) | Herbruikbare modules: `loaders`, `consolidate`, `spatial`, `flows`, `export`, `pipeline` |
| [`contour_legacy.ipynb`](contour_legacy.ipynb) | Archief oorspronkelijk notebook |

**Uitvoeringsvolgorde:** `contour_data.ipynb` → `contour_flows.ipynb` (of `python -c "from contour.pipeline import run_data_pipeline, run_flows_pipeline; run_flows_pipeline(run_data_pipeline())"`).

**Open blokkades:**

1. Gemeente–contour naamkoppeling (fusiegemeenten → `vergunningen_niet_toewijsbaar`)
2. CaPaKey–contour (stub in `capakey_naar_contour()`)
3. Placeholder vastgoedstocks in `contour/consolidate.py`
4. Validatie: `contour/flows.py` → `valideer_flow_rates()`

---

## 7. Bronbestanden

**Naamgevingsconventie:** `{thema}_{onderwerp}_{jaar}.xlsx` (ruw) en `{thema}_{onderwerp}_{jaar}_lang.csv` (plat); transacties onder `data/transacties_vastgoed/transacties_{segment}.csv`. Overzicht: `data/README.md`.

| Bestand | Inhoud |
| ------- | ------ |
| `data/contour_vlaanderen_stocks.xlsx` | Vlaanderen: inwoners, woningen, stocks, woongebied-percelen, prijzen |
| `data/inwoners_brussel_sector_contour_2024.xlsx` | Brussel: inwoners per sector × contour |
| `data/population 2024 par bout de secteur stat.xlsx` | Sector × dB voor gemeente→contour |
| `data/vergunningen_omgevingsloket_2026_lang.csv` | Vergunningen omgevingsloket |
| `data/vergunningen_kwetsbare_functies_2026_lang.csv` | Vergunningen kwetsbare functies |
| `data/vergunningen_verkaveling_2026_lang.csv` | Verkaveling/sloop |
| `data/transacties_vastgoed/transacties_*.csv` | Vastgoedtransacties per CaPaKey |
| `input/lden_contour.csv` | Contour + stocks + vier prijskolommen |
| `input/flow_rules.csv` | Flow-definities (rates te vervangen) |
| `input/measure_costs.csv` | Kostenvermenigvuldigers per maatregel |

---

## 8. Openstaande definities

| Vraag | Voorstel |
| ----- | -------- |
| MER-plichtig vs. niet-MER-plichtig | Totaal vergunde wooneenheden; `verbod_grote_woning` op 0 |
| Opsplitsing woningen | `woonverdichtingsverbod_*` op 0 |
| Iso-split nieuwbouw/renovatie | Vast aandeel of externe bron |
| Gemeente → contour | Som sector-opp-aandeel per gemeente × dB (`contour/spatial.py`) |
| CaPaKey → contour | Ruimtelijke join transactiedata met contourpolygonen |
| Jaar voor tellers | Laatste jaar of rollend gemiddelde; transacties zonder jaarkolom |
| Publiek vs privé | 50% publiek; 25% opkoopbaar voor aankoopbeleid |

### Controlepunten (gecorrigeerd t.o.v. eerdere versies)

1. **Woongebiedverbod** — noemer is `onbebouwde_onbebouwbare_percelen`; teller is jaarlijks (cumulatief / 5).
2. **Onteigening** — vaste rate 0,05, niet stock/stock.
3. **Isolatie nieuwbouw** — rates per simulatiejaar herberekenen (tussenstock `nieuwe_woning`).
4. **Renovatie zonder maatregel** — alleen baseline; actief = 0 bij andere renovatiemaatregel.
