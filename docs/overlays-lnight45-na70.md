# Overlays Lnight45 en NA70

Uitleg van de twee **overlappende** contouren op het Lden-dashboard: data, selectie, rekenmodel en visualisaties.

[← Terug naar README](../readme.md)

---

## Waarom apart van A–F?

Zones **A–F** verdelen de Lden-as in mutueel exclusieve 5 dB-buckets.  
**Lnight45** en **NA70** zijn geografische overlays: een deel van elke Lden-intersectie kan (deels) in die contouren liggen. Daardoor overlappen ze met A–F — en deels met elkaar.

Typische dekking (inwoners × oppervlakte-%):

| Zone | Lnight45 | NA70 |
|------|----------|------|
| A–B | ~100% | ~100% |
| C | ~100% | ~91% |
| D | ~100% | ~13% |
| E | ~22% | ~0% |
| F | ~0% | ~0% |

Een maatregel “in zone A én Lnight45” zou A dubbel meetellen. Daarom is de UI **wederzijds uitsluitend**.

---

## Data

Bron: `data_1/intersection lden avec lnight45 et NA70 final.csv`  
Join in `contour_analyse_1.py` op `id_inter_ss_lden`.

Per intersectie o.a.:

- `pct_lnight45`, `pct_na70` (0–100)
- gewogen kolommen `inwoners_lnight45`, …

Per 1 dB-band in `flow_size.csv`:

- `share_lnight45`, `share_na70` ∈ [0, 1]  
  (inwonersgewogen; oppervlakte-fallback als er geen inwoners zijn)

---

## UI-regels

Per maatregel:

```text
[ A ] [ B ] [ C ] [ D ] [ E ] [ F ]    ☐ Lnight45   ☐ NA70
```

1. Ofwel één of meer zones A–F, ofwel exact één overlay — niet beide.
2. Maximaal één overlay tegelijk (Lnight45 XOR NA70).
3. Overlay aan → A–F disabled; A–F aan → overlays disabled.

Implementatie: `ui/components.py` + `MeasureSelectionManager.set_selected_overlay`.

---

## Rekenmodel

Per band:

```text
rate = baseline + share × (active − baseline)
```

Gevolg: Lnight45 ≈ volle A–D + fractioneel E; NA70 ≈ A–B + fractioneel C/D.  
Effecten verschijnen nog steeds in de A–F-aggregatie (simulatie blijft per band). Het **totaal** over A–F blijft zonder double count.

Zie [Dashboard-berekeningen](dashboard-berekeningen.md).

---

## Visualisaties

| Blok | Doel |
|------|------|
| Grafiek A–F | Exclusieve zones; som = totaal |
| Sectie “Overlappende contouren” | Lnight45 en NA70 **apart**; waarschuwing: niet optellen bij A–F of bij elkaar |
| Expander “Dekking” | % van zone-inwoners in elke overlay |

---

## Gerelateerd

- [Data-structuur](data-structuur.md)
- [Terminologie](terminologie.md)
