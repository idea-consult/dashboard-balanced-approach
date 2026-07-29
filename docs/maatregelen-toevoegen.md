# Maatregelen toevoegen

Checklist om een nieuwe maatregel in het dashboard te configureren zonder codewijziging (tenzij je nieuwe stocks of UI-logica nodig hebt).

[← Terug naar README](../readme.md)

---

## 1. Catalogus — `input/measures.csv`

Voeg een rij toe met minstens:

| Kolom | Vereist | Opmerking |
|-------|---------|-----------|
| `measure_id` | ja | Unieke technische sleutel (snake_case) |
| `naam_mooi` | ja | Label in de sidebar |
| `help` | ja | Markdown-tooltip |
| `priority` | ja | Lager = eerder in de sidebar |
| `hidden_in_ui` | nee | `TRUE` = verbergen |
| `group_id` | nee | Zelfde id (≥2 maatregelen) → gedeelde zone-selector |

---

## 2. Flowregels — `input/flow_rules.csv`

Per effect van de maatregel één (of meer) regels:

| Kolom | Betekenis |
|-------|-----------|
| `rule_id` | Uniek |
| `measure_id` | Koppeling naar `measures.csv` |
| `inflow_stock` / `outflow_stock` | Geldige simulatiestocknamen |
| `flow_rate_baseline` / `flow_rate_active` | Defaults; bandwaarden uit `flow_size` overschrijven waar aanwezig |
| `flow_mode` | `transfer` of `growth` |
| `priority` | Volgorde binnen het jaar (lager = eerder) |

Bekende stocks o.a.:  
`bewoonde_niet_geïsoleerde_woning`, `bewoonde_geïsoleerde_woning`, `nieuwe_woning`,  
`onbebouwde_bebouwbare_percelen`, `onbebouwde_onbebouwbare_percelen`,  
`perceel_eigendom_overheid`, `woning_eigendom_overheid`.

---

## 3. Kosten — `input/measure_costs.csv`

| Kolom | Betekenis |
|-------|-----------|
| `measure_id` | Zelfde id |
| `rel_cost_overheid` / `rel_cost_prive` | Vermenigvuldigers op rijkost |
| `kost_stock` | Stock voor eenheidsprijs, of `-` / leeg voor geen kost |

---

## 4. Band-rates — `input/flow_size.csv` (aanbevolen)

Voor realistische per-dB-rates: in `contour_analyse_2.py` kolommen  
`{prefix}_baseline` en `{prefix}_active` berekenen en exporteren.

Mapping uitzondering: maatregel `verkavelingsverbod` ↔ kolomprefix `verkavelings_verbod`  
(zie `MEASURE_ID_TO_FLOW_COLUMN` in `models/lden_data_loader.py`).

---

## 5. Incompatibele combinaties

Als twee maatregelen niet samen op dezelfde zone mogen: voeg een tupel toe in  
`models/validation.py` → `INCOMPATIBLE_MEASURES`.

Validatie houdt ook rekening met **overlay-dekking** (zelfde zone via Lnight45/NA70).

---

## 6. Scenario-presets — `input/scenarios.csv`

Bovenaan de sidebar staan vier scenario’s (plus **Geen**). Eén rij per maatregel per scenario:

```csv
scenario_id,scenario_label,priority,measure_id,zones,overlay
minimaal,Minimaal ambitieniveau,1,woongebiedverbod,A;B;C,
kleine_nachtzone,Studie hoger ruimtelijk rendement + kleinste nachtzone,3,woongebiedverbod,,lnight45
```

| Kolom | Regel |
|-------|--------|
| `zones` | `A;B;C` of leeg |
| `overlay` | leeg / `lnight45` / `na70` (niet combineren met zones) |

Rijen met lege `measure_id` definiëren alleen het scenario-label. Bij kiezen van een scenario worden alle knoppen gereset en daarna de CSV-selecties gezet. Handmatig bijsturen zet het scenario terug op **Geen**.

---

## 7. Controleren

1. App herstarten / pagina verversen — maatregel verschijnt in de sidebar.
2. Zone of overlay selecteren → simulatie loopt zonder importfouten.
3. Eventueel: `uv run pytest tests/test_measure_selection_manager.py`

---

## Gerelateerd

- [Dashboard-berekeningen](dashboard-berekeningen.md)
- [Data-structuur](data-structuur.md)
- [Architectuur](architectuur.md)
- [Scenario’s](scenarios.md)