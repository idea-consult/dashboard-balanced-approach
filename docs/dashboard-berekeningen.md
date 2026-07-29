# Dashboard-berekeningen

Hoe de Streamlit-simulator van maatregelkeuze naar KPI’s en grafieken komt.

[← Terug naar README](../readme.md)

---

## Overzicht

1. Gebruiker selecteert per maatregel zones **A–F** of één overlay (**Lnight45** / **NA70**).
2. De engine bouwt per 1 dB-band `FlowRule`s met een **activation weight** ∈ [0, 1].
3. Per simulatiejaar: stocks kopiëren naar jaar+1, daarna alle flows sequentieel toepassen.
4. Afgeleide metrics (ernstig gehinderden, …) en kosten; resultaten naar `output/` en grafieken.

Horizon: `BEGINJAAR` … `EINDJAAR` in [`config.py`](../config.py) (standaard 2026 + looptijd).

---

## Selectie → activatie

| UI-keuze | `activation_weight` per band |
|----------|------------------------------|
| Zone bevat de band (A–F) | `1.0` |
| Overlay Lnight45 of NA70 | `share_*` van die band (0–1) |
| Niets | `0.0` |

Effectieve flow-rate:

```text
rate = baseline + weight × (active_rate − baseline)
```

- `weight = 0` → enkel baseline (geen maatregelkost)
- `weight = 1` → volle active rate
- `weight = 0.22` (bv. deels zone E in Lnight45) → gewogen mix

### Kosten

Wanneer `weight > 0`:

```text
kostvolume = |flow_rate_baseline − flow_rate_effectief| × beschikbare_inflow_stock
rijkost    = kostvolume × eenheidsprijs(kost_stock)
overheid  += rijkost × rel_cost_overheid
privé     += rijkost × rel_cost_prive
```

- **Aankoop / isolatie** (`baseline ≈ 0`, `active > 0`): kostvolume ≈ werkelijke outflow.
- **Verbod** (`baseline > 0`, `active = 0`): kostvolume = verhinderde eenheden (bv. planschade woningverbod).
- Factoren en `kost_stock` staan in `input/measure_costs.csv`; eenheidsprijzen in `stock_prices.csv`.

A–F en overlays zijn **wederzijds uitsluitend** in de UI; zie [Overlays](overlays-lnight45-na70.md).

---

## Simulatiestap per jaar

Voor elke band (of legacy: zone) en elk jaar:

### 1. Carry-over

Alle stocks: `waarde(jaar+1) = waarde(jaar)`.

### 2. Flows toepassen

Voor elke `FlowRule` (gesorteerd op `priority`):

```text
flow_absolute = future_inflow_stock_value × flow_rate
```

De absolute hoeveelheid gebruikt de **reeds bijgewerkte** waarde in jaar+1, zodat flows binnen hetzelfde jaar elkaar beïnvloeden (bv. eerst nieuwbouw, daarna isolatievoorschriften op `nieuwe_woning`).

| `flow_mode` | Update |
|-------------|--------|
| `transfer` | inflow −= flow_absolute, outflow += flow_absolute |
| `growth` | inflow += flow_absolute (outflow ongewijzigd als het dezelfde stock is) |

Regels komen uit `flow_rules.csv` + kosten uit `measure_costs.csv`. Per-band rates komen bij voorkeur uit `flow_size.csv` (`*_baseline` / `*_active`).

Regionale stocks: elke regel wordt parallel toegepast op `_vlaanderen` en `_brussel` als die kolommen bestaan.

---

## Logging

Per flow-stap een regel in `flow_log.csv` met o.a.:

- `flow_rate`, `flow_mode`, `maatregel_toegepast`
- oorspronkelijke en nieuwe inflow/outflow-waarden
- `delta_inflow`, `delta_outflow`

Daarna aggregatie naar `flow_log_zone.csv` op zone × jaar × flow (sommen van numerieke delta’s).

---

## Afgeleide KPI’s

Na (of tijdens) flush naar zone-niveau:

| KPI | Idee |
|-----|------|
| **Ernstig gehinderden** | Woningen × inwoners/huis × dosis-effectrelatie (per regio) |
| **Leefbaarheidspunten** | Inwoners × zonegewichten (geïsoleerd / niet-geïsoleerd; UI kan defaults overschrijven) |
| **Kosten** | `\|baseline−effectief\| × stock × eenheidsprijs × rel_cost`; verboden = verhinderde eenheden; alleen bij actieve maatregel |

Totale KPI’s over A–F mogen worden opgeteld (zones zijn exclusief). Overlay-KPI’s in de UI zijn **gewogen** met dekking en mogen **niet** bij A–F worden opgeteld.

---

## Visualisaties

- Staafgrafieken A–F: beginjaar vs eindjaar, vaak Vlaanderen/Brussel gestapeld
- Apart blok overlays Lnight45 / NA70
- Expander met % dekking per zone A–F
- Tijdreeksen van stocks per zone

---

## Gerelateerd

- [Data-structuur](data-structuur.md)
- [Terminologie](terminologie.md)
- [Maatregelen toevoegen](maatregelen-toevoegen.md)
