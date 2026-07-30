# Terminologie

Korte definities van begrippen die in data, code en UI voorkomen.

[← Terug naar README](../readme.md)

---

## Ruimte en geluid

| Term | Betekenis |
|------|-----------|
| **Contour** | Ruimtelijke geluidsband rond de luchthaven, hier op **1 dB** (Lden). |
| **Lden** | Day-evening-night equivalent geluidsniveau; hoofddashboard-contour. |
| **Lnight** | Nachtcontour; apart dashboard is (nog) niet actief. |
| **Intersectie** | Overlap van een **statistische sector** met één Lden-contourband. |
| **Zone A–F** | 5 dB-groep van Lden-banden (A = 70–75 … F = 45–50). **Mutueel exclusief**: iemand in A zit niet in B. |
| **Lnight45** | Overlay: deel van de Lden-intersectie dat ook in Lnight ≥ 45 dB ligt. Overlapt met A–F. |
| **NA70** | Overlay: deel van de Lden-intersectie in de NA70-contour. Overlapt met A–F (en deels met Lnight45). |
| **Share** | Inwoners- (of oppervlakte-)aandeel van een 1 dB-band dat in een overlay ligt (`share_lnight45`, `share_na70`). |

---

## Stocks en flows

| Term | Betekenis |
|------|-----------|
| **Stock** | Voorraadgrootheid in het model (woningen, percelen, overheidseigendom, …). |
| **Flow** | Jaarlijkse overgang tussen stocks: `Flow = stock_inflow × rate`. |
| **Flow rate** | Jaarlijks aandeel van de inflow-stock (0–1). |
| **Baseline** | Rate **zonder** geactiveerde maatregel in die zone/overlay. |
| **Active** | Rate **met** geactiveerde maatregel. |
| **Transfer** | Verschuiving: uit inflow-stock, naar outflow-stock. |
| **Growth** | Groei (of krimp) op dezelfde stock (inflow = outflow-naam). |
| **Activation weight** | Fractie waarmee de active rate wordt gemengd (1 voor volle zone, share voor overlay). |

---

## Maatregelen en UI

| Term | Betekenis |
|------|-----------|
| **Maatregel** | Beleidsinstrument in `measures.csv` (`measure_id`, weergavenaam `naam_mooi`). |
| **Flow rule** | Eén regel in `flow_rules.csv` die een maatregel koppelt aan stocks en modes. |
| **Group** | Meerdere maatregelen met dezelfde `group_id` delen één zone-selector. |
| **Hidden** | `hidden_in_ui = TRUE`: niet in de sidebar, wel in de simulatieconfiguratie. |

---

## Impact en regio

| Term | Betekenis |
|------|-----------|
| **Ernstig gehinderden** | KPI: inwoners/woningen × dosis-effectrelatie (vaak opgesplitst Vlaanderen / Brussel). |
| **Dosis-effectrelatie** | Factor per dB-band die hinderkans weergeeft. |
| **Vlaanderen / Brussel** | Regionale laag van stocks en KPI’s (`*_vlaanderen`, `*_brussel`). |

---

## Gerelateerd

- [Data-structuur](data-structuur.md)
- [Dashboard-berekeningen](dashboard-berekeningen.md)
- [Overlays Lnight45 / NA70](overlays-lnight45-na70.md)
