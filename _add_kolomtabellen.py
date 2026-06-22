"""Add column overview tables to contour_data.ipynb markdown cells."""
import json
import re
from pathlib import Path

NB = Path("contour_data.ipynb")

from contour.consolidate import bouw_contour_lden  # noqa: E402
from contour.prices import PRIJS_KOLOMMEN  # noqa: E402

WOONGEBIED_A = (
    "aantal bebouwbare percelen die werden gecreëerd door woongebieden aan te duiden"
)
WOONGEBIED_S = (
    "aantal niet-bebouwbarepercelen die worden gecreëerd door woongebied te schrappen"
)
JAAR = "2026"

KOLOM_BESCHRIJVINGEN: dict[str, str] = {
    "geluidscontour": "Bandlabel (bv. `45-46`)",
    "db_ondergrens": "Ondergrens dB-band",
    "db_bovengrens": "Bovengrens dB-band",
    "inwoners": "Totaal inwoners Vlaanderen + Brussel in band",
    "aantal_woningen": "Woningen Vlaanderen (bron Excel)",
    WOONGEBIED_A: "Flow-teller: woongebied-aanduiding, cumulatief 5 jr (Vlaanderen)",
    WOONGEBIED_S: "Flow-teller: woongebied-schrapping, cumulatief 5 jr (Vlaanderen)",
    "gemiddeld_aantal_inwoners_per_huis": "Vlaanderen: `inwoners` / `aantal_woningen`",
    "inwoners_brussel": "Brussel: som sectoren per `db_ondergrens`",
    "inwoners_vlaanderen": "Kopie Vlaanderen-`inwoners` vóór merge",
    "aantal_woningen_vlaanderen": "Gelijk aan Excel `aantal_woningen`",
    "aantal_woningen_brussel": "Geschat: `inwoners_brussel` / gem. inw./woning",
    "aantal_woningen_totaal": "Som Vlaanderen + Brussel",
    "db_midden": "Middelpunt band: (`db_ondergrens` + `db_bovengrens`) / 2",
    "dosis_effect_relatie": "% ernstig gehinderden (lookup lden/lnight)",
    "prijs_onbebouwde_bebouwbare_percelen": "€/eenheid uit transacties industrie",
    "prijs_onbebouwde_onbebouwbare_percelen": "€/eenheid uit transacties industrie-terrein",
    "prijs_bewoonde_niet_geïsoleerde_woning": "€/woning uit woningen + appartementen",
    "prijs_bewoonde_geïsoleerde_woning": "Idem (zelfde transactiebron)",
}


def _regio_kolom_beschrijving(kolom: str) -> str:
    if kolom.startswith("aantal_ernstig_gehinderden_"):
        regio = kolom.replace("aantal_ernstig_gehinderden_", "").replace(f"_{JAAR}", "")
        return f"Ernstig gehinderden ({regio}): inwoners x dosis-effect / 100"
    if "niet_geïsoleerde_huizen" in kolom:
        regio = "totaal" if "_totaal_" in kolom else kolom.split("_")[-2]
        return f"Placeholder 80% woningen ({regio})"
    if "geïsoleerde_huizen" in kolom:
        regio = kolom.split("_")[-2] if "_totaal_" not in kolom else "totaal"
        return f"Placeholder 20% woningen ({regio})"
    if "onbebouwde_bebouwbare_percelen" in kolom or "onbebouwde_onbebouwbare_percelen" in kolom:
        return "Placeholder 0 (parcel-stock; woongebied-kolommen zijn aparte flow-tellers)"
    if "eigendom_overheid" in kolom:
        return "Startwaarde 0 (nog geen bron)"
    return "Afgeleide stock-kolom"


def volledige_contour_tabel() -> str:
    kolommen = list(bouw_contour_lden().columns) + list(PRIJS_KOLOMMEN)
    regels = ["| Kolom | Beschrijving |", "|-------|----------------|"]
    for kolom in kolommen:
        desc = KOLOM_BESCHRIJVINGEN.get(kolom, _regio_kolom_beschrijving(kolom))
        regels.append(f"| `{kolom}` | {desc} |")
    return "\n".join(regels)


def strip_kolomoverzicht(text: str) -> str:
    return re.sub(r"\n#### Kolomoverzicht.*", "", text, flags=re.DOTALL).rstrip()


def add_section(text: str, section: str) -> str:
    return strip_kolomoverzicht(text) + "\n\n" + section.strip()


SECTIONS: dict[str, str] = {
    "## Deel A": f"""#### Kolomoverzicht (`df_data_inventory`)

| Kolom | Beschrijving |
|-------|----------------|
| `bestand` | Bestandsnaam in `data/` |
| `pad` | Volledig pad naar bron |
| `beschrijving` | Korte inhoud (lden/lnight, vergunningen, ...) |
| `rijen` | Aantal rijen (CSV) of `None` (Excel) |
| `kolommen` | Kolomnamen of tabbladen |
| `status` | `ok` / `deels` t.o.v. FLOW §2 |""",
    "## Deel B": f"""#### Kolomoverzicht (ruwe bronnen na laden)

**`raw_vlaanderen_lden` / `raw_vlaanderen_lnight`** — na `hernoem_vlaanderen_kolommen()`:

| Kolom | Beschrijving |
|-------|----------------|
| `geluidscontour` | Bandlabel (bv. `45-46`) |
| `db_ondergrens` / `db_bovengrens` | dB-grenzen van de band |
| `inwoners` | Inwoners Vlaanderen (+ rest land) in contour |
| `aantal_woningen` | Woningen Vlaanderen in contour |
| `{WOONGEBIED_A}` | Woongebied-aanduiding (5 jr voorraad; Excel-naam ongewijzigd) |
| `{WOONGEBIED_S}` | Woongebied-schrapping (Excel-naam ongewijzigd) |

**`raw_brussel_lden`** (sector, selectie kolommen):

| Kolom | Beschrijving |
|-------|----------------|
| `dB` | dB-waarde van de contour |
| `Population dans le contour` | Inwoners sector in contour |
| `T_MUN_NL` | Gemeentenaam (NL) |

**`vergunningen_*` (lang CSV)** — kolommen `bron`, `jaar_indiening`, `gemeente`, `handeling`, `gebouw_functie`, `metriek`, `waarde`.

**`transacties`** — per segment samengevoegd:

| Kolom | Beschrijving |
|-------|----------------|
| `capakey` | Kadastraal perceel (hernoemd uit `NISCode`) |
| `sum_ParcelsNumber` | Aantal transacties op perceel |
| `avg_PriceP25` / `avg_PriceP50` / `avg_PriceP75` | Prijspercentielen |
| `avg_ParcelsAreaP50` | Mediane perceeloppervlakte |
| `average_price_m2` | Gemiddelde prijs per m² |
| `segment` | `woningen`, `appartementen`, `handel`, ... |""",
    "## Deel B2": """#### Kolomoverzicht (setup — hergebruikt Deel B)

Geen nieuw dataframe; de setup-cel laadt of hergebruikt:

| Variabele | Kolommen (zie Deel B) |
|-----------|------------------------|
| `raw_vlaanderen_lden` / `raw_vlaanderen_lnight` | 7 kolommen na hernoemen |
| `raw_brussel_lden` / `raw_brussel_lnight` | Sector x contour (39 kolommen ruw) |
| `vergunningen_*` | Lang-formaat vergunningen |
| `transacties` | CaPaKey-transacties + `segment` |

In **stap 6** komt bovendien `sector_lden` uit `population 2024 par bout de secteur stat.xlsx`:

| Kolom | Beschrijving |
|-------|----------------|
| `T_MUN_NL` | Gemeentenaam |
| `dB` | dB-waarde contour |
| `Part de la surface du qs dans le noise contour` | Aandeel sectoroppervlak in contour (input gewicht) |""",
    "### Stap 1": f"""#### Kolomoverzicht

**`excel_lden`** — ruwe Excel vóór hernoemen: `db_contour`, `lower`, `upper`, `inwoners`, `woningen`, + woongebied-kolommen.

**`stap1_vla`** — output van deze stap:

| Kolom | Beschrijving |
|-------|----------------|
| `geluidscontour` | Hernoemd uit `db_contour` |
| `db_ondergrens` / `db_bovengrens` | Hernoemd uit `lower` / `upper` |
| `inwoners` | Ongewijzigd uit Excel |
| `aantal_woningen` | Hernoemd uit `woningen` |
| `{WOONGEBIED_A}` | Numeriek gemaakt (`geen data` -> 0) |
| `{WOONGEBIED_S}` | Idem |
| `gemiddeld_aantal_inwoners_per_huis` | **Nieuw:** `inwoners` / `aantal_woningen` |""",
    "### Stap 2": """#### Kolomoverzicht

**`stap2_bru_sector`** (voorbeeld, 10 rijen):

| Kolom | Beschrijving |
|-------|----------------|
| `dB` | dB-waarde |
| `Population dans le contour` | Inwoners in sector x contour |
| `T_MUN_NL` | Brusselse gemeente |

**`stap2_bru_db`** — geaggregeerd per dB-band:

| Kolom | Beschrijving |
|-------|----------------|
| `db` | dB-waarde (koppelt aan `db_ondergrens` Vlaanderen) |
| `inwoners` | Som inwoners alle Brusselse sectoren in die band |""",
    "### Stap 3": """#### Kolomoverzicht (`stap3`)

Alle kolommen van `stap1_vla`, plus:

| Kolom | Beschrijving |
|-------|----------------|
| `inwoners_brussel` | Inwoners Brussel (uit `stap2_bru_db`, via `db_ondergrens` = `db`) |
| `inwoners_vlaanderen` | Kopie van Vlaanderen-`inwoners` vóór merge |
| `inwoners` | **Totaal:** `inwoners_vlaanderen` + `inwoners_brussel` |""",
    "### Stap 4": """#### Kolomoverzicht (`stap4`)

Kolommen van `stap3`, plus:

| Kolom | Beschrijving |
|-------|----------------|
| `aantal_woningen_vlaanderen` | Gelijk aan `aantal_woningen` uit Excel |
| `aantal_woningen_brussel` | Geschat: `inwoners_brussel` / `gemiddeld_aantal_inwoners_per_huis` |
| `aantal_woningen_totaal` | Som Vlaanderen + Brussel |""",
    "### Stap 5": f"""#### Kolomoverzicht (`stap5`)

Kolommen van `stap4`, plus:

| Kolom | Beschrijving |
|-------|----------------|
| `db_midden` | `(db_ondergrens + db_bovengrens) / 2` |
| `dosis_effect_relatie` | Lookup % ernstig gehinderden per band (lden) |
| `aantal_ernstig_gehinderden_vlaanderen_{JAAR}` | `inwoners_vlaanderen` x dosis-effect / 100 |
| `aantal_ernstig_gehinderden_brussel_{JAAR}` | `inwoners_brussel` x dosis-effect / 100 |
| `aantal_ernstig_gehinderden_totaal_{JAAR}` | Som beide regio's |
| `aantal_bewoonde_geisoleerde_huizen_*_{JAAR}` | Placeholder: 20% van woningen (`_vlaanderen`, `_brussel`, `_totaal`) |
| `aantal_bewoonde_niet_geisoleerde_huizen_*_{JAAR}` | Placeholder: 80% van woningen |
| `aantal_onbebouwde_bebouwbare_percelen_*_{JAAR}` | Placeholder **0** (stock; woongebied-kolom blijft apart als flow-teller) |
| `aantal_onbebouwde_onbebouwbare_percelen_*_{JAAR}` | Placeholder **0** (idem) |
| `aantal_perceel_eigendom_overheid_*_{JAAR}` | Start 0 |
| `aantal_woning_eigendom_overheid_*_{JAAR}` | Start 0 |

Patroon `_*_`: suffix `_vlaanderen_{JAAR}`, `_brussel_{JAAR}`, `_totaal_{JAAR}`.""".replace(
        "geisoleerde", "geïsoleerde"
    ),
    "### Stap 6": """#### Kolomoverzicht

**`verg_combined`** (lang):

| Kolom | Beschrijving |
|-------|----------------|
| `bron` | `omgevingsloket` / `kwetsbare_functies` / `verkaveling` |
| `jaar_indiening` | Indieningsjaar |
| `gemeente` | Gemeentenaam (Vlaanderen) |
| `handeling` | bv. `Nieuwbouw`, `Verbouwen of hergebruik` |
| `gebouw_functie` | Gebouwfunctie |
| `metriek` | bv. `Aantal projecten`, `Aantal wooneenheden` |
| `waarde` | Numerieke teller |

**`conversie_lden`** (gemeente x dB):

| Kolom | Beschrijving |
|-------|----------------|
| `gemeente` | `T_MUN_NL` uit sectorbestand |
| `db` | dB-waarde |
| `gewicht_ruimtelijk` | Som `Part de la surface du qs...` per gemeente x dB |
| `aandeel` | Gewicht / som per gemeente (som = 1) |
| `indicator` | `lden` of `lnight` |

**`conversie_band`** — `conversie_lden` + `geluidscontour`, `db_ondergrens`, `db_bovengrens`.

**`verg_contour`** — vergunningen na verdeling:

| Kolom | Beschrijving |
|-------|----------------|
| `bron`, `geluidscontour`, `db_ondergrens`, `jaar_indiening`, `handeling`, `gebouw_functie`, `metriek` | Dimensies |
| `waarde` | `waarde_gemeente` x `aandeel` (geaggregeerd) |

**`verg_niet`** — zelfde dimensies als input, gemeenten zonder spatial match.

**`verg_gemeente`** — aggregatie per gemeente x handeling x metriek (zonder contour).""",
    "### Stap 7": """#### Kolomoverzicht

**`tx`** — transacties + afgeleid:

| Kolom | Beschrijving |
|-------|----------------|
| `capakey` | Kadastraal perceel (hernoemd uit `NISCode`) |
| `segment` | `woningen`, `appartementen`, `industrie_terrein`, ... |
| `sum_ParcelsNumber` | Aantal transacties op perceel |
| `nis5` | **Nieuw:** eerste 5 tekens capakey (NIS-gemeente) |
| `regio` | **Nieuw:** `Brussel` of `Vlaanderen/overig` |
| (+ prijskolommen uit CSV) | `avg_PriceP50`, `average_price_m2`, ... |

**`tx_overzicht`** — aggregatie:

| Kolom | Beschrijving |
|-------|----------------|
| `regio` | Brussel / Vlaanderen |
| `segment` | Transactiesegment |
| `sum_ParcelsNumber` | Som transacties |""",
    "### Stap 8": """#### Kolomoverzicht

**`capakey_prijzen`** — prijs per capakey x prijskolom.

**`capakey_mapping`** — capakey naar `geluidscontour` / `db_ondergrens`.

**`prijzen_contour`** — gemiddelde prijs per contourband.

**`stap8`** — `stap5` + prijskolommen:

| Kolom | Beschrijving |
|-------|----------------|
| `prijs_onbebouwde_bebouwbare_percelen` | Uit transacties `industrie_terrein` (+ bebouwd) |
| `prijs_onbebouwde_onbebouwbare_percelen` | Uit `industrie_terrein` |
| `prijs_bewoonde_niet_geisoleerde_woning` | Uit woningen + appartementen |
| `prijs_bewoonde_geisoleerde_woning` | Idem (zelfde bron) |""".replace(
        "geisoleerde", "geïsoleerde"
    ),
    "### Stap 9": f"""#### Kolomoverzicht (`contour_lden_handmatig`)

Zelfde kolommen als `stap8` en als `contour_lden` na Deel C ({len(list(bouw_contour_lden().columns)) + len(PRIJS_KOLOMMEN)} kolommen, één rij per dB-band):

PLACEHOLDER_VOLLEDIG""",
    "## Deel C": f"""#### Kolomoverzicht (`tables` na `run_data_pipeline()`)

**`contour_lden` / `contour_lnight`** — volledige kolomlijst (lden = onderstaand; lnight idem structuur):

PLACEHOLDER_VOLLEDIG

**Overige parquet-bestanden:**

| Sleutel | Belangrijkste kolommen |
|---------|------------------------|
| `conversie_gemeente_db` | `gemeente`, `db`, `aandeel`, `indicator` |
| `vergunningen_gemeente` | gemeente x handeling x metriek |
| `vergunningen_contour` | vergunningen per `geluidscontour` |
| `vergunningen_niet_toewijsbaar` | gemeenten zonder match |
| `transacties_capakey` | ruwe transacties + `segment` |
| `capakey_prijzen` | prijs per capakey |
| `capakey_contour_mapping` | capakey -> contour |
| `prijs_dekking` | dekkingsstatistiek prijsberekening |""",
}


def match_key(first_line: str) -> str | None:
    for key in sorted(SECTIONS, key=len, reverse=True):
        if first_line.startswith(key):
            return key
    return None


def main() -> None:
    volledig = volledige_contour_tabel()
    sections = {
        k: v.replace("PLACEHOLDER_VOLLEDIG", volledig)
        for k, v in SECTIONS.items()
    }

    nb = json.loads(NB.read_text(encoding="utf-8"))
    updated = 0
    for cell in nb["cells"]:
        if cell.get("cell_type") != "markdown":
            continue
        text = "".join(cell.get("source", []))
        first_line = text.strip().split("\n")[0]
        key = match_key(first_line)
        if key is None:
            continue
        cell["source"] = add_section(text, sections[key])
        updated += 1

    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"updated {updated} cells ({len(SECTIONS)} sections defined)")


if __name__ == "__main__":
    main()
