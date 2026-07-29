# Maatregelen en stocks

Uitgebreide referentiepagina voor alle maatregelen en simulatiestocks in het dashboard.

[← Terug naar README](../readme.md)

---

## Bronnen

- **Maatregelen** komen uit `input/measures.csv`. De beschrijvingen hieronder zijn overgenomen en licht geordend op basis van de `help`-kolom, plus metadata zoals `measure_id`, `priority`, `group_id` en `hidden_in_ui`.
- **Stocks** zijn afgeleid uit de stockkolommen in `input/stocks.csv`, de actieve simulatienamen in `models/stock_manager.py` en de toelichting in `contour_analyse_1.py`.
- **Modelkosten** staan in `input/measure_costs.csv`; zie [Dashboard-berekeningen](dashboard-berekeningen.md) voor de formule.

---

## Modelkosten (samenvatting)

Formule bij actieve maatregel: `|baseline − effectief| × stock × eenheidsprijs × rel_cost`.

| Maatregel(groep) | Overheid | Privé | Eenheidsprijs |
|------------------|----------|-------|---------------|
| Verkavelingsverbod, woongebiedverbod, verbod kwetsbare groepen | 0 | 0 | — |
| Aankoop / voorkoop percelen of woningen | 1,00 | 0 | perceel of woning |
| Onteigening percelen of woningen | 1,50 | 0 | perceel of woning |
| Woningverbod | 1,00 (verhinderde nieuwbouw) | 0 | perceel (planschade) |
| Woonverdichtingsverbod | 1,00 (verhinderde verdichting) | 0 | woning |
| Isolatievoorschriften nieuwbouw → geïsoleerd | 0 | 0,10 | woning |
| Renovatie zonder / verplicht isoleren | 0 | 0,20 | woning |
| Gesubsidieerd isolatieprogramma | 0,10 | 0,10 | woning |
| Gestuurd isolatieprogramma | 0,15 (= 3/20) | 0 | woning |
| Aanleg geluidsbuffers | 0 (open) | 0 | — |

---

## Simulatiestocks

### `onbebouwde_bebouwbare_percelen`

- **Betekenis:** onbebouwde percelen die in het model als bebouwbaar beschouwd worden.
- **Bron in de pipeline:** in `contour_analyse_1.py` rechtstreeks afgeleid van `aantal_percelen_onbebouwd_woongebied`.
- **Rol in de simulatie:** instroom- of uitgangsstock voor maatregelen zoals `verkavelingsverbod`, `aankoopbeleid_percelen`, `voorkooprecht_percelen`, `onteigening_percelen` en nieuwbouwverboden.
- **Gebruik in flows:** deze stock kan gelijk blijven, krimpen door overheidstussenkomst, of doorstromen naar `nieuwe_woning`.

### `onbebouwde_onbebouwbare_percelen`

- **Betekenis:** onbebouwde percelen die niet bebouwbaar zijn.
- **Bron in de pipeline:** in `contour_analyse_1.py` momenteel als werkhypothese opgebouwd als `aantal_percelen_onbebouwd_woongebied × 3`.
- **Rol in de simulatie:** tegenhanger van `onbebouwde_bebouwbare_percelen` voor maatregelen rond woongebiedaanduiding.
- **Gebruik in flows:** bij `woongebiedverbod` verschuift deze stock conceptueel ten opzichte van de bebouwbare percelenstock.
- **Opmerking:** dit is expliciet een placeholderbenadering tot er een betere bron per contourband beschikbaar is.

### `bewoonde_niet_geïsoleerde_woning`

- **Betekenis:** bewoonde woningen zonder akoestische isolatie.
- **Bron in de pipeline:** in `contour_analyse_1.py` afgeleid uit `aantal_woningen` met een gewestaanname voor het aandeel niet-geïsoleerde woningen.
- **Rol in de simulatie:** cruciale stock voor hindervermindering en isolatiemaatregelen.
- **Gebruik in flows:** vertrekstock voor aankoopbeleid, voorkooprecht, onteigening, renovatie-isolatie en geluidsbuffers.
- **Interpretatie:** dit is de groep woningen waarvoor bijkomend beleid het meeste verschil maakt in hinderreductie of binnencomfort.

### `bewoonde_geïsoleerde_woning`

- **Betekenis:** bewoonde woningen met akoestische isolatie.
- **Bron in de pipeline:** in `contour_analyse_1.py` afgeleid uit `aantal_woningen` met een gewestaanname voor het aandeel geïsoleerde woningen.
- **Rol in de simulatie:** eindstock voor nieuwbouw- en renovatiemaatregelen die isolatie opleveren.
- **Gebruik in flows:** bestemming van `nieuwe_woning` bij conforme nieuwbouw, en bestemming van renovatie- of isolatiestromen vanuit niet-geïsoleerde woningen.

### `nieuwe_woning`

- **Betekenis:** tussentijdse stock voor nieuwbouwwoningen voordat ze in de bewoonde woningstocks landen.
- **Bron in de pipeline:** in `contour_analyse_1.py` initieel op `0` gezet voor alle intersecties.
- **Rol in de simulatie:** tijdelijke simulatorstock voor nieuwbouwflows.
- **Gebruik in flows:** nieuwe woningen ontstaan vanuit `onbebouwde_bebouwbare_percelen` en stromen daarna door naar `bewoonde_niet_geïsoleerde_woning` of `bewoonde_geïsoleerde_woning`.

### `perceel_eigendom_overheid`

- **Betekenis:** percelen die in overheidseigendom terechtkomen.
- **Bron in de pipeline:** in `contour_analyse_1.py` initieel op `0`; het is een interne simulatorstock.
- **Rol in de simulatie:** doelstock voor beleidsingrepen op percelen.
- **Gebruik in flows:** bestemming van aankoopbeleid, voorkooprecht en onteigening van bebouwbare percelen.

### `woning_eigendom_overheid`

- **Betekenis:** woningen die in overheidseigendom terechtkomen.
- **Bron in de pipeline:** in `contour_analyse_1.py` initieel op `0`; ook dit is een interne simulatorstock.
- **Rol in de simulatie:** doelstock voor beleidsingrepen op woningen.
- **Gebruik in flows:** bestemming van aankoopbeleid, voorkooprecht en onteigening van woningen.

### `niet_bewoonde_geïsoleerde_woning`

- **Betekenis:** niet-bewoonde maar geïsoleerde woningen.
- **Status in huidige dataflow:** deze stocknaam staat nog in `models/stock_manager.py` als vereiste/legacy simulatienaam, maar komt niet meer als actieve kolom voor in de huidige `input/stocks.csv`.
- **Rol:** vooral relevant voor achterwaartse compatibiliteit met oudere stockexports.
- **Opmerking:** er lijken momenteel geen actieve dashboardflows op deze stock te lopen.

### `niet_bewoonde_niet_geïsoleerde_woning`

- **Betekenis:** niet-bewoonde, niet-geïsoleerde woningen.
- **Status in huidige dataflow:** net als de vorige stock nog aanwezig als legacy simulatienaam in `models/stock_manager.py`, maar niet actief in de huidige `input/stocks.csv`.
- **Rol:** compatibiliteit met oudere exports.
- **Opmerking:** in de actuele Lden-flowschema's speelt deze stock geen actieve rol.

---

## Tooltip-flowlogica per maatregel

Deze samenvatting dekt het deel van de maatregeltooltips dat in de app dynamisch wordt aangevuld met simulatieflow-informatie.

- `verkavelingsverbod`: geen gemodelleerde stock-transfer; maatregel staat vooral in de configuratie voor beleids- en kostencatalogus.
- `woongebiedverbod`: verschuiving tussen `onbebouwde_onbebouwbare_percelen` en `onbebouwde_bebouwbare_percelen`.
- `aankoopbeleid_percelen`: `onbebouwde_bebouwbare_percelen -> perceel_eigendom_overheid`.
- `voorkooprecht_percelen`: `onbebouwde_bebouwbare_percelen -> perceel_eigendom_overheid`.
- `onteigening_percelen`: `onbebouwde_bebouwbare_percelen -> perceel_eigendom_overheid`.
- `woningverbod`: transfer `onbebouwde_bebouwbare_percelen -> nieuwe_woning`; baseline = gedeelde nieuwbouwrate, active = 0.
- `verbod_kwetsbare_groep`: beperkt projecttoewijzing vanuit `onbebouwde_bebouwbare_percelen`; de maatregel gebruikt vergunningen voor kwetsbare functies als indicator.
- `woonverdichtingsverbod_niet_geïsoleerde_woningen`: growth op `bewoonde_niet_geïsoleerde_woning` met dezelfde gedeelde nieuwbouwrate als `woningverbod`.
- `woonverdichtingsverbod_geïsoleerde_woningen`: growth op `bewoonde_geïsoleerde_woning` met dezelfde gedeelde nieuwbouwrate.
- `aankoopbeleid_niet_geïsoleerde_woningen`: `bewoonde_niet_geïsoleerde_woning -> woning_eigendom_overheid`.
- `aankoopbeleid_geïsoleerde_woningen`: `bewoonde_geïsoleerde_woning -> woning_eigendom_overheid`.
- `voorkooprecht_niet_geïsoleerde_woningen`: `bewoonde_niet_geïsoleerde_woning -> woning_eigendom_overheid`.
- `voorkooprecht_geïsoleerde_woningen`: `bewoonde_geïsoleerde_woning -> woning_eigendom_overheid`.
- `onteigening_niet_geïsoleerde_woningen`: `bewoonde_niet_geïsoleerde_woning -> woning_eigendom_overheid`.
- `onteigening_geïsoleerde_woningen`: `bewoonde_geïsoleerde_woning -> woning_eigendom_overheid`.
- `isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning`: `nieuwe_woning -> bewoonde_niet_geïsoleerde_woning` voor het deel nieuwbouw dat niet aan de norm voldoet.
- `isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning`: `nieuwe_woning -> bewoonde_geïsoleerde_woning` voor conforme nieuwbouw.
- `renovatie_zonder_maatregel`: referentiestroom `bewoonde_niet_geïsoleerde_woning -> bewoonde_geïsoleerde_woning`.
- `verplicht_isoleren_renovatie`: versterkte renovatiestroom `bewoonde_niet_geïsoleerde_woning -> bewoonde_geïsoleerde_woning`.
- `gesubsidieerd_isolatieprogramma`: idem, maar met hogere beleidsintensiteit.
- `gestuurd_isolatieprogramma`: idem, met de sterkste beleidsintensiteit van de isolatiemaatregelen.
- `aanleg_geluidsbuffers`: nog geen gekwantificeerd stock-effect; modelkost open.
- `compensatie_*` / soft measures: verwijderd uit de actieve configuratie.

---

## Maatregelen

De volgorde hieronder volgt de `priority` uit `input/measures.csv`.

### Verkavelingsverbod

- `measure_id`: `verkavelingsverbod`
- `priority`: `1`
- `hidden_in_ui`: `false`

#### Uitleg
Bij een verkavelingsverbod is het verboden om percelen op te splitsen in meerdere percelen.

#### Beoogd effect
Doordat er minder percelen zijn door het toepassen van deze maatregel wil men verhinderen dat er meer woningen gebouwd worden.

#### Type maatregel
bijkomende gehinderde personen vermijden

#### Instrument en kosten
- **Instrument:** Gewestelijk RUP/Decreetswijziging/Stedenbouwkundige verordening
- **Modelkost:** 0 (geen modelkost in dashboard)
- **Administratieve kost:** regulier beleid
- **Koststock:** -

### Verbod op het aanduiden van woongebied

- `measure_id`: `woongebiedverbod`
- `priority`: `2`
- `hidden_in_ui`: `false`

#### Uitleg
Bij een woongebiedverbod kiest de overheid ervoor om geen woongebied meer aan te duiden voor bepaalde zones.

#### Beoogd effect
Doordat er geen extra percelen bebouwbaar worden gemaakt, wil men bijkomende woningen voorkomen.

#### Type maatregel
bijkomende gehinderde personen vermijden

#### Instrument en kosten
- **Instrument:** Gewestelijk RUP/Decreetswijziging
- **Modelkost:** 0 (geen modelkost in dashboard)
- **Administratieve kost:** regulier beleid
- **Koststock:** -

### Aankoopbeleid van percelen

- `measure_id`: `aankoopbeleid_percelen`
- `priority`: `3`
- `hidden_in_ui`: `false`

#### Uitleg
Hierbij worden onbebouwde percelen opgekocht wanneer deze publiek beschikbaar zijn op de markt.

#### Beoogd effect
Doordat er bebouwbare percelen worden opgekocht, wordt vermeden dat er meer gebouwd wordt.

#### Type maatregel
bijkomende gehinderde personen vermijden

#### Instrument en kosten
- **Instrument:** VLM Grondenbank
- **Modelkost (overheid):** `1,00 x` eenheidsprijs bebouwbaar perceel
- **Administratieve kost:** regulier beleid, als het kan
- **Koststock:** `onbebouwde_bebouwbare_percelen`

### Voorkooprecht op percelen

- `measure_id`: `voorkooprecht_percelen`
- `priority`: `4`
- `hidden_in_ui`: `false`

#### Uitleg
Hierbij worden onbebouwde percelen opgekocht via voorkooprecht wanneer deze doorverkocht worden.

#### Beoogd effect
Doordat er bebouwbare percelen worden opgekocht, wordt vermeden dat er meer gebouwd wordt.

#### Type maatregel
bijkomende gehinderde personen vermijden

#### Instrument en kosten
- **Instrument:** decretaal voorkooprecht
- **Modelkost (overheid):** `1,00 x` eenheidsprijs bebouwbaar perceel
- **Administratieve kost:** regulier beleid
- **Koststock:** `onbebouwde_bebouwbare_percelen`

### Onteigenen van percelen

- `measure_id`: `onteigening_percelen`
- `priority`: `5`
- `hidden_in_ui`: `false`

#### Uitleg
Hierbij worden onbebouwde percelen onteigend.

#### Beoogd effect
Doordat er minder percelen zijn door het toepassen van deze maatregel wil men verhinderen dat er meer woningen gebouwd worden.

#### Type maatregel
bijkomende gehinderde personen vermijden

#### Instrument en kosten
- **Instrument:** decretale basis of opdracht om te onteigenen
- **Modelkost (overheid):** `1,50 x` eenheidsprijs bebouwbaar perceel
- **Administratieve kost:** organiseren onteigening
- **Koststock:** `onbebouwde_bebouwbare_percelen`

### Verbod op bouwen van nieuwe woningen op onbebouwde percelen

- `measure_id`: `woningverbod`
- `priority`: `6`
- `hidden_in_ui`: `false`

#### Uitleg
Op onbebouwde (bebouwbare) percelen mogen geen nieuwe woningen meer gebouwd worden.
Baseline-rate = nieuwbouw / (woningen + bebouwbare percelen), gelijk aan woonverdichting; active = 0.

#### Beoogd effect
Doordat er minder woningen gebouwd mogen worden, wil men verhinderen dat er meer inwoners op plaatsen komen wonen waar er veel geluidshinder is.

#### Type maatregel
bijkomende gehinderde personen vermijden

#### Instrument en kosten
- **Instrument:** Gewestelijk GRUP, bouwverbod
- **Modelkost (overheid):** planschade = verhinderde nieuwbouw x eenheidsprijs bebouwbaar perceel
- **Administratieve kost:** regulier beleid
- **Koststock:** `onbebouwde_bebouwbare_percelen`

### Verbod op bijkomende kwetsbare groepen

- `measure_id`: `verbod_kwetsbare_groep`
- `priority`: `8`
- `hidden_in_ui`: `false`

#### Uitleg
Gebouwen die voor kwetsbare groepen bedoeld zijn mogen niet meer gebouwd worden (bijv. scholen).

#### Beoogd effect
Doordat er minder projecten gebouwd mogen worden, wil men verhinderen dat er meer kwetsbare groepen op plaatsen komen wonen waar er veel geluidshinder is.

#### Type maatregel
bijkomende gehinderde personen vermijden

#### Instrument en kosten
- **Instrument:** stedenbouwkundige verordening/exploitatievergunning
- **Modelkost:** 0 (geen modelkost in dashboard)
- **Administratieve kost:** regulier beleid
- **Koststock:** -

### Woonverdichtingsverbod niet-geïsoleerde woningen

- `measure_id`: `woonverdichtingsverbod_niet_geïsoleerde_woningen`
- `priority`: `9`
- `hidden_in_ui`: `false`

#### Uitleg
Het is verboden om woningen op te splitsen in meerdere woningen (growth op niet-geïsoleerde stock).
Zelfde baseline-rate als `woningverbod`; active = 0.

#### Beoogd effect
Doordat er minder woonunits worden gecreëerd, wil men verhinderen dat er meer inwoners zich vestigen waar er veel geluidshinder is.

#### Type maatregel
bijkomende gehinderde personen vermijden

#### Instrument en kosten
- **Instrument:** RUP
- **Modelkost (overheid):** verhinderde verdichting x eenheidsprijs woning
- **Administratieve kost:** regulier beleid
- **Koststock:** `bewoonde_niet_geïsoleerde_woning`

### Woonverdichtingsverbod geïsoleerde woningen

- `measure_id`: `woonverdichtingsverbod_geïsoleerde_woningen`
- `priority`: `10`
- `hidden_in_ui`: `false`

#### Uitleg
Het is verboden om woningen op te splitsen in meerdere woningen (growth op geïsoleerde stock).
Zelfde baseline-rate als `woningverbod`; active = 0.

#### Beoogd effect
Doordat er minder woonunits worden gecreëerd, wil men verhinderen dat er meer inwoners zich vestigen waar er veel geluidshinder is.

#### Type maatregel
bijkomende gehinderde personen vermijden

#### Instrument en kosten
- **Instrument:** RUP
- **Modelkost (overheid):** verhinderde verdichting x eenheidsprijs woning
- **Administratieve kost:** regulier beleid
- **Koststock:** `bewoonde_geïsoleerde_woning`

### Aankoopbeleid niet-geïsoleerde woningen

- `measure_id`: `aankoopbeleid_niet_geïsoleerde_woningen`
- `priority`: `11`
- `hidden_in_ui`: `false`
- `group_id`: `aankoopbeleid_woningen`

#### Uitleg
Hierbij worden woningen opgekocht wanneer deze publiek beschikbaar zijn op de markt.

#### Beoogd effect
Doordat er woningen worden opgekocht, wordt er vermeden dat er inwoners zich vestigen op een plaats waar er veel geluidshinder is.

#### Type maatregel
aantal gehinderde personen verminderen

#### Instrument en kosten
- **Instrument:** VLM Grondenbank
- **Modelkost (overheid):** `1,00 x` eenheidsprijs woning
- **Administratieve kost:** regulier beleid, als het kan
- **Koststock:** `bewoonde_niet_geïsoleerde_woning`

### Aankoopbeleid geïsoleerde woningen

- `measure_id`: `aankoopbeleid_geïsoleerde_woningen`
- `priority`: `12`
- `hidden_in_ui`: `false`
- `group_id`: `aankoopbeleid_woningen`

#### Uitleg
Hierbij worden woningen opgekocht wanneer deze publiek beschikbaar zijn op de markt.

#### Beoogd effect
Doordat er woningen worden opgekocht, wordt er vermeden dat er inwoners zich vestigen op een plaats waar er veel geluidshinder is.

#### Type maatregel
aantal gehinderde personen verminderen

#### Instrument en kosten
- **Instrument:** VLM Grondenbank
- **Modelkost (overheid):** `1,00 x` eenheidsprijs woning
- **Administratieve kost:** regulier beleid, als het kan
- **Koststock:** `bewoonde_geïsoleerde_woning`

### Voorkooprecht niet-geïsoleerde woningen

- `measure_id`: `voorkooprecht_niet_geïsoleerde_woningen`
- `priority`: `13`
- `hidden_in_ui`: `false`
- `group_id`: `voorkooprecht_woningen`

#### Uitleg
Hierbij worden woningen opgekocht via voorkooprecht wanneer deze doorverkocht worden.

#### Beoogd effect
Doordat er woningen worden opgekocht, wordt er vermeden dat er inwoners zich vestigen op een plaats waar er veel geluidshinder is.

#### Type maatregel
aantal gehinderde personen verminderen

#### Instrument en kosten
- **Instrument:** decretaal voorkooprecht
- **Modelkost (overheid):** `1,00 x` eenheidsprijs woning
- **Administratieve kost:** regulier beleid
- **Koststock:** `bewoonde_niet_geïsoleerde_woning`

### Voorkooprecht geïsoleerde woningen

- `measure_id`: `voorkooprecht_geïsoleerde_woningen`
- `priority`: `14`
- `hidden_in_ui`: `false`
- `group_id`: `voorkooprecht_woningen`

#### Uitleg
Hierbij worden woningen opgekocht via voorkooprecht wanneer deze doorverkocht worden.

#### Beoogd effect
Doordat er woningen worden opgekocht, wordt er vermeden dat er inwoners zich vestigen op een plaats waar er veel geluidshinder is.

#### Type maatregel
aantal gehinderde personen verminderen

#### Instrument en kosten
- **Instrument:** decretaal voorkooprecht
- **Modelkost (overheid):** `1,00 x` eenheidsprijs woning
- **Administratieve kost:** regulier beleid
- **Koststock:** `bewoonde_geïsoleerde_woning`

### Onteigenen niet-geïsoleerde woningen

- `measure_id`: `onteigening_niet_geïsoleerde_woningen`
- `priority`: `15`
- `hidden_in_ui`: `false`
- `group_id`: `onteigenen_woningen`

#### Uitleg
Hierbij worden woningen onteigend.

#### Beoogd effect
Doordat er woningen worden onteigend, wordt er vermeden dat er bijkomende inwoners zich vestigen op een plaats waar er veel geluidshinder is.

#### Type maatregel
aantal gehinderde personen verminderen

#### Instrument en kosten
- **Instrument:** onteigeningsplan
- **Modelkost (overheid):** `1,50 x` eenheidsprijs woning
- **Administratieve kost:** organiseren onteigening
- **Koststock:** `bewoonde_niet_geïsoleerde_woning`

### Onteigenen geïsoleerde woningen

- `measure_id`: `onteigening_geïsoleerde_woningen`
- `priority`: `16`
- `hidden_in_ui`: `false`
- `group_id`: `onteigenen_woningen`

#### Uitleg
Hierbij worden woningen onteigend.

#### Beoogd effect
Doordat er woningen worden onteigend, wordt er vermeden dat er bijkomende inwoners zich vestigen op een plaats waar er veel geluidshinder is.

#### Type maatregel
aantal gehinderde personen verminderen

#### Instrument en kosten
- **Instrument:** onteigeningsplan
- **Modelkost (overheid):** `1,50 x` eenheidsprijs woning
- **Administratieve kost:** organiseren onteigening
- **Koststock:** `bewoonde_geïsoleerde_woning`

### Isolatievoorschriften nieuwbouw naar niet-geïsoleerde woning

- `measure_id`: `isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning`
- `priority`: `17`
- `hidden_in_ui`: `false`
- `group_id`: `isolatie_nieuwbouw`

#### Praktische informatie
- **Instrument:** Gewestelijk GRUP/stedenbouwkundige verordening
- **Modelkost:** geen (stroom naar niet-geïsoleerd heeft geen isolatiekost)
- **Administratieve kost:** monitoring via as built
- **Koststock:** -

### Isolatievoorschriften nieuwbouw naar geïsoleerde woning

- `measure_id`: `isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning`
- `priority`: `18`
- `hidden_in_ui`: `false`
- `group_id`: `isolatie_nieuwbouw`

#### Uitleg
Bij het bouwen van een nieuwe woning zijn akoestische isolatievoorschriften opgelegd.

#### Beoogd effect
Doordat er geïsoleerd wordt, wordt het akoestisch binnencomfort verbeterd.

#### Type maatregel
akoestisch binnencomfort verbeteren

#### Instrument en kosten
- **Instrument:** Gewestelijk GRUP/stedenbouwkundige verordening
- **Modelkost (privé):** `0,10 x` eenheidsprijs woning per nieuwe geïsoleerde woning
- **Administratieve kost:** monitoring via as built
- **Koststock:** `bewoonde_geïsoleerde_woning`

### Renovatie zonder maatregel

- `measure_id`: `renovatie_zonder_maatregel`
- `priority`: `19`
- `hidden_in_ui`: `true`

#### Praktische informatie
- **Instrument:** geen bijkomend instrument (referentiescenario)
- **Modelkost (privé):** `0,20 x` eenheidsprijs woning per akoestisch gerenoveerde woning
- **Administratieve kost:** regulier beleid
- **Koststock:** `bewoonde_niet_geïsoleerde_woning`

### Verplicht isoleren bij serieuze renovatie

- `measure_id`: `verplicht_isoleren_renovatie`
- `priority`: `20`
- `hidden_in_ui`: `false`

#### Uitleg
Bij een grondige renovatie wordt een akoestische isolatie opgelegd.

#### Beoogd effect
Doordat er geïsoleerd wordt, wordt het akoestisch binnencomfort verbeterd.

#### Type maatregel
akoestisch binnencomfort verbeteren

#### Instrument en kosten
- **Instrument:** akoestische stedenbouwkundige verordening
- **Modelkost (privé):** `0,20 x` eenheidsprijs woning per verplicht geïsoleerde woning
- **Administratieve kost:** monitoring via as built
- **Koststock:** `bewoonde_niet_geïsoleerde_woning`

### Gesubsidieerd isolatieprogramma

- `measure_id`: `gesubsidieerd_isolatieprogramma`
- `priority`: `21`
- `hidden_in_ui`: `false`

#### Uitleg
Akoestische isolaties worden gesubsidieerd.

#### Beoogd effect
Doordat er geïsoleerd wordt, wordt het akoestisch binnencomfort verbeterd.

#### Type maatregel
akoestisch binnencomfort verbeteren

#### Instrument en kosten
- **Instrument:** Gewestelijk isolatieprogramma en subsidieregeling
- **Modelkost:** `0,10 x` woningprijs overheid + `0,10 x` woningprijs privé per geïsoleerde woning
- **Administratieve kost:** 1 werkdag per dossier subsidie voor isolatie
- **Koststock:** `bewoonde_niet_geïsoleerde_woning`

### Gestuurd isolatieprogramma

- `measure_id`: `gestuurd_isolatieprogramma`
- `priority`: `22`
- `hidden_in_ui`: `false`

#### Uitleg
Akoestische isolaties worden gesubsidieerd en er wordt een aannemer aangesteld die straat per straat dit aanpakt.

#### Beoogd effect
Doordat er geïsoleerd wordt, wordt het akoestisch binnencomfort verbeterd.

#### Type maatregel
akoestisch binnencomfort verbeteren

#### Instrument en kosten
- **Instrument:** isolatieprogramma, past dit binnen gelijkheidsbeginsel?
- **Modelkost (overheid):** `0,15` (= 3/20) x eenheidsprijs woning per geïsoleerde woning
- **Administratieve kost:** 3 werkdagen per dossier isolatie
- **Koststock:** `bewoonde_niet_geïsoleerde_woning`

### Aanleg van geluidsbuffers

- `measure_id`: `aanleg_geluidsbuffers`
- `priority`: `23`
- `hidden_in_ui`: `false`

#### Praktische informatie
- **Instrument:** geen instrument voor nodig
- **Modelkost:** 0 (open / nog niet gekwantificeerd)
- **Administratieve kost:** -
- **Koststock:** -


---

## Gerelateerd

- [README](../readme.md)
- [Maatregelen toevoegen](maatregelen-toevoegen.md)
- [Dashboard-berekeningen](dashboard-berekeningen.md)
- [Terminologie](terminologie.md)
