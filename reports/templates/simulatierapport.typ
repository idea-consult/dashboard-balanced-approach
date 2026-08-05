#let data = json("data.json")

#set page(
  paper: "a4",
  margin: (x: 2cm, y: 2.2cm),
  header: context {
    if counter(page).get().first() > 1 {
      set text(size: 9pt, fill: rgb("#4E2567"), font: "Aptos")
      grid(
        columns: (1fr, auto),
        align: (left, right),
        [#data.title],
        [#image("logo.png", height: 0.9cm)],
      )
      line(length: 100%, stroke: 0.5pt + rgb("#4E2567"))
    }
  },
  footer: context {
    set text(size: 8pt, fill: rgb("#666666"), font: "Aptos")
    line(length: 100%, stroke: 0.4pt + rgb("#A68BB8"))
    v(0.3cm)
    grid(
      columns: (1fr, auto),
      align: (left, right),
      [#data.opdrachtregel],
      [Pagina #counter(page).display()],
    )
  },
)

#set text(font: "Aptos", size: 11pt, fill: rgb("#333333"))
#set heading(numbering: "1.1")
#show heading.where(level: 1): it => {
  set text(fill: rgb("#4E2567"), weight: "bold", size: 14pt)
  v(0.6cm)
  it
  v(0.2cm)
}
#show heading.where(level: 2): it => {
  set text(fill: rgb("#4E2567"), weight: "bold", size: 12pt)
  v(0.4cm)
  it
  v(0.15cm)
}
#show heading.where(level: 3): it => {
  set text(fill: rgb("#4E2567"), weight: "bold", size: 11pt)
  v(0.3cm)
  it
  v(0.1cm)
}
#set par(justify: true, leading: 0.65em)

// —— Voorblad ——
#align(center)[
  #image("logo.png", width: 55%)
  #v(1.2cm)
  #text(size: 22pt, weight: "bold", fill: rgb("#4E2567"))[#data.title]
  #v(0.6cm)
  #text(size: 11pt, fill: rgb("#4E2567"))[#data.opdrachtregel]
  #v(1.2cm)
  #line(length: 60%, stroke: 1pt + rgb("#DD5B61"))
  #v(0.8cm)
  #grid(
    columns: (auto, auto),
    column-gutter: 1.2cm,
    row-gutter: 0.4cm,
    align: (right, left),
    [*Datum van deze export:*], [#data.exported_at],
    [*Simulatieperiode:*], [#str(data.beginjaar) – #str(data.eindjaar)],
    [*Geluidscontour:*], [#data.contour],
    [*Gekozen scenario / maatregelenbundel:*], [
      #data.scenario_label
      #if data.scenario_is_none [
        #linebreak()
        #text(size: 9pt, fill: rgb("#666666"))[(geen preset — handmatige maatregelselectie)]
      ]
    ],
    [*Rekenmethode ernstig gehinderden:*], [#data.ernstig_methode.label],
    [*Cumulatieve modelkost overheid:*], [#data.kosten.overheid],
    [*Cumulatieve modelkost privé:*], [#data.kosten.prive],
  )
]

#pagebreak()

= Leeswijzer

Dit rapport geeft een overzicht van de *simulatie van kosten van een maatregelenbundel* binnen de *tweede pijler* van de Balanced Approach voor de luchthaven van *Brussels-Nationaal (Zaventem)*. De kostensimulatie-toepassing laat toe om interactief verschillende maatregelenbundels te testen binnen de Lden-geluidscontouren rond de luchthaven.

Dit document beschrijft *één gekozen set van maatregelen*, de overige parameters die in de simulatie zijn gebruikt, en de evolutie van de modelkostprijs en hinderindicatoren tussen #str(data.beginjaar) en #str(data.eindjaar).

*Stock* = voorraad (bv. woningen of percelen) in een zone. *Flow* = jaarlijkse verandering als aandeel van een noemer-stock.

- *Baseline:* situatie zonder de betreffende maatregel (referentiestroom).
- *Active:* rate wanneer de maatregel aanstaat.
- Zones *A–F* zijn mutueel exclusief. Overlays *Lnight45* en *NA70* overlappen met A–F en met elkaar; cijfers daarvoor niet optellen bij A–F.
- *Kosten:* som over alle jaren en bands van |baseline − effectieve rate| × stock × eenheidsprijs × relatieve kostfactor (zie sectie Kosten).
- *Ernstig gehinderden:* in deze run geldt *#data.ernstig_methode.label*. Zie sectie *Berekening ernstig gehinderden*.

= Scenario en maatregelselectie

In de dashboardtoepassing kun je een *voorgeprogrammeerd scenario* (maatregelenbundel) selecteren, of *zelf* per maatregel de ruimtelijke dekking kiezen (zones A–F of een overlay).

#if data.scenario_is_none [
  *Gekozen scenario:* Geen (handmatige selectie). De onderstaande tabel toont de maatregelen die in deze run ruimtelijk actief stonden.
] else [
  *Gekozen scenario:* #data.scenario_label. De onderstaande tabel volgt die maatregelenbundel (eventueel plus later handmatig bijgestelde selecties).
]

#if data.applied_measures.len() == 0 [
  Er werden geen (zichtbare) maatregelen ruimtelijk geactiveerd. De simulatie loopt dan vooral op baseline- en altijd-actieve stromen.
] else [
  #table(
    columns: (2.2fr, 1.4fr),
    stroke: 0.4pt + rgb("#A68BB8"),
    inset: 6pt,
    fill: (_, y) => if y == 0 { rgb("#4E2567") } else if calc.odd(y) { rgb("#F7F2FA") } else { white },
    text(fill: white, weight: "bold")[Maatregel],
    text(fill: white, weight: "bold")[Ruimtelijke dekking],
    ..for m in data.applied_measures {
      (m.naam, m.coverage)
    },
  )
]

== Ruimtelijke zones en overlays

Zones *A–F* verdelen de Lden-contour in mutueel exclusieve 5 dB-buckets. Daarnaast bestaan twee *overlays* die geografisch overlappen met A–F (en deels met elkaar):

- *Lnight45:* nachtcontour vanaf 45 dB — doorgaans de *bredere* overlay (ruwweg A–D en deels E).
- *NA70:* NA70-contour — *kleiner*; typisch vooral zones A–B en deels C/D.

Omdat overlays met A–F overlappen, zijn zone- en overlayselectie in de tool wederzijds uitsluitend. Cijfers voor overlays mag je niet optellen bij A–F of bij elkaar.

#figure(
  image("kaart_contouren.png", width: 100%),
  caption: [Zones A–F (Lden) met overlays Lnight45 en NA70 rond Brussels-Nationaal.],
)

= Resultatensamenvatting

== KPI's (totaal over zones)

#table(
  columns: (2.2fr, 1fr, 1fr, 0.9fr),
  stroke: 0.4pt + rgb("#A68BB8"),
  inset: 6pt,
  fill: (_, y) => if y == 0 { rgb("#4E2567") } else if calc.odd(y) { rgb("#F7F2FA") } else { white },
  text(fill: white, weight: "bold")[Indicator],
  text(fill: white, weight: "bold")[#str(data.beginjaar)],
  text(fill: white, weight: "bold")[#str(data.eindjaar)],
  text(fill: white, weight: "bold")[Δ %],
  ..for k in data.kpis {
    (k.label, k.begin, k.eind, k.delta_pct)
  },
)

*Gekozen rekenmethode:* #data.ernstig_methode.label. #data.ernstig_methode.short

== Kosten over het traject

Onderstaande bedragen zijn de *cumulatieve modelkosten* van alle actieve maatregelen over #str(data.beginjaar)–#str(data.eindjaar), afgerond in miljoenen euro. Het zijn geen budgetramingen, maar een vergelijkbare indicator op basis van stockprijzen en relatieve kostfactoren per maatregel (`measure_costs.csv`).

#table(
  columns: (2.2fr, 1.2fr),
  stroke: 0.4pt + rgb("#A68BB8"),
  inset: 6pt,
  fill: (_, y) => if y == 0 { rgb("#4E2567") } else if calc.odd(y) { rgb("#F7F2FA") } else { white },
  text(fill: white, weight: "bold")[Partij],
  text(fill: white, weight: "bold")[Totale modelkost],
  [Overheid], [#data.kosten.overheid],
  [Privé], [#data.kosten.prive],
)

*Hoe worden kosten berekend?* Per actieve flowregel en per jaar:

- *Kostvolume* = |baseline-rate − effectieve rate| × beschikbare inflow-stock.
- *Rijkost* = kostvolume × eenheidsprijs van de koststock (perceel of woning).
- Overheid en privé krijgen elk hun aandeel via `rel_cost_overheid` / `rel_cost_prive`.

Voor *aankoop* of *isolatie* (baseline ≈ 0) komt het volume ongeveer overeen met de werkelijke outflow. Voor *verboden* (active = 0) is het volume het aantal *verhinderde* eenheden (bv. planschade bij woningverbod). Maatregelen zonder kostfactor (0) tellen niet mee in dit totaal.

= Visualisaties

Onderstaande figuren komen overeen met de kernvisualisaties in het dashboard (IDEA-huisstijlkleuren).

#if data.figures.len() == 0 [
  _Geen figuren beschikbaar voor deze run._
] else [
  #for fig in data.figures [
    #block(breakable: false)[
      #image("figures/" + fig.file, width: 100%)
      #text(size: 9pt, fill: rgb("#666666"))[#fig.caption]
      #v(0.5cm)
    ]
  ]
]

= Toegepaste maatregelen (detail)

#if data.measure_groups.len() == 0 [
  Geen actieve maatregelen om toe te lichten.
] else [
  #for group in data.measure_groups [
    == #group.title
    #for m in group.measures [
      === #m.naam
      *Dekking:* #m.coverage

      #m.help_short
    ]
  ]
]

= Flow rates

Gewogen gemiddelde rates over LDEN-bands (zelfde bron als de simulator: `flow_size.csv`). *Gebruikt in deze run* = active als de maatregel ruimtelijk aanstaat, anders baseline.

#table(
  columns: (2.1fr, 0.7fr, 0.75fr, 0.75fr, 0.75fr, 0.55fr),
  stroke: 0.35pt + rgb("#A68BB8"),
  inset: 5pt,
  fill: (_, y) => if y == 0 { rgb("#4E2567") } else if calc.odd(y) { rgb("#F7F2FA") } else { white },
  text(fill: white, size: 9pt, weight: "bold")[Maatregel],
  text(fill: white, size: 9pt, weight: "bold")[Mode],
  text(fill: white, size: 9pt, weight: "bold")[Baseline],
  text(fill: white, size: 9pt, weight: "bold")[Active],
  text(fill: white, size: 9pt, weight: "bold")[Gebruikt],
  text(fill: white, size: 9pt, weight: "bold")[Aan?],
  ..for r in data.flow_rates {
    (
      text(size: 8.5pt)[#r.naam],
      text(size: 8.5pt)[#r.mode],
      text(size: 8.5pt)[#r.baseline_pct],
      text(size: 8.5pt)[#r.active_pct],
      text(size: 8.5pt)[#r.used_pct],
      text(size: 8.5pt)[#r.applied],
    )
  },
)

= Stock-evolutie (totaal)

#table(
  columns: (2.2fr, 1fr, 1fr, 0.9fr),
  stroke: 0.4pt + rgb("#A68BB8"),
  inset: 6pt,
  fill: (_, y) => if y == 0 { rgb("#4E2567") } else if calc.odd(y) { rgb("#F7F2FA") } else { white },
  text(fill: white, weight: "bold")[Stock],
  text(fill: white, weight: "bold")[#str(data.beginjaar)],
  text(fill: white, weight: "bold")[#str(data.eindjaar)],
  text(fill: white, weight: "bold")[Δ %],
  ..for s in data.stocks {
    (s.label, s.begin, s.eind, s.delta_pct)
  },
)

= Methodiek en aannames

- Simulatiehorizon: #str(data.beginjaar)–#str(data.eindjaar) op Lden-contour (1 dB-bands, geaggregeerd naar zones A–F).
- Omrekening: #str(data.personen_per_woonunit) personen per woonunit (config).
- Flow rates per band komen uit de analyse-export (`input/flow_size.csv`); sommige rates bevatten *placeholders* (expertinschatting) tot betere brondata beschikbaar is.
- Kosten zijn modelmatig: `|baseline − effectief| × stock × eenheidsprijs × rel_cost` (overheid/privé), gesommeerd over jaren en bands. Zie sectie *Kosten over het traject*.
- Dit document is automatisch gegenereerd vanuit de dashboardselectie op #data.exported_at.

== Berekening ernstig gehinderden

*Gekozen methode:* #data.ernstig_methode.label (#data.ernstig_methode.code).

#data.ernstig_methode.short

#for b in data.ernstig_methode.bullets [
  - #b
]
