# Code Structure Documentation

This document describes the refactored structure of the simulation application and the input data files.

## Overview

The application has been restructured into a modular architecture with clear separation of concerns:

- **Configuration**: Centralized constants and settings
- **Models**: Data management classes for stocks and flows
- **Simulation**: Business logic for year-by-year calculations
- **UI**: Streamlit interface components

## Directory Structure

```
.
├── app.py                      # Main Streamlit application entry point
├── config.py                   # Configuration constants
├── models/                     # Data models
│   ├── __init__.py
│   ├── stock_manager.py                  # Manages stock data operations
│   ├── measure_selection_manager.py      # UI measure metadata + selections
│   └── simulation_input_loader.py        # Builds validated SimulationState inputs
│
├── simulation/                 # Simulation logic
│   ├── __init__.py
│   ├── engine.py               # Main simulation engine
│   ├── state.py                # SimulationState, FlowRule, SimulationOutputs
│   └── helpers.py              # Calculation helper functions
│
├── ui/                         # UI components
│   ├── __init__.py
│   ├── auth.py                 # Authentication logic
│   └── components.py           # Streamlit UI components
│
├── contour/                    # Contour data + flow-rate preparation (see below)
├── contour_data.ipynb          # Load sources → parquet (STOCKS_EN_FLOWS §2)
├── contour_flows.ipynb         # Stocks, tellers, flow rates → input/ (STOCKS_EN_FLOWS §4)
├── contour_legacy.ipynb        # Archived monolithic notebook
├── input/                      # CSV input data (see below)
└── output/                     # Generated CSV outputs (stock, flow logs)
    └── intermediate/           # Parquet tussenbestanden (contour pipeline)
```

## Contour pipeline (`contour/` + notebooks)

Brondata in `data/` wordt via twee notebooks (of `contour.pipeline`) omgezet naar dashboard-inputs:

1. **`contour_data.ipynb`** — inventaris, laden, consolidatie naar `output/intermediate/*.parquet`.
2. **`contour_flows.ipynb`** — stocks/tellers/flow rates per `measure_id`; export naar `input/lden_contour.csv`, `input/lnight_contour.csv` en bijgewerkte rates in `input/flow_rules.csv`.

| Module | Rol |
|--------|-----|
| `contour/loaders.py` | Lezen Excel/CSV bronnen |
| `contour/consolidate.py` | `contour_lden` / `contour_lnight` master-tabellen |
| `contour/spatial.py` | Gemeente→dB-contour; stub CaPaKey→contour |
| `contour/flows.py` | Flow-rate berekening (STOCKS_EN_FLOWS_BEREKENEN.md §4) |
| `contour/export.py` | Schrijven naar `input/` |
| `contour/prices.py` | Prijzen per contour uit `transacties_vastgoed/` (vervangt dummy Excel-prijzen) |
| `contour/pipeline.py` | End-to-end `run_data_pipeline()` / `run_flows_pipeline()` |

Zie [`STOCKS_EN_FLOWS_BEREKENEN.md`](STOCKS_EN_FLOWS_BEREKENEN.md) §6 voor workflow en openstaande blokkades.

## Input data (`input/`)

All simulation and UI configuration is driven by CSV files in `input/`. Paths are defined in `config.py`.

In the dashboard kiest de gebruiker **Lden** of **Lnight** (sidebar). Daarmee wisselen het contour- en zones-bestand; maatregelen, flowregels en kosten zijn voor beide gelijk.

| Bestand | Gebruikt door | Doel |
|---------|---------------|------|
| `lden_contour.csv` / `lnight_contour.csv` | `StockManager`, `SimulationEngine` | Startvoorraad en kengetallen per 1 dB-geluidscontour |
| `lden_zones.csv` / `lnight_zones.csv` | `StockManager`, `MeasureSelectionManager`, `SimulationEngine` | Zone-indeling (5 dB-buckets) |
| `measures.csv` | `MeasureSelectionManager` | Metadata en volgorde van maatregelen in de UI |
| `flow_rules.csv` | `simulation_input_loader`, validatie | Stock-flows per maatregel |
| `measure_costs.csv` | `simulation_input_loader`, validatie | Kostentoewijzing per maatregel |

`BEGINJAAR` in `config.py` (standaard 2026) bepaalt het jaartal in stock-kolomnamen op het contour (`*_2026`).

**Regionale stocks:** contourkolommen `*_vlaanderen_{jaar}` en `*_brussel_{jaar}` worden apart door de simulatie geëvolueerd; `*_totaal_{jaar}` blijft op het contour als controle/export. De simulatie gebruikt 16 regionale stocks (`{stock}_vlaanderen`, `{stock}_brussel`); `flow_rules.csv` blijft ongewijzigd — elke regel wordt parallel op beide regio’s toegepast.

---

### `lden_contour.csv` en `lnight_contour.csv`

Één rij per smalle geluidscontour (typisch 1 dB breed). Rijen worden via `midden` aan een zone uit het bijbehorende zones-bestand gekoppeld en per zone opgeteld tot startvoorraad.

| Kolom | Gebruik in de applicatie |
|-------|--------------------------|
| `Unnamed: 0` | Index uit export; wordt genegeerd bij inladen |
| `db_contour` | Label van de contour (bijv. `45-46`); alleen informatief |
| `lower` | Ondergrens geluidsniveau (dB) van de contour; informatief |
| `upper` | Bovengrens geluidsniveau (dB) van de contour; informatief |
| `midden` | Midden van het contour-interval; **bepaalt zone-toewijzing** (`min dBel ≤ midden < max dBel`) |
| `inwoners` | Aantal inwoners op deze contour; gebruikt in `contour.ipynb` om afgeleide kolommen te berekenen; niet direct in de simulatielus |
| `huizen` | Aantal woningen op deze contour; **gewogen gemiddelde prijs** bij kostberekening (`prijs × huizen`, per zone) |
| `aantal bebouwbare percelen die werden gecreëerd door woongebieden aan te duiden` | Historische indicator voor woongebied-dynamiek; gebruikt in `contour.ipynb` om flow rates af te leiden; **niet** ingelezen door `StockManager` |
| `aantal niet-bebouwbarepercelen die worden gecreëerd door woongebied te schrappen` | Idem; alleen relevant bij voorbereiding van data in `contour.ipynb` |
| `prijs_onbebouwde_bebouwbare_percelen` | Eenheidsprijs (€) voor kostberekening wanneer `kost_stock` = `onbebouwde_bebouwbare_percelen` |
| `prijs_onbebouwde_onbebouwbare_percelen` | Eenheidsprijs voor `onbebouwde_onbebouwbare_percelen` |
| `prijs_bewoonde_niet_geïsoleerde_woning` | Eenheidsprijs voor `bewoonde_niet_geïsoleerde_woning` |
| `prijs_bewoonde_geïsoleerde_woning` | Eenheidsprijs voor `bewoonde_geïsoleerde_woning` |
| `dosis_effect_relatie` | Dosis-effectfactor per contour; vermenigvuldiger voor **ernstig gehinderden** (met/zonder isolatie) |
| `gemiddeld_aantal_inwoners_per_huis` | Gemiddeld aantal inwoners per woning; gebruikt voor **gehinderde personen** en ernstig gehinderden |
| `aantal_ernstig_gehinderden_vlaanderen_{jaar}` / `_brussel_{jaar}` | Ernstig gehinderden per regio; na simulatie herberekend uit regionale woningstocks |
| `aantal_ernstig_gehinderden_totaal_{jaar}` | Som op contour (notebook); in dashboard als `aantal_ernstig_gehinderden` = Vlaanderen + Brussel |
| `aantal_bewoonde_geïsoleerde_huizen_vlaanderen_{jaar}` (en `_brussel_`, `_totaal_`) | Startvoorraad; simulatie op `_vlaanderen` / `_brussel` → intern `bewoonde_geïsoleerde_woning_vlaanderen` enz. |
| `aantal_bewoonde_niet_geïsoleerde_huizen_{jaar}` | Startvoorraad; wordt intern `bewoonde_niet_geïsoleerde_woning` |
| `aantal_onbebouwde_bebouwbare_percelen_{jaar}` | Startvoorraad; wordt intern `onbebouwde_bebouwbare_percelen` |
| `aantal_perceel_eigendom_overheid_{jaar}` | Startvoorraad; wordt intern `perceel_eigendom_overheid` |
| `aantal_woning_eigendom_overheid` | Startvoorraad overheidswoningen (zonder jaarsuffix in de export); wordt intern `woning_eigendom_overheid` |

Stocks die in de simulatie voorkomen maar **ontbreken** op het contour krijgen automatisch kolom `{stocknaam}_{BEGINJAAR}` met waarde `0`.

Simulatiestocks (9 stuks) die uit het contour komen of op 0 worden gezet:

`bewoonde_geïsoleerde_woning`, `bewoonde_niet_geïsoleerde_woning`, `niet_bewoonde_geïsoleerde_woning`, `niet_bewoonde_niet_geïsoleerde_woning`, `nieuwe_woning`, `onbebouwde_bebouwbare_percelen`, `onbebouwde_onbebouwbare_percelen`, `perceel_eigendom_overheid`, `woning_eigendom_overheid`.

---

### `lden_zones.csv` en `lnight_zones.csv`

Definieert de 5 dB-zones (A, B, …) waarin contourrijen en UI-selecties worden gegroepeerd. Lden- en Lnight-versies verschillen in de dB-grenzen.

| Kolom | Gebruik in de applicatie |
|-------|--------------------------|
| `zone` | Zonecode (bijv. `A`); **lijst van zones** voor sidebar, simulatie en aggregatie |
| `min dBel` | Ondergrens van de zone (inclusief); koppeling contour via `midden`; sortering zones (hoog → laag) |
| `max dBel` | Bovengrens van de zone (exclusief); ook gebruikt bij hergroepering van `flow_log.csv` naar `flow_log_zone.csv` |
| `leefbaarheidspunten_geïsoleerd` | Punten per geïsoleerde inwoner per zone (default voor UI-berekening) |
| `leefbaarheidspunten_niet_geïsoleerd` | Punten per niet-geïsoleerde inwoner per zone (default voor UI-berekening) |

---

### `measures.csv`

Catalogus van alle maatregelen voor de Streamlit-sidebar en validatie.

| Kolom | Gebruik in de applicatie |
|-------|--------------------------|
| `measure_id` | Unieke technische sleutel; koppelt aan `flow_rules.csv` en `measure_costs.csv`; interne naam in selectiestatus |
| `naam_mooi` | Weergavenaam in de sidebar (`st.segmented_control`) |
| `help` | Markdown-uitleg in de tooltip van de maatregel |
| `hidden_in_ui` | `TRUE` = maatregel niet tonen in sidebar (wel simuleren als flow actief is) |
| `group_id` | Optionele groep: maatregelen met dezelfde `group_id` (≥2 rijen) delen één zone-selector in de UI |
| `priority` | Sorteervolgorde in sidebar en bij inladen; **lager = eerder** |

Verplichte kolommen worden gevalideerd in `MeasureSelectionManager._validate_normalized_inputs`.

---

### `flow_rules.csv`

Definieert per regel hoe een maatregel stocks jaar-op-jaar beïnvloedt. Meerdere regels kunnen naar dezelfde `measure_id` verwijzen (bijv. transfer naar geïsoleerd én niet-geïsoleerd).

| Kolom | Gebruik in de applicatie |
|-------|--------------------------|
| `rule_id` | Unieke sleutel per regel; komt in flow-log |
| `measure_id` | Koppeling naar `measures.csv`; bepaalt of regel **actief** is (zone geselecteerd in UI) |
| `inflow_stock` | Stock waar de flow op wordt toegepast (noemer bij `flow_absolute = waarde × rate`) |
| `outflow_stock` | Bestemmingsstock bij `transfer`; bij `growth` vaak gelijk aan `inflow_stock` |
| `flow_rate_baseline` | Jaarlijkse rate als maatregel **niet** actief is in die zone |
| `flow_rate_active` | Jaarlijkse rate als maatregel **wel** actief is in die zone |
| `flow_mode` | `transfer` (verschuiving tussen stocks) of `growth` (toename op inflow) |
| `comments` | Vrije documentatie; niet gebruikt in code |
| `priority` | Volgorde waarin regels binnen een zone worden toegepast; **lager = eerder** |

Geldige stocknamen moeten overeenkomen met de negen simulatiestocks (zie contour-sectie).

---

### `measure_costs.csv`

Kostenparameters per maatregel; wordt bij inladen samengevoegd met `flow_rules.csv` op `measure_id`.

| Kolom | Gebruik in de applicatie |
|-------|--------------------------|
| `measure_id` | Koppeling naar `measures.csv` |
| `rel_cost_overheid` | Vermenigvuldiger op berekende rijkost → **totale kost overheid** |
| `rel_cost_prive` | Vermenigvuldiger op berekende rijkost → **totale kost privé** |
| `kost_stock` | Stock waarvan de eenheidsprijs uit het contour wordt gehaald; `-` of leeg = geen kost voor deze maatregel |

Rijkost = `|delta_outflow| × gewogen_gemiddelde_prijs` (gewogen met `huizen` per contour in de zone), alleen wanneer de maatregel actief is.

---

## Module Descriptions

### `config.py`
Centralized configuration for:
- Authentication settings
- Simulation parameters (`BEGINJAAR`, `LOOPTIJD`, `EINDJAAR`)
- Conversion factors (`PERSONEN_PER_WOONUNIT`, …)
- File paths to all `input/` and `output/` CSVs

### `models/stock_manager.py`
`StockManager` class for managing stock data:
- Loads contour + zones CSV
- Maps contour rows to zones via `midden`
- `get_aantal(naam, jaar, zone)`: Get aggregated stock value
- `set_aantal(naam, jaar, zone, aantal)`: Set value (proportioneel over contourrijen in de zone)
- `save(output_file)`: Save stock data to CSV
- `get_zone_contour_frame(zone, jaar)`: Contourdetail voor afgeleide metrics

### `models/measure_selection_manager.py`
`MeasureSelectionManager` class for UI measure metadata and selections:
- `get_selected_zones(maatregel_naam)`: Zones where measure is applied
- `set_selected_zones(maatregel_naam, selected_zones)`: Set measure zones
- `is_measure_applied(naam, zone)`: Check if measure is applied
- `get_ui_sidebar_entries()`: Sidebar order from `measures.csv` (`priority`, `group_id`, `hidden_in_ui`)

### `models/simulation_input_loader.py`
Loads and validates `flow_rules.csv` + `measure_costs.csv` and builds `SimulationState` with `FlowRule` entries per zone.

### `simulation/engine.py`
`SimulationEngine` class for running simulations:
- `load_inputs(beginjaar, eindjaar)`: Build simulation state from inputs
- `run_simulation_state(state)`: Year-by-year flow loop (in-memory)
- `build_outputs(state)` / `persist_outputs(outputs)`: Flow logs, derived metrics, costs

### `simulation/helpers.py`
Helper functions for derived hinder calculations.

### `ui/auth.py`
Authentication module:
- `check_password()`: Check user authentication

### `ui/components.py`
UI rendering functions:
- `render_sidebar_controls()`: Measure selection sidebar
- `render_metrics()`: Key metrics (gehinderde personen, kosten)
- `render_charts()`: Visualization charts
- `render_ernstig_gehinderden_chart()`: Staafgrafiek zone × beginjaar/eindjaar × regio (Vlaanderen / Brussel)
- `render_leefbaarheidspunten_chart()`: Zelfde opmaak, gestapeld niet-geïsoleerd / geïsoleerd
- `render_flow_log_zone_table()`: Table from `output/flow_log_zone.csv`

### `app.py`
Main application entry point:
1. Authentication
2. Contour type selection (Lden / Lnight)
3. Initialize managers
4. Render sidebar and validate measure conflicts
5. Run simulation and persist outputs
6. Render metrics and charts

## Output data (`output/`)

| Bestand | Inhoud |
|---------|--------|
| `stock.csv` | Voorraad per `naam`, `jaar`, `zone` (en `Totaal`) na de simulatie |
| `flow_log.csv` | Detail-log per zone, jaar en flow-regel |
| `flow_log_zone.csv` | Zelfde log, geaggregeerd naar 5 dB-zones |

Zie `readme.md` voor de interpretatie van flow-logvelden en transfer vs. growth.

## Benefits of This Structure

1. **Separation of Concerns**: Each module has a single, clear responsibility
2. **Easier Testing**: Individual components can be tested in isolation
3. **Maintainability**: Changes to one area don't affect others
4. **Extensibility**: Easy to add new measures, stocks, or UI components via CSV
5. **Reusability**: Components can be reused in different contexts
6. **Readability**: Clear structure makes code easier to understand

## Adding New Features

### Adding a new measure
1. Voeg een rij toe aan `measures.csv` (`measure_id`, `naam_mooi`, `help`, `priority`, …).
2. Voeg één of meer regels toe aan `flow_rules.csv` (stocks, rates, `flow_mode`, `priority`).
3. Voeg een rij toe aan `measure_costs.csv` met dezelfde `measure_id`.
4. Optioneel: pas `models/validation.py` aan voor incompatibele combinaties.

### Changing initial stocks or prices
1. Pas `lden_contour.csv` / `lnight_contour.csv` aan (kolommen `aantal_*_{BEGINJAAR}` en `prijs_*`).
2. Controleer zone-indeling in `lden_zones.csv` / `lnight_zones.csv` als `midden`-waarden wijzigen.

### Adding a new simulated stock
1. Voeg startkolom toe op het contour (`{naam}_{BEGINJAAR}`) of laat `StockManager` deze op 0 zetten.
2. Neem de stock op in `simulation_input_loader.load_simulation_inputs` (`stock_names`).
3. Voeg flowregels toe in `flow_rules.csv` waar nodig.

### Adding a new calculation or chart
1. Voeg logica toe in `simulation/engine.py` of `simulation/helpers.py`.
2. Toon resultaat in `ui/components.py`.

## Migration Notes

The refactor uses explicit managers for UI selections and simulation input loading. Legacy bestandsnamen (`flow.csv`, `beschrijving_maatregelen.csv`, `stock.csv` in `input/`) zijn vervangen door `flow_rules.csv`, `measures.csv` en contour-gebaseerde startvoorraad.
