# Balanced approach luchthaven

`uv sync`


`uv run streamlit run app.py`

## Berekening

### Simulatie per jaar en per zone (`_simulate_year_zone`)

De kernlogica van de simulatie werkt in 2 fasen voor elke combinatie van `jaar` en `zone`.

1. **Initialisatie van jaar+1 met de huidige toestand (carry-over)**
   - Voor elke stock in de lijst (`bewoonde_*`, `niet_bewoonde_*`, `nieuwe_woning`, `onbebouwde_*`, `*_eigendom_overheid`) wordt eerst:
     - `waarde(jaar+1) = waarde(jaar)`
   - Hierdoor start `jaar+1` als kopie van de huidige toestand.

2. **Sequentieel toepassen van alle flows voor die zone**
   - Voor elke flow-rij uit `flows.csv`:
     - lees `inflow_stock_name`, `outflow_stock_name`
     - lees de relatieve factoren `(inflow_relative, outflow_relative)` via `row.get_flow()`
     - lees de **huidige werkwaarden** in `jaar+1`:
       - `future_inflow_stock_value`
       - `future_outflow_stock_value`

#### Waarom de absolute flow op `future_inflow_stock_value` wordt berekend

Absolute hoeveelheden worden berekend op basis van de reeds opgebouwde waarde in `jaar+1`:

- `inflow_absolute = future_inflow_stock_value * inflow_relative`
- `outflow_absolute = future_inflow_stock_value * outflow_relative`

Dit is belangrijk omdat flows binnen hetzelfde jaar elkaar beïnvloeden.  
Bijvoorbeeld: `nieuwe_woning` kan eerst toenemen door eerdere flows, en moet later in datzelfde jaar kunnen afnemen door `isolatievoorschriften_nieuwbouw_*`.

#### Updatevergelijkingen per flow-stap

Voor elke flow-stap worden de nieuwe waarden:

- `future_inflow_stock_value = future_inflow_stock_value - inflow_absolute`
- `future_outflow_stock_value = future_outflow_stock_value + outflow_absolute`

Bescherming:
- Als `future_inflow_stock_value < 0`, wordt een `ValueError` gegooid.

Daarna worden beide waarden teruggeschreven naar de stocktabel voor `jaar+1`.

### Logging in `flow_log.csv`

Per flow-stap wordt één logregel toegevoegd met o.a.:

- `orig_future_inflow_stock_value` = inflow-waarde vóór de stap
- `new_future_inflow_stock_value` = inflow-waarde na de stap
- `orig_future_outflow_stock_value` = outflow-waarde vóór de stap
- `new_future_outflow_stock_value` = outflow-waarde na de stap
- `delta_inflow = new_future_inflow_stock_value - orig_future_inflow_stock_value`
- `delta_outflow = new_future_outflow_stock_value - orig_future_outflow_stock_value`

Interpretatie:
- `delta_inflow` is normaal negatief of 0 (afname van inflow stock)
- `delta_outflow` is normaal positief of 0 (toename van outflow stock)

### Aggregatie naar `flow_log_zone.csv`

Na het wegschrijven van `flow_log.csv` wordt `flow_log_zone.csv` gemaakt:

- Mapping gebeurt via `input/zones.csv` (5 dB-zones).
- Groepering gebeurt op:
  - `zone`, `jaar`, `naam_flow`, `inflow_stock_name`, `outflow_stock_name`
- Numerieke velden (`orig/new/delta`) worden gesommeerd.

