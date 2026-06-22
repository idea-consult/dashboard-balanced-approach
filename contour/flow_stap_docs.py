"""Uitgebreide documentatie per flow-stap voor contour_flows.ipynb."""

from __future__ import annotations

from dataclasses import dataclass

from contour.columns import (
    KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR,
    KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR,
)
from contour.flows import AANKOOP_AANDEEL, ONTEIGING_RATE, RENOVATIE_ISO_AANDEEL

WOONGEBIED_JAREN = 5
WOONVERDICHTING_BASELINE = 0.01
VERBOD_GROTE_WONING_BASELINE = 0.01
ISOLATIE_NIEUW_NIET_BASELINE = 0.5
ISOLATIE_NIEUW_GEO_BASELINE = 1.0


@dataclass(frozen=True)
class FlowStapDefinitie:
    measure_id: str
    titel: str
    uitleg: str
    formule_baseline: str
    formule_active: str
    variabelen: tuple[str, ...]
    aannames: str = ""
    stock_flow: str = ""

_AANKOOP = f"{AANKOOP_AANDEEL} (= 50% publiek × 50% opkoopbaar)"
_ONTEIG = f"{ONTEIGING_RATE} (= 5% van stock per jaar, beleidskeuze)"
_RENO_SPLIT = f"renovatie_totaal × {RENOVATIE_ISO_AANDEEL} (R+) en × {1 - RENOVATIE_ISO_AANDEEL} (R−)"

FLOW_STAP_DEFINITIES: dict[str, FlowStapDefinitie] = {
    "verkavelingsverbod": FlowStapDefinitie(
        measure_id="verkavelingsverbod",
        titel="Verkavelingsverbod",
        uitleg=(
            "Verbod op verkaveling in de geluidszone. In het simulatiemodel heeft deze maatregel "
            "**geen stock-transfer**: geen woningen of percelen veranderen van categorie."
        ),
        formule_baseline="0 (geen effect)",
        formule_active="0 (geen effect)",
        variabelen=(),
        aannames=(
            "Geen quantitatief hinder-effect gemodelleerd — maatregel staat wel in `flow_rules.csv` "
            "voor kostentoewijzing (indien ingevuld)."
        ),
        stock_flow="—",
    ),
    "woongebiedverbod": FlowStapDefinitie(
        measure_id="woongebiedverbod",
        titel="Woongebiedverbod",
        uitleg=(
            "Schrappen van woongebied-aanduidingen: percelen gaan van **onbebouwd bebouwbare** naar "
            "**onbebouwd onbebouwbare** stock (omgekeerd van woongebied-aanduiding). "
            "Baseline = historische netto-aanduiding; active = versnelde schrapping."
        ),
        formule_baseline=(
            f"(bebouwbare_percelen_woongebied(5jr) − niet_bebouwbare_percelen_woongebied_schrapping(5jr)) "
            f"/ {WOONGEBIED_JAREN} / onbebouwde_onbebouwbare_percelen"
        ),
        formule_active=(
            f"niet_bebouwbare_percelen_woongebied_schrapping(5jr) / {WOONGEBIED_JAREN} "
            "/ onbebouwde_onbebouwbare_percelen"
        ),
        variabelen=(
            KOL_BEBOUWBARE_PERCELEN_WOONGEBIED_5JR,
            KOL_NIET_BEBOUWBARE_SCHRAPPING_5JR,
            "onbebouwde_onbebouwbare_percelen",
        ),
        aannames=(
            f"Cumulatieve 5-jaar-tellers worden **geannualiseerd** (/ {WOONGEBIED_JAREN}).\n"
            "Woongebied-data alleen uit Vlaanderen-contour; Brussel = 0.\n"
            "`onbebouwde_onbebouwbare_percelen` is nu **placeholder 0** → rate = 0 tot echte stock per band."
        ),
        stock_flow="onbebouwde_onbebouwbare_percelen ↔ onbebouwde_bebouwbare_percelen",
    ),
    "aankoopbeleid_percelen": FlowStapDefinitie(
        measure_id="aankoopbeleid_percelen",
        titel="Aankoopbeleid percelen",
        uitleg=(
            "Overheid koopt onbebouwde bebouwbare percelen op. In actief scenario stijgt "
            "`perceel_eigendom_overheid`; de privé-stock `onbebouwde_bebouwbare_percelen` daalt."
        ),
        formule_baseline="0 (geen aankoopbeleid in referentie)",
        formule_active=f"{_AANKOOP} × alle_transacties_percelen / onbebouwde_bebouwbare_percelen",
        variabelen=("alle_transacties_percelen", "onbebouwde_bebouwbare_percelen"),
        aannames=(
            f"Opkoopaandeel = **{AANKOOP_AANDEEL}** (50% publieke actor × 50% van transacties die opkoopbaar zijn).\n"
            "Transactieteller = industrie/onbebouwd segment (`industrie_terrein` + `industrie_bebouwd`), "
            "gekoppeld per CaPaKey → contour.\n"
            "Geen aparte filter op «bebouwbaar» in transactiedata.\n"
            "`onbebouwde_bebouwbare_percelen` placeholder **0** → rate = 0."
        ),
        stock_flow="onbebouwde_bebouwbare_percelen → perceel_eigendom_overheid",
    ),
    "voorkooprecht_percelen": FlowStapDefinitie(
        measure_id="voorkooprecht_percelen",
        titel="Voorkooprecht percelen",
        uitleg=(
            "Gemeente/overheid oefent voorkooprecht uit bij verkoop van onbebouwde bebouwbare percelen. "
            "Teller = alle verkopen (≈ transacties) per band."
        ),
        formule_baseline="0",
        formule_active="alle_verkopen_onbebouwde_bebouwbare_percelen / onbebouwde_bebouwbare_percelen",
        variabelen=("alle_verkopen_onbebouwde_bebouwbare_percelen", "onbebouwde_bebouwbare_percelen"),
        aannames=(
            "**Geen publiek/privé-split** in transactiedata → `alle_verkopen_onbebouwde_bebouwbare_percelen` "
            "= `alle_transacties_percelen` (zelfde waarde).\n"
            "Voorkooprecht geldt als 100% van die transactiestroom in actief scenario.\n"
            "Stock-noemer placeholder 0."
        ),
        stock_flow="onbebouwde_bebouwbare_percelen → perceel_eigendom_overheid",
    ),
    "onteigening_percelen": FlowStapDefinitie(
        measure_id="onteigening_percelen",
        titel="Onteigening percelen",
        uitleg=(
            "Onteigening van onbebouwde bebouwbare percelen door overheid. "
            "Geen empirische teller — vaste jaarlijkse rate op de stock."
        ),
        formule_baseline="0",
        formule_active=_ONTEIG,
        variabelen=("onbebouwde_bebouwbare_percelen",),
        aannames=(
            f"Vaste rate **{ONTEIGING_RATE}** per jaar (5% van stock), niet data-gedreven.\n"
            "Onafhankelijk van transactie- of vergunningentellers."
        ),
        stock_flow="onbebouwde_bebouwbare_percelen → perceel_eigendom_overheid",
    ),
    "verbod_kleine_woning": FlowStapDefinitie(
        measure_id="verbod_kleine_woning",
        titel="Verbod kleine woning",
        uitleg=(
            "Verbod op kleine/MER-vrije nieuwbouwwoningen in de zone. "
            "Baseline én active gebruiken dezelfde rate: vergunde wooneenheden nieuwbouw t.o.v. "
            "onbebouwde bebouwbare percelen (proportioneel per band)."
        ),
        formule_baseline="vergunde_wooneenheden_nieuwbouw / onbebouwde_bebouwbare_percelen",
        formule_active="= baseline (zelfde formule)",
        variabelen=("vergunde_wooneenheden_nieuwbouw", "onbebouwde_bebouwbare_percelen"),
        aannames=(
            "Vergunningen per gemeente → contour via conversietabel (deels Vlaamse ring).\n"
            "Filter: `Nieuwbouw` + `Aantal wooneenheden`, jaar = 2025.\n"
            "**Geen MER-split** in brondata: totaal nieuwbouw-wooneenheden als proxy voor «kleine» woning."
        ),
        stock_flow="onbebouwde_bebouwbare_percelen → nieuwe_woning (via simulator)",
    ),
    "verbod_grote_woning": FlowStapDefinitie(
        measure_id="verbod_grote_woning",
        titel="Verbod grote woning (MER-plichtig)",
        uitleg=(
            "Verbod op grote/MER-plichtige woningen. MER-plichtige projecten zijn **niet identificeerbaar** "
            "in vergunningsdata → geen aparte teller."
        ),
        formule_baseline=f"{VERBOD_GROTE_WONING_BASELINE} (symbolische referentiestroom)",
        formule_active="0 (beleidskeuze: geen effect in actief scenario)",
        variabelen=("onbebouwde_bebouwbare_percelen",),
        aannames=(
            "**Beleidskeuze:** `active = 0` — maatregel doet niets in actief scenario zolang MER-split ontbreekt.\n"
            f"Baseline = {VERBOD_GROTE_WONING_BASELINE} als placeholder (1% per jaar)."
        ),
        stock_flow="— (geen effect gemodelleerd)",
    ),
    "verbod_kwetsbare_groep": FlowStapDefinitie(
        measure_id="verbod_kwetsbare_groep",
        titel="Verbod kwetsbare groep",
        uitleg=(
            "Beperking van kwetsbare functies (bv. zorg, kinderopvang) in de geluidszone. "
            "Teller = vergunningen kwetsbare functies per band."
        ),
        formule_baseline="vergunningen_kwetsbare_groep / onbebouwde_bebouwbare_percelen",
        formule_active="= baseline",
        variabelen=("vergunningen_kwetsbare_groep", "onbebouwde_bebouwbare_percelen"),
        aannames=(
            "Bron: `vergunningen_kwetsbare_functies_2026_lang.csv`, verdeeld naar contour.\n"
            "Baseline = active: maatregel schakelt de bestaande stroom uit (zelfde rate beide kanten)."
        ),
        stock_flow="onbebouwde_bebouwbare_percelen (functie-toewijzing)",
    ),
    "woonverdichtingsverbod_niet_geïsoleerde_woningen": FlowStapDefinitie(
        measure_id="woonverdichtingsverbod_niet_geïsoleerde_woningen",
        titel="Woonverdichtingsverbod — niet-geïsoleerde woningen",
        uitleg=(
            "Verbod op woonverdichting (opsplitsing/uitbreiding) van **niet-geïsoleerde** woningen. "
            "Geen aparte vergunningenteller voor «verdichting» in de data."
        ),
        formule_baseline=f"{WOONVERDICHTING_BASELINE} (symbolische referentie-verdichting)",
        formule_active="0 (beleidskeuze: geen extra verdichting tegengehouden)",
        variabelen=("bewoonde_niet_geïsoleerde_woning",),
        aannames=(
            "**Beleidskeuze:** `active = 0` — geen kwantitatief effect tot vergunningen opsplitsing isoleren.\n"
            f"Baseline = {WOONVERDICHTING_BASELINE} op stock niet-geïsoleerde woningen."
        ),
        stock_flow="—",
    ),
    "woonverdichtingsverbod_geïsoleerde_woningen": FlowStapDefinitie(
        measure_id="woonverdichtingsverbod_geïsoleerde_woningen",
        titel="Woonverdichtingsverbod — geïsoleerde woningen",
        uitleg="Zelfde maatregel als vorige stap, maar op stock **geïsoleerde** woningen.",
        formule_baseline=f"{WOONVERDICHTING_BASELINE}",
        formule_active="0",
        variabelen=("bewoonde_geïsoleerde_woning",),
        aannames="Idem woonverdichtingsverbod niet-geïsoleerd; `active = 0` beleidskeuze.",
        stock_flow="—",
    ),
    "aankoopbeleid_niet_geïsoleerde_woningen": FlowStapDefinitie(
        measure_id="aankoopbeleid_niet_geïsoleerde_woningen",
        titel="Aankoopbeleid — niet-geïsoleerde woningen",
        uitleg=(
            "Overheid koopt **niet-geïsoleerde** woningen op de markt. "
            "Privé-stock daalt; `woning_eigendom_overheid` stijgt."
        ),
        formule_baseline="0",
        formule_active=f"{_AANKOOP} × alle_transacties_woningen / bewoonde_niet_geïsoleerde_woning",
        variabelen=("alle_transacties_woningen", "bewoonde_niet_geïsoleerde_woning"),
        aannames=(
            f"Opkoopaandeel **{AANKOOP_AANDEEL}** op alle woningtransacties (woningen + appartementen) per band.\n"
            "Geen split geo/niet-geo in transactiedata — zelfde teller als geïsoleerde variant.\n"
            "Stock = 80% placeholder van totaal woningen per band."
        ),
        stock_flow="bewoonde_niet_geïsoleerde_woning → woning_eigendom_overheid",
    ),
    "aankoopbeleid_geïsoleerde_woningen": FlowStapDefinitie(
        measure_id="aankoopbeleid_geïsoleerde_woningen",
        titel="Aankoopbeleid — geïsoleerde woningen",
        uitleg=(
            "Overheid koopt **geïsoleerde** woningen op. Zelfde transactiestroom als niet-geïsoleerd, "
            "maar noemer = stock geïsoleerde woningen (20% placeholder)."
        ),
        formule_baseline="0",
        formule_active=f"{_AANKOOP} × alle_transacties_woningen / bewoonde_geïsoleerde_woning",
        variabelen=("alle_transacties_woningen", "bewoonde_geïsoleerde_woning"),
        aannames=(
            f"Opkoopaandeel **{AANKOOP_AANDEEL}**.\n"
            "**Zelfde** `alle_transacties_woningen` voor geo en niet-geo — transacties niet gesplitst op isolatiestatus.\n"
            "Noemer kleiner (20% woningen) → hogere rate per band dan niet-geïsoleerde variant."
        ),
        stock_flow="bewoonde_geïsoleerde_woning → woning_eigendom_overheid",
    ),
    "voorkooprecht_niet_geïsoleerde_woningen": FlowStapDefinitie(
        measure_id="voorkooprecht_niet_geïsoleerde_woningen",
        titel="Voorkooprecht — niet-geïsoleerde woningen",
        uitleg="Voorkooprecht op verkoop van niet-geïsoleerde woningen.",
        formule_baseline="0",
        formule_active="alle_verkopen_woningen / bewoonde_niet_geïsoleerde_woning",
        variabelen=("alle_verkopen_woningen", "bewoonde_niet_geïsoleerde_woning"),
        aannames=(
            "`alle_verkopen_woningen` = `alle_transacties_woningen` (geen publiek/privé-split).\n"
            "100% van transactiestroom als voorkoop in actief scenario."
        ),
        stock_flow="bewoonde_niet_geïsoleerde_woning → woning_eigendom_overheid",
    ),
    "voorkooprecht_geïsoleerde_woningen": FlowStapDefinitie(
        measure_id="voorkooprecht_geïsoleerde_woningen",
        titel="Voorkooprecht — geïsoleerde woningen",
        uitleg="Voorkooprecht op verkoop van geïsoleerde woningen.",
        formule_baseline="0",
        formule_active="alle_verkopen_woningen / bewoonde_geïsoleerde_woning",
        variabelen=("alle_verkopen_woningen", "bewoonde_geïsoleerde_woning"),
        aannames="Zelfde transactieteller als niet-geïsoleerd; noemer = geïsoleerde stock.",
        stock_flow="bewoonde_geïsoleerde_woning → woning_eigendom_overheid",
    ),
    "onteigening_niet_geïsoleerde_woningen": FlowStapDefinitie(
        measure_id="onteigening_niet_geïsoleerde_woningen",
        titel="Onteigening — niet-geïsoleerde woningen",
        uitleg="Jaarlijkse onteigening van niet-geïsoleerde woningen door overheid.",
        formule_baseline="0",
        formule_active=_ONTEIG,
        variabelen=("bewoonde_niet_geïsoleerde_woning",),
        aannames=f"Vaste **{ONTEIGING_RATE}** per jaar op stock; niet gekoppeld aan transacties.",
        stock_flow="bewoonde_niet_geïsoleerde_woning → woning_eigendom_overheid",
    ),
    "onteigening_geïsoleerde_woningen": FlowStapDefinitie(
        measure_id="onteigening_geïsoleerde_woningen",
        titel="Onteigening — geïsoleerde woningen",
        uitleg="Jaarlijkse onteigening van geïsoleerde woningen.",
        formule_baseline="0",
        formule_active=_ONTEIG,
        variabelen=("bewoonde_geïsoleerde_woning",),
        aannames=f"Vaste **{ONTEIGING_RATE}** op geïsoleerde stock.",
        stock_flow="bewoonde_geïsoleerde_woning → woning_eigendom_overheid",
    ),
    "isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning": FlowStapDefinitie(
        measure_id="isolatievoorschriften_nieuwbouw_naar_niet_geïsoleerde_woning",
        titel="Isolatievoorschriften nieuwbouw → niet-geïsoleerd",
        uitleg=(
            "Nieuwbouw die **niet** aan isolatienorm voldoet, stroomt naar niet-geïsoleerde woning-stock. "
            "In actief scenario worden strengere normen — baseline-reflectie blijft deels niet-geïsoleerde instroom."
        ),
        formule_baseline="nieuwbouw_niet_geïsoleerd / nieuwe_woning (fallback: vaste 0,5)",
        formule_active="0 (strengere norm in actief scenario)",
        variabelen=("nieuwbouw_niet_geïsoleerd", "nieuwe_woning"),
        aannames=(
            f"Placeholder `nieuwbouw_niet_geïsoleerd` = **0** → notebook gebruikt baseline **{ISOLATIE_NIEUW_NIET_BASELINE}** "
            "als vaste rate zolang teller ontbreekt.\n"
            "Noemer `nieuwe_woning` dynamisch in simulator (stock in aanbouw)."
        ),
        stock_flow="nieuwe_woning → bewoonde_niet_geïsoleerde_woning",
    ),
    "isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning": FlowStapDefinitie(
        measure_id="isolatievoorschriften_nieuwbouw_naar_geïsoleerde_woning",
        titel="Isolatievoorschriften nieuwbouw → geïsoleerd",
        uitleg=(
            "Nieuwbouw die wél aan isolatienorm voldoet → geïsoleerde woning-stock. "
            "Actief scenario: alle nieuwbouw moet voldoen (rate → 1)."
        ),
        formule_baseline="nieuwbouw_geïsoleerd / nieuwe_woning (fallback: 1,0)",
        formule_active="1,0 (100% geïsoleerde nieuwbouw)",
        variabelen=("nieuwbouw_geïsoleerd", "nieuwe_woning"),
        aannames=(
            "Placeholder tellers = 0; fallback baseline **1,0** in code.\n"
            "Active = 1: volledige instroom naar geïsoleerde stock."
        ),
        stock_flow="nieuwe_woning → bewoonde_geïsoleerde_woning",
    ),
    "renovatie_zonder_maatregel": FlowStapDefinitie(
        measure_id="renovatie_zonder_maatregel",
        titel="Renovatie zonder maatregel",
        uitleg=(
            "Referentie-renovatiestroom **met** akoestische/isolatiemaatregel (R+): woningen gaan van "
            "niet-geïsoleerd naar geïsoleerd **zonder** extra beleidsimpuls."
        ),
        formule_baseline=f"R+ / bewoonde_niet_geïsoleerde_woning  waar R+ = {_RENO_SPLIT}",
        formule_active="0",
        variabelen=("renovatie_totaal", "bewoonde_niet_geïsoleerde_woning"),
        aannames=(
            f"Geen iso-split in vergunningen → **{RENOVATIE_ISO_AANDEEL}** van `renovatie_totaal` = R+, rest = R−.\n"
            "Baseline behoudt «natuurlijke» R+-stroom; active = 0 (geen extra maatregel)."
        ),
        stock_flow="bewoonde_niet_geïsoleerde_woning → bewoonde_geïsoleerde_woning",
    ),
    "verplicht_isoleren_renovatie": FlowStapDefinitie(
        measure_id="verplicht_isoleren_renovatie",
        titel="Verplicht isoleren bij renovatie",
        uitleg=(
            "Verplichte isolatie bij elke renovatie: alle renovaties (R+ + R−) moeten isoleren in actief scenario."
        ),
        formule_baseline="0",
        formule_active=f"(R+ + R−) / bewoonde_niet_geïsoleerde_woning",
        variabelen=("renovatie_totaal", "bewoonde_niet_geïsoleerde_woning"),
        aannames=(
            f"R+ + R− = volledige `renovatie_totaal` (vergunningen «Verbouwen of hergebruik»).\n"
            f"Split R+/R− via **{RENOVATIE_ISO_AANDEEL}** alleen voor baseline van andere maatregelen."
        ),
        stock_flow="bewoonde_niet_geïsoleerde_woning → bewoonde_geïsoleerde_woning",
    ),
    "gesubsidieerd_isolatieprogramma": FlowStapDefinitie(
        measure_id="gesubsidieerd_isolatieprogramma",
        titel="Gesubsidieerd isolatieprogramma",
        uitleg=(
            "Subsidie stimuleert isolatie: **dubbele** renovatiestroom t.o.v. verplicht isoleren."
        ),
        formule_baseline="0",
        formule_active=f"2 × (R+ + R−) / bewoonde_niet_geïsoleerde_woning",
        variabelen=("renovatie_totaal", "bewoonde_niet_geïsoleerde_woning"),
        aannames="Factor **2×** op totale renovatiestroom (beleidsintensiteit gesubsidieerd programma).",
        stock_flow="bewoonde_niet_geïsoleerde_woning → bewoonde_geïsoleerde_woning",
    ),
    "gestuurd_isolatieprogramma": FlowStapDefinitie(
        measure_id="gestuurd_isolatieprogramma",
        titel="Gestuurd isolatieprogramma",
        uitleg="Actief, gericht isolatieprogramma: **viervoudige** renovatiestroom.",
        formule_baseline="0",
        formule_active=f"4 × (R+ + R−) / bewoonde_niet_geïsoleerde_woning",
        variabelen=("renovatie_totaal", "bewoonde_niet_geïsoleerde_woning"),
        aannames="Factor **4×** — sterkste isolatie-intensiteit in het maatregelenpakket.",
        stock_flow="bewoonde_niet_geïsoleerde_woning → bewoonde_geïsoleerde_woning",
    ),
    "aanleg_geluidsbuffers": FlowStapDefinitie(
        measure_id="aanleg_geluidsbuffers",
        titel="Aanleg geluidsbuffers",
        uitleg=(
            "Akoestische isolatie via geluidsbuffers: woningen worden geïsoleerd zonder klassieke renovatie-flow."
        ),
        formule_baseline="0",
        formule_active="potentieel_isoleerbare_woningen / 5 / bewoonde_niet_geïsoleerde_woning",
        variabelen=("potentieel_isoleerbare_woningen", "bewoonde_niet_geïsoleerde_woning"),
        aannames=(
            "`potentieel_isoleerbare_woningen` = **placeholder 0** (nog niet gemodelleerd) → rate = 0.\n"
            "Annualisatie / 5 analoge aan 5-jaar-tellers."
        ),
        stock_flow="bewoonde_niet_geïsoleerde_woning → bewoonde_geïsoleerde_woning",
    ),
    "compensatie_buitenzone": FlowStapDefinitie(
        measure_id="compensatie_buitenzone",
        titel="Compensatie buitenzone",
        uitleg=(
            "Financiële compensatie voor bewoners buiten de zone — **geen stock-transfer** in het model."
        ),
        formule_baseline="0",
        formule_active="0",
        variabelen=(),
        aannames=(
            "Kosten via `measure_costs.csv` (lage vermenigvuldiger op woningprijs); "
            "geen wijziging stocks/flows."
        ),
        stock_flow="— (alleen kosten)",
    ),
    "compensatie_verhuis": FlowStapDefinitie(
        measure_id="compensatie_verhuis",
        titel="Compensatie verhuis",
        uitleg="Compensatie bij verhuizing — geen quantitatieve flow in stockmodel.",
        formule_baseline="0",
        formule_active="0",
        variabelen=(),
        aannames="Idem compensatie buitenzone: kostenpost, geen stock-effect.",
        stock_flow="— (alleen kosten)",
    ),
    "versterken_sociale_cohesie": FlowStapDefinitie(
        measure_id="versterken_sociale_cohesie",
        titel="Versterken sociale cohesie",
        uitleg="Sociaal beleid zonder gemodelleerde stock-flow.",
        formule_baseline="0",
        formule_active="0",
        variabelen=(),
        aannames="Geen kost-stock in `measure_costs.csv` (`kost_stock = -`).",
        stock_flow="—",
    ),
    "vergroenen_leefomgeving": FlowStapDefinitie(
        measure_id="vergroenen_leefomgeving",
        titel="Vergroenen leefomgeving",
        uitleg="Groeninfra — geen stock-flow gemodelleerd.",
        formule_baseline="0",
        formule_active="0",
        variabelen=(),
        aannames="Geen quantitatieve flow; optionele kosten apart.",
        stock_flow="—",
    ),
}
