"""Kolommapping en documentatie voor sector–contour-overlap Vlaanderen."""

from __future__ import annotations

import streamlit as st

KOLOM_HERNAMING = {
    "Identifiant intersection LDEN contour de bruit": "id_inter_ss_lden",
    "geometrie intersection secteur statitstique et contour de bruit Lden": "geometrie_inter_ss_lden",
    "NIS secteur statistique": "nis_sector",
    "géométrie secteur statistique": "geometrie_sector",
    "Nom secteur statistique NL": "naam_sector_nl",
    "Nom secteur statistique FR": "naam_sector_fr",
    "NIS commune": "nis_gemeente",
    "Nom commune NL": "naam_gemeente_nl",
    "Nom commune FR": "naam_gemeente_fr",
    "NIS arrondissement": "nis_arrondissement",
    "Nom arrondissement NL": "naam_arrondissement_nl",
    "Nom arrondissement FR": "naam_arrondissement_fr",
    "NIS province": "nis_provincie",
    "Nom province NL": "naam_provincie_nl",
    "Nom province FR": "naam_provincie_fr",
    "NIS région": "nis_regio",
    "Région NL": "regio_nl",
    "Région FR": "regio_fr",
    "Surface secteur statistique en m2": "oppervlakte_sector_m2",
    "dB Lden": "db_lden",
    "Surface (m2) section de secteur statistique intersectée avec contour de bruit": "oppervlakte_overlap_m2",
    "Part de la surface du secteur statistique dans le noise contour": "aandeel_sector_in_contour",
    "Population totale 2024 secteur statistique": "inwoners_sector_totaal_2024",
    "Population attribuée à la section de secteur statistique intersectée avec le contour de bruit": "inwoners_overlap",
    "Population à partir des données transmises par le client ": "inwoners_client",
    "Nombre de bâtiment résidentiel": "aantal_woningen",
}

KOLOM_GROEPEN = [
    {
        "titel": "Identificatie",
        "beschrijving": "Sleutels om elke rij uniek te identificeren.",
        "kolommen": [
            (
                "id_inter_ss_lden",
                "Uniek identificatienummer van de overlap tussen een statistische sector "
                "en een LDEN-geluidscontour (per 1 dB-band). Komt overeen met `fid` in andere contourbestanden.",
            ),
        ],
    },
    {
        "titel": "Geometrie",
        "beschrijving": "Ruimtelijke polygonen in Lambert 72 (EPSG:31370).",
        "kolommen": [
            (
                "geometrie_inter_ss_lden",
                "Polygon van het overlappende deel: het gedeelte van de statistische sector "
                "dat binnen de LDEN-geluidscontour valt.",
            ),
            (
                "geometrie_sector",
                "Polygon van de volledige statistische sector, onafhankelijk van de geluidscontour.",
            ),
        ],
    },
    {
        "titel": "Statistische sector",
        "beschrijving": "Kleinste ruimtelijke eenheid van de Belgische statistiek.",
        "kolommen": [
            ("nis_sector", "NIS-code van de statistische sector."),
            ("naam_sector_nl", "Naam van de sector in het Nederlands."),
            ("naam_sector_fr", "Naam van de sector in het Frans."),
        ],
    },
    {
        "titel": "Gemeente",
        "beschrijving": "Administratieve gemeente waartoe de sector behoort.",
        "kolommen": [
            ("nis_gemeente", "NIS-code van de gemeente."),
            ("naam_gemeente_nl", "Gemeentenaam in het Nederlands."),
            ("naam_gemeente_fr", "Gemeentenaam in het Frans."),
        ],
    },
    {
        "titel": "Arrondissement & provincie",
        "beschrijving": "Bovenliggende administratieve niveaus.",
        "kolommen": [
            ("nis_arrondissement", "NIS-code van het arrondissement."),
            ("naam_arrondissement_nl", "Naam van het arrondissement in het Nederlands."),
            ("naam_arrondissement_fr", "Naam van het arrondissement in het Frans."),
            ("nis_provincie", "NIS-code van de provincie."),
            ("naam_provincie_nl", "Naam van de provincie in het Nederlands."),
            ("naam_provincie_fr", "Naam van de provincie in het Frans."),
        ],
    },
    {
        "titel": "Regio",
        "beschrijving": "Gewestniveau (Vlaams Gewest of Brussels Hoofdstedelijk Gewest).",
        "kolommen": [
            ("nis_regio", "NIS-code van de regio."),
            ("regio_nl", "Naam van de regio in het Nederlands."),
            ("regio_fr", "Naam van de regio in het Frans."),
        ],
    },
    {
        "titel": "Oppervlakte & geluidscontour",
        "beschrijving": "Ruimtelijke koppeling tussen sector en LDEN-contour.",
        "kolommen": [
            (
                "oppervlakte_sector_m2",
                "Totale oppervlakte van de statistische sector, uitgedrukt in vierkante meter.",
            ),
            (
                "db_lden",
                "Ondergrens van de LDEN-geluidsband in decibel (bijv. 55 = band 55–56 dB).",
            ),
            (
                "oppervlakte_overlap_m2",
                "Oppervlakte van het overlappende deel tussen sector en contour, in m².",
            ),
            (
                "aandeel_sector_in_contour",
                "Fractie van de sectoroppervlakte die binnen de geluidscontour ligt "
                "(0–1, of als percentage).",
            ),
        ],
    },
    {
        "titel": "Inwoners",
        "beschrijving": "Bevolkingscijfers 2024, op sector- en overlapniveau.",
        "kolommen": [
            (
                "inwoners_sector_totaal_2024",
                "Totaal aantal inwoners in de volledige statistische sector (2024).",
            ),
            (
                "inwoners_overlap",
                "Inwoners toegewezen aan het overlappende deel, proportioneel op basis "
                "van de overlapoppervlakte ten opzichte van de sector.",
            ),
            (
                "inwoners_client",
                "Inwoners op basis van door de klant aangeleverde data (Departement Omgeving): "
                "woningniveau voor Vlaanderen, toegekend via GIS aan de sector–contour-overlap.",
            ),
        ],
    },
    {
        "titel": "Woningen",
        "beschrijving": "Gebouwenteller op overlapniveau.",
        "kolommen": [
            (
                "aantal_woningen",
                "Aantal residentiële gebouwen (woningen) in de overlap tussen sector en contour.",
            ),
        ],
    },
]


def toon_kolomdocumentatie() -> None:
    st.markdown(
        """
        <style>
        .kolom-doc-intro {
            color: #4a4a5a;
            font-size: 0.95rem;
            line-height: 1.6;
            margin-bottom: 1.25rem;
        }
        .kolom-groep {
            border-left: 3px solid #4E2567;
            padding: 0.6rem 0 0.6rem 1rem;
            margin-bottom: 1.5rem;
        }
        .kolom-groep-titel {
            color: #4E2567;
            font-size: 1.05rem;
            font-weight: 600;
            margin: 0 0 0.2rem 0;
        }
        .kolom-groep-beschrijving {
            color: #6b6b7b;
            font-size: 0.85rem;
            margin: 0 0 0.75rem 0;
        }
        .kolom-kaart {
            background: #f8f6fa;
            border-radius: 6px;
            padding: 0.55rem 0.75rem;
            margin-bottom: 0.45rem;
        }
        .kolom-naam {
            background: #ede8f2;
            color: #4E2567;
            font-family: monospace;
            font-size: 0.88rem;
            padding: 0.1rem 0.35rem;
            border-radius: 4px;
        }
        .kolom-uitleg {
            color: #3a3a4a;
            font-size: 0.88rem;
            line-height: 1.5;
            margin: 0.35rem 0 0 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p class="kolom-doc-intro">'
        "Elke rij beschrijft één <strong>overlap</strong> tussen een statistische sector "
        "en een LDEN-geluidscontour (1 dB-band). "
        f"Het bestand bevat <strong>{len(KOLOM_HERNAMING)} kolommen</strong>, "
        "hernoemd vanuit de Franse bronkolommen naar Nederlandse technische namen."
        "</p>",
        unsafe_allow_html=True,
    )

    for groep in KOLOM_GROEPEN:
        kaarten = "\n".join(
            f'<div class="kolom-kaart">'
            f'<code class="kolom-naam">{naam}</code>'
            f'<p class="kolom-uitleg">{uitleg}</p>'
            f"</div>"
            for naam, uitleg in groep["kolommen"]
        )
        st.markdown(
            f'<div class="kolom-groep">'
            f'<p class="kolom-groep-titel">{groep["titel"]}</p>'
            f'<p class="kolom-groep-beschrijving">{groep["beschrijving"]}</p>'
            f"{kaarten}"
            f"</div>",
            unsafe_allow_html=True,
        )
