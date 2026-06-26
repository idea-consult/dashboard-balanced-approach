# Databronnen (`data/`)

Overzicht van bronbestanden met consistente Nederlandse naamgeving.

## Naamgevingsconventie

| Patroon | Voorbeeld | Betekenis |
| ------- | --------- | --------- |
| `contour_*` | `contour_vlaanderen_stocks.xlsx` | Geluidscontour + stocks (Vlaanderen) |
| `inwoners_*` | `inwoners_brussel_sector_contour_2024.xlsx` | Bevolkingsdata |
| `vergunningen_*` | `vergunningen_omgevingsloket_2026.xlsx` | Vergunningsdata omgevingsloket |
| `vergunningen_*_lang.csv` | `vergunningen_omgevingsloket_2026_lang.csv` | Zelfde bron, platte (lange) tabel |
| `transacties_vastgoed/transacties_*.csv` | `transacties_woningen.csv` | Vastgoedtransacties per segment |

- **Ruw (Excel):** pivot-structuur, 3 headerrijen — te verwerken in `contour_data.ipynb` / `contour/vergunningen.py`.
- **Lang (`_lang.csv`):** kolommen `bron`, `jaar_indiening`, `gemeente`, `handeling`, `gebouw_functie`, `metriek`, `waarde`.
- **Jaar** (`_2026`, `_2024`): peildatum of versie van de export.

## Bestanden in `data/`

### Contour en inwoners

| Bestand | Inhoud |
| ------- | ------ |
| `contour_vlaanderen_stocks.xlsx` | Vlaanderen (+ rest land): tabbladen `lden` en `lnight` — inwoners, woningen, percelen, prijzen, woongebied |
| `inwoners_brussel_sector_contour_2024.xlsx` | Brussel: inwoners per statistische sector per dB-contour (gebruikt voor `inwoners_brussel` in contour; niet voor gemeente-koppeling) |
| `population 2024 par bout de secteur stat.xlsx` | Brussel + Vlaanderen: sector x dB; kolom `Part de la surface du qs dans le noise contour` voor gemeente→contour (`contour/spatial.py`) |

### Vergunningen (omgevingsloket)

| Ruw | Lang | Inhoud |
| --- | ---- | ------ |
| `vergunningen_omgevingsloket_2026.xlsx` | `vergunningen_omgevingsloket_2026_lang.csv` | Alle vergunningen: nieuwbouw, sloop, verbouwen; per gemeente en jaar |
| `vergunningen_kwetsbare_functies_2026.xlsx` | `vergunningen_kwetsbare_functies_2026_lang.csv` | Vergunde kwetsbare functies |
| `vergunningen_verkaveling_2026.xlsx` | `vergunningen_verkaveling_2026_lang.csv` | Verkaveling en sloop |

### Vastgoedtransacties (`transacties_vastgoed/`)

Per kadastraal perceel (CaPaKey in kolom `NISCode`), tab-gescheiden CSV:

| Bestand | Segment |
| ------- | ------- |
| `transacties_woningen.csv` | Eengezinswoningen |
| `transacties_appartementen.csv` | Appartementen |
| `transacties_handel.csv` | Handel |
| `transacties_kantoren.csv` | Kantoren |
| `transacties_industrie_bebouwd.csv` | Industrie (bebouwd perceel) |
| `transacties_industrie_terrein.csv` | Industrieterrein (onbebouwd) |

Kaarten databeschikbaarheid prijzen: `transacties_vastgoed/kaarten_beschikbaarheid/kaart_prijzen_*.png`.

**Prijzen op contour:** de kolommen `prijs_*` in `input/lden_contour.csv` worden berekend uit deze transactie-CSVs (`contour/prices.py`), niet meer uit dummy-waarden in `contour_vlaanderen_stocks.xlsx`. Per CaPaKey: `avg_PriceP50`, of anders `average_price_m2 × avg_ParcelsAreaP50`. Aggregatie naar geluidsband via `data/capakey_contour_lden.csv` (optioneel) en/of Brusselse sector-gewichten.

## Oude → nieuwe namen (migratie)

| Oud | Nieuw |
| --- | ----- |
| `contour.xlsx` | `contour_vlaanderen_stocks.xlsx` |
| `Population of brussels per statistical sector and db contour 2024.xlsx` | `inwoners_brussel_sector_contour_2024.xlsx` |
| `analyse_omgevingsloket_juni2026.*` | `vergunningen_omgevingsloket_2026.*` |
| `kwetsbare_functies_vergund_2026.*` | `vergunningen_kwetsbare_functies_2026.*` |
| `verkavelingen_2026.*` | `vergunningen_verkaveling_2026.*` |
| `real estate transaction per segment/` | `transacties_vastgoed/` |
| `houses.csv` | `transacties_woningen.csv` |
| `Appartment.csv` | `transacties_appartementen.csv` |
| `retail.csv` | `transacties_handel.csv` |
| `offices.csv` | `transacties_kantoren.csv` |
| `industry built parcel.csv` | `transacties_industrie_bebouwd.csv` |
| `industry terrain.csv` | `transacties_industrie_terrein.csv` |
