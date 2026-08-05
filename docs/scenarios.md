# Scenario-presets

Bovenaan de sidebar kun je één van de beleidsscenario’s kiezen. Dat zet automatisch de juiste maatregel-zones of overlays aan, volgens [`input/scenarios.csv`](../input/scenarios.csv).

[← Terug naar README](../readme.md)

---

## Gedrag

- Exact **één** scenario tegelijk (of **Geen**).
- Kiezen van een scenario: alle selecties wissen → CSV toepassen.
- Daarna handmatig bijsturen mag; de scenario-keuze springt terug naar **Geen**.

---

## CSV-formaat

```csv
scenario_id,scenario_label,priority,measure_id,zones,overlay
minimaal,Minimaal ambitieniveau,1,woongebiedverbod,A;B;C,
kleine_nachtzone,Studie hoger ruimtelijk rendement + kleinste nachtzone,3,woongebiedverbod,,lnight45
```

| Kolom | Betekenis |
|-------|-----------|
| `scenario_id` | Stabiele sleutel (`minimaal`, `hoger_ruimtelijk_rendement`, …) |
| `scenario_label` | Tekst in de radio |
| `priority` | Volgorde in de UI |
| `measure_id` | Bestaande id uit `measures.csv` (leeg = alleen label definiëren) |
| `zones` | `A;B;C` of leeg |
| `overlay` | leeg / `lnight45` / `na70` |

Niet beide `zones` en `overlay` op dezelfde rij zetten.

Standaardscenario’s in de repo:

1. Minimaal ambitieniveau  
2. Studie hoger ruimtelijk rendement  
3. Studie hoger ruimtelijk rendement + kleinste nachtzone  
4. Maximaal ambitieniveau  
5. Scenario IDEA  

Vul zelf de maatregelrijen in (vertaling vanuit de opdrachtgever-tabel naar dashboard-`measure_id`s).

---

## Code

- `models/scenario_manager.py` — laden en valideren  
- `ui/components.py` — radio bovenaan de sidebar  

---

## Gerelateerd

- [Maatregelen toevoegen](maatregelen-toevoegen.md)
- [Overlays Lnight45 / NA70](overlays-lnight45-na70.md)
