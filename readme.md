# Balanced approach luchthaven

`uv sync`

`uv run streamlit run app.py`

## Contour data (marimo)

Traceerbare opbouw van `lden` / `lnight` staat in **`contour_data.py`** (marimo-notebook, geconverteerd uit `contour_data.ipynb`).

```powershell
uv run marimo edit contour_data.py
```

Na wijzigingen in het Jupyter-notebook opnieuw converteren:

```powershell
uv run marimo convert contour_data.ipynb -o contour_data.py
uv run python scripts/marimo_post_convert.py
```

## Kunstmatige vertraging (demo)

Standaard staat een korte pauze tussen stappen aan (~3,8 s extra per pagina-refresh), met een `st.spinner` per stap (data laden, simulatie, …).

| Omgevingsvariabele | Default | Stap |
|--------------------|---------|------|
| `ARTIFICIAL_DELAY_ENABLED` | `true` | Alles aan/uit |
| `ARTIFICIAL_DELAY_INIT_S` | `0.6` | Data laden |
| `ARTIFICIAL_DELAY_SIMULATION_S` | `2.0` | Simulatie |
| `ARTIFICIAL_DELAY_LEEFBAARHEIDSPUNTEN_S` | `0.4` | Leefbaarheidspunten |
| `ARTIFICIAL_DELAY_RENDER_S` | `0.5` | KPI's en grafieken |
| `ARTIFICIAL_DELAY_SAVE_S` | `0.3` | Opslaan CSV |

Snelle modus voor de klant:

```powershell
$env:ARTIFICIAL_DELAY_ENABLED="false"
uv run streamlit run app.py
```

## Berekening

### Simulatie per jaar en per zone (`run_simulation_state`)

De kernlogica van de simulatie werkt in 2 fasen voor elke combinatie van `jaar` en `zone`, op de in-memory `SimulationState`.

1. **Initialisatie van jaar+1 met de huidige toestand (carry-over)**
   - Voor elke stock in de lijst (`bewoonde_*`, `niet_bewoonde_*`, `nieuwe_woning`, `onbebouwde_*`, `*_eigendom_overheid`) wordt eerst:
     - `waarde(jaar+1) = waarde(jaar)`
   - Hierdoor start `jaar+1` als kopie van de huidige toestand.

2. **Sequentieel toepassen van alle flows voor die zone**
   - Voor elke `FlowRule`:
     - lees `inflow_stock_name`, `outflow_stock_name`
     - lees `flow_rate` (baseline of active) en `flow_mode` (`transfer` of `growth`)
     - lees de **huidige werkwaarden** in `jaar+1`:
       - `future_inflow_stock_value`
       - `future_outflow_stock_value`

#### Waarom de absolute flow op `future_inflow_stock_value` wordt berekend

Absolute hoeveelheid wordt berekend op basis van de reeds opgebouwde waarde in `jaar+1`:

- `flow_absolute = future_inflow_stock_value * flow_rate`

Dit is belangrijk omdat flows binnen hetzelfde jaar elkaar beïnvloeden.  
Bijvoorbeeld: `nieuwe_woning` kan eerst toenemen door eerdere flows, en moet later in datzelfde jaar kunnen afnemen door `isolatievoorschriften_nieuwbouw_*`.

#### Updatevergelijkingen per flow-stap

Voor elke flow-stap worden de nieuwe waarden afhankelijk van `flow_mode`:

- `transfer`: `inflow -= flow_absolute`, `outflow += flow_absolute`
- `growth`: `inflow += flow_absolute` (outflow blijft ongewijzigd)

Bescherming:
- Als `future_inflow_stock_value < 0`, wordt een `ValueError` gegooid.

Daarna worden beide waarden teruggeschreven in de state-array voor `jaar+1`.

### Logging in `flow_log.csv`

Per flow-stap wordt één logregel toegevoegd met o.a.:

- `flow_rate` = gebruikte rate voor deze regel (baseline of active)
- `flow_mode` = `transfer` of `growth`
- `orig_future_inflow_stock_value` = inflow-waarde vóór de stap
- `new_future_inflow_stock_value` = inflow-waarde na de stap
- `orig_future_outflow_stock_value` = outflow-waarde vóór de stap
- `new_future_outflow_stock_value` = outflow-waarde na de stap
- `delta_inflow = new_future_inflow_stock_value - orig_future_inflow_stock_value`
- `delta_outflow = new_future_outflow_stock_value - orig_future_outflow_stock_value`

Interpretatie:
- bij `transfer`: `delta_inflow` meestal negatief, `delta_outflow` meestal positief
- bij `growth`: `delta_inflow` meestal positief

### Aggregatie naar `flow_log_zone.csv`

Na het wegschrijven van `flow_log.csv` wordt `flow_log_zone.csv` gemaakt:

- Mapping gebeurt via het gekozen zones-bestand (`input/lden_zones.csv` of `input/lnight_zones.csv`).
- Groepering gebeurt op:
  - `zone`, `jaar`, `naam_flow`, `inflow_stock_name`, `outflow_stock_name`
- Numerieke velden (`orig/new/delta`) worden gesommeerd.

