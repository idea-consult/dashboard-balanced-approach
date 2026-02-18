import pandas as pd
import streamlit as st
import os

# ---- CONFIG ----
ACCESS_CODE = os.getenv("ACCESS_CODE", "code")  
# Better to set via environment variable on your host

# ---- AUTH ----
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        password = st.text_input("Enter access code", type="password")
        if password:
            if password == ACCESS_CODE:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect code")
        st.stop()

check_password()

from util.helpers import (
    get_hinder_punten,
    get_hinder_punten_met_isolatie,
    get_hinder_punten_zonder_isolatie,
)

st.set_page_config(layout="wide")
# onbebouwde bebouwbare onbebouwde_bebouwbare_percelen st
# woningen
df_stock = pd.read_csv("input/stock.csv")
df_flow = pd.read_csv("input/flow.csv")
df_beschrijving_maatregelen = pd.read_csv("input/beschrijving_maatregelen.csv")

zones = ("A", "B", "C", "D", "E")

df_stock.set_index(["naam", "jaar", "zone"], inplace=True)
df_stock = df_stock.sort_index()
# df_flow.set_index(["naam", "zone"], inplace=True)

df_flow = df_flow.set_index(["naam", "zone"], verify_integrity=True).sort_index()
df_beschrijving_maatregelen = df_beschrijving_maatregelen.set_index(
    ["naam"], verify_integrity=True
)


def set_aantal(naam, jaar, zone, aantal):
    df_stock.loc[(naam, jaar, zone), "aantal"] = aantal
    df_stock.sort_index(inplace=True)


def get_aantal(naam, jaar, zone):
    return df_stock.loc[(naam, jaar, zone), "aantal"]


def get_selected_zones(df, maatregel_naam):
    subset = df.loc[maatregel_naam]
    return tuple(subset.index[subset["maatregel_toepassen"]])


def set_selected_zones(df, maatregel_naam, selected_zones):
    idx = pd.IndexSlice
    df.loc[idx[maatregel_naam, :], "maatregel_toepassen"] = (
        df.loc[idx[maatregel_naam, :]]
        .index.get_level_values("zone")
        .isin(selected_zones)
    )


with st.sidebar:
    for maatregel in df_beschrijving_maatregelen.index.get_level_values("naam"):
        selected = st.segmented_control(
            label=df_beschrijving_maatregelen.at[maatregel, "naam_mooi"],
            options=zones,
            help=df_beschrijving_maatregelen.at[maatregel, "help"],
            selection_mode="multi",
            default=get_selected_zones(df_flow, maatregel),
            key=f"seg_{maatregel}",
            width="stretch",
        )

        set_selected_zones(df_flow, maatregel, selected)


def get_flow(naam, zone):
    maatregel_toepassen = df_flow.loc[(naam, zone), "maatregel_toepassen"]

    if maatregel_toepassen:
        return df_flow.loc[(naam, zone), "waarde_na_maatregel"]
    else:
        return df_flow.loc[(naam, zone), "waarde_normaal"]


personen_per_woonunit = 2

woon_units_per_kleinschalige_woning = 1.2
woon_units_per_grootschalige_woning = 60


beginjaar = 2026
looptijd = 5  # in jaar
eindjaar = beginjaar + looptijd
hinderpunten = 0
for z in zones:
    niet_geisoleerde_woningen = get_aantal("niet_geisoleerde_woningen", beginjaar, z)
    geisoleerde_woningen = get_aantal("geisoleerde_woningen", beginjaar, z)
    set_aantal(
        "hinderpunten",
        beginjaar,
        z,
        get_hinder_punten(
            niet_geisoleerde_woningen * personen_per_woonunit,
            geisoleerde_woningen * personen_per_woonunit,
            z,
        ),
    )
    set_aantal(
        "hinderpunten_isolatie",
        beginjaar,
        z,
        get_hinder_punten_zonder_isolatie(
            niet_geisoleerde_woningen * personen_per_woonunit,
            z,
        ),
    )
    set_aantal(
        "hinderpunten_zonder_isolatie",
        beginjaar,
        z,
        get_hinder_punten_met_isolatie(geisoleerde_woningen * personen_per_woonunit, z),
    )
    set_aantal(
        "gehinderde_personen_zonder_isolatie",
        beginjaar,
        z,
        niet_geisoleerde_woningen * personen_per_woonunit,
    )
    set_aantal(
        "gehinderde_personen_met_isolatie",
        beginjaar,
        z,
        geisoleerde_woningen * personen_per_woonunit,
    )
    set_aantal(
        "totaal_gehinderde_personen",
        beginjaar,
        z,
        niet_geisoleerde_woningen * personen_per_woonunit
        + geisoleerde_woningen * personen_per_woonunit,
    )

jaren = range(beginjaar, eindjaar)
for j in jaren:
    print(f"JAAR: {j}")
    for z in zones:
        print(f"ZONE: {z}")
        # * Onbebouwde bebouwbare onbebouwde_bebouwbare_percelen
        huidige_onbebouwde_bebouwbare_percelen = get_aantal(
            "onbebouwde_bebouwbare_percelen", j, z
        )
        bijkomende_percelen_opsplitsing = (
            huidige_onbebouwde_bebouwbare_percelen * get_flow("verkavelingsverbod", z)
        )
        bijkomende_percelen_woongebied = (
            huidige_onbebouwde_bebouwbare_percelen * get_flow("woongebiedverbod", z)
        )

        percelen_gekocht_door_overheid = (
            huidige_onbebouwde_bebouwbare_percelen
            * get_flow("aankoopbeleid_percelen", z)
            + huidige_onbebouwde_bebouwbare_percelen
            * get_flow("voorkooprecht_percelen", z)
        )

        onteigende_percelen = huidige_onbebouwde_bebouwbare_percelen * get_flow(
            "onteigening_percelen", z
        )

        vergunde_kleine_woningen = huidige_onbebouwde_bebouwbare_percelen * get_flow(
            "verbod_kleine_woning", z
        )
        vergunde_grote_woningen = huidige_onbebouwde_bebouwbare_percelen * get_flow(
            "verbod_grote_woning", z
        )
        vergunde_kwetsbare_groepen = huidige_onbebouwde_bebouwbare_percelen * get_flow(
            "verbod_kwetsbare_groep", z
        )

        toekomstige_onbebouwde_bebouwbare_percelen = (
            huidige_onbebouwde_bebouwbare_percelen
            + bijkomende_percelen_opsplitsing
            + bijkomende_percelen_woongebied
            - percelen_gekocht_door_overheid
            - onteigende_percelen
            - vergunde_kleine_woningen
            - vergunde_grote_woningen
            - vergunde_kwetsbare_groepen
        )

        set_aantal(
            "onbebouwde_bebouwbare_percelen",
            j + 1,
            z,
            toekomstige_onbebouwde_bebouwbare_percelen,
        )

        toekomstige_onbebouwde_onbebouwbare_percelen = (
            percelen_gekocht_door_overheid + onteigende_percelen
        )
        set_aantal(
            "onbebouwde_onbebouwbare_percelen",
            j + 1,
            z,
            toekomstige_onbebouwde_bebouwbare_percelen,
        )

        bijkomende_woningen = (
            vergunde_grote_woningen
            + vergunde_kleine_woningen
            + vergunde_kwetsbare_groepen
        )

        # * Woningen
        huidige_niet_geisoleerde_woningen = get_aantal(
            "niet_geisoleerde_woningen", j, z
        )
        huidige_geisoleerde_woningen = get_aantal("geisoleerde_woningen", j, z)

        bijkomende_niet_geisoleerde_woningen_opsplitsing = (
            huidige_niet_geisoleerde_woningen
            * get_flow("woonverdichtingsverbod_woningen", z)
        )
        bijkomende_geisoleerde_woningen_opsplitsing = (
            huidige_geisoleerde_woningen
            * get_flow("woonverdichtingsverbod_woningen", z)
        )
        onteigende_niet_geisoleerde_woningen = (
            huidige_niet_geisoleerde_woningen * get_flow("onteigening_woningen", z)
        )
        onteigende_geisoleerde_woningen = huidige_geisoleerde_woningen * get_flow(
            "onteigening_woningen", z
        )

        niet_geisoleerde_woningen_gekocht_door_overheid = (
            huidige_niet_geisoleerde_woningen * get_flow("aankoopbeleid_woningen", z)
            + huidige_niet_geisoleerde_woningen * get_flow("voorkooprecht_woningen", z)
        )
        geisoleerde_woningen_gekocht_door_overheid = (
            huidige_geisoleerde_woningen * get_flow("aankoopbeleid_woningen", z)
            + huidige_geisoleerde_woningen * get_flow("voorkooprecht_woningen", z)
        )

        isolatie_huidige_woningen = (
            huidige_niet_geisoleerde_woningen
            * get_flow("verplicht_isoleren_renovatie", z)
            + huidige_niet_geisoleerde_woningen
            * get_flow("gesubsidieerd_isolatieprogramma", z)
            + huidige_niet_geisoleerde_woningen
            * get_flow("gestuurd_isolatieprogramma", z)
            + huidige_niet_geisoleerde_woningen * get_flow("aanleg_geluidsbuffers", z)
        )

        bijkomende_geisoleerde_woningen = bijkomende_woningen * get_flow(
            "isolatievoorschriften_nieuwbouw", z
        )
        bijkomende_niet_geisoleerde_woningen = (
            bijkomende_woningen - bijkomende_geisoleerde_woningen
        )

        toekomstige_niet_geisoleerde_woningen = (
            huidige_niet_geisoleerde_woningen
            + bijkomende_niet_geisoleerde_woningen
            - isolatie_huidige_woningen  # Dit zijn bestaande huizen die geïsoleerd worden.
            - niet_geisoleerde_woningen_gekocht_door_overheid
            - onteigende_niet_geisoleerde_woningen
        )
        toekomstige_geisoleerde_woningen = (
            huidige_geisoleerde_woningen
            + bijkomende_geisoleerde_woningen
            + isolatie_huidige_woningen  # Dit zijn bestaande huizen die geïsoleerd worden.
            - geisoleerde_woningen_gekocht_door_overheid
            - onteigende_geisoleerde_woningen
        )
        toekomstige_leegstaande_woningen = (
            niet_geisoleerde_woningen_gekocht_door_overheid
            + onteigende_niet_geisoleerde_woningen
            + onteigende_geisoleerde_woningen
        )
        set_aantal(
            "niet_geisoleerde_woningen", j + 1, z, toekomstige_niet_geisoleerde_woningen
        )
        set_aantal("geisoleerde_woningen", j + 1, z, toekomstige_geisoleerde_woningen)
        set_aantal("leegstaande_woningen", j + 1, z, toekomstige_leegstaande_woningen)
        gehinderde_personen_zonder_isolatie = (
            toekomstige_niet_geisoleerde_woningen * personen_per_woonunit
        )
        set_aantal(
            "gehinderde_personen_zonder_isolatie",
            j + 1,
            z,
            gehinderde_personen_zonder_isolatie,
        )
        gehinderde_personen_met_isolatie = (
            toekomstige_geisoleerde_woningen * personen_per_woonunit
        )
        set_aantal(
            "gehinderde_personen_met_isolatie",
            j + 1,
            z,
            gehinderde_personen_met_isolatie,
        )
        set_aantal(
            "totaal_gehinderde_personen",
            j + 1,
            z,
            gehinderde_personen_met_isolatie + gehinderde_personen_zonder_isolatie,
        )

        hinderpunten = get_hinder_punten(
            gehinderde_personen_zonder_isolatie, gehinderde_personen_met_isolatie, z
        )
        set_aantal(
            "hinderpunten",
            j + 1,
            z,
            int(hinderpunten),
        )
        set_aantal(
            "hinderpunten_isolatie",
            j + 1,
            z,
            get_hinder_punten_zonder_isolatie(
                gehinderde_personen_zonder_isolatie,
                z,
            ),
        )
        set_aantal(
            "hinderpunten_zonder_isolatie",
            j + 1,
            z,
            get_hinder_punten_met_isolatie(
                gehinderde_personen_met_isolatie,
                z,
            ),
        )

        if df_flow.loc[("landingsbaan_verschuiven", z), "maatregel_toepassen"]:
            continue


df_totalen = pd.DataFrame()
for j in range(beginjaar, eindjaar + 1):
    set_aantal(
        "gehinderde_personen_met_isolatie",
        j,
        "Totaal",
        sum(
            df_stock.loc[("gehinderde_personen_met_isolatie", j, z), "aantal"]
            for z in zones
        ),
    )
    set_aantal(
        "gehinderde_personen_zonder_isolatie",
        j,
        "Totaal",
        sum(
            df_stock.loc[("gehinderde_personen_zonder_isolatie", j, z), "aantal"]
            for z in zones
        ),
    )
    set_aantal(
        "hinderpunten",
        j,
        "Totaal",
        sum(df_stock.loc[("hinderpunten", j, z), "aantal"] for z in zones),
    )
    set_aantal(
        "hinderpunten_isolatie",
        j,
        "Totaal",
        sum(df_stock.loc[("hinderpunten_isolatie", j, z), "aantal"] for z in zones),
    )
    set_aantal(
        "hinderpunten_zonder_isolatie",
        j,
        "Totaal",
        sum(
            df_stock.loc[("hinderpunten_zonder_isolatie", j, z), "aantal"]
            for z in zones
        ),
    )
    set_aantal(
        "totaal_gehinderde_personen",
        j,
        "Totaal",
        sum(
            df_stock.loc[("totaal_gehinderde_personen", j, z), "aantal"] for z in zones
        ),
    )


def change_metric(metric, mooie_naam):
    begin = get_aantal(metric, beginjaar, "Totaal")
    eind = get_aantal(metric, eindjaar, "Totaal")
    return st.metric(
        mooie_naam,
        f"{int(eind)}",
        f"{int(100* (eind - begin) / begin)} %",
        delta_color="inverse",
    )


df_stock.to_csv("output/stock.csv")

import altair as alt


links, midden, rechts = st.columns(3)
with links:
    
    change_metric("hinderpunten_isolatie", "Hinderpunten voor mensen met isolatie")

    change_metric("gehinderde_personen_met_isolatie", "Gehinderde geïsoleerde personen")
with midden:
    change_metric("hinderpunten_zonder_isolatie", "Hinderpunten voor mensen zonder isolatie")
    change_metric(
        "gehinderde_personen_zonder_isolatie", "Gehinderde niet-geïsoleerde personen"
    )

with rechts:
    change_metric("hinderpunten", "Hinderpunten")

    change_metric("totaal_gehinderde_personen", "Totaal aantal gehinderde personen")

st.metric(
        "Totale kost van de maatregels",
        df_flow.loc[df_flow["maatregel_toepassen"], "kost_maatregel"].sum(),
        format="euro",
    )

col1, col2 = st.columns(2)

df_plot = df_stock.reset_index()
df_plot = df_plot[df_plot["naam"] == "onbebouwde_bebouwbare_percelen"]

onbebouwde_bebouwbare_percelen_chart = (
    alt.Chart(df_plot)
    .mark_line(point=True)
    .encode(
        x=alt.X("jaar:O", title="Jaar"),
        y=alt.Y("aantal:Q", title="# onbebouwde bebouwbare perc"),
        color=alt.Color("zone:N", title="Zone"),
        tooltip=["zone", "jaar", "aantal"],
    )
    .properties(title="Evolutie van onbebouwde bebouwbare percelen per zone")
)
onbebouwde_onbebouwbare_percelen_chart = (
    alt.Chart(df_plot)
    .mark_line(point=True)
    .encode(
        x=alt.X("jaar:O", title="Jaar"),
        y=alt.Y("aantal:Q", title="# onbebouwde onbebouwbare perc"),
        color=alt.Color("zone:N", title="Zone"),
        tooltip=["zone", "jaar", "aantal"],
    )
    .properties(title="Evolutie van onbebouwde onbebouwbare percelen per zone")
)
with col1:
    st.altair_chart(onbebouwde_bebouwbare_percelen_chart)
    st.altair_chart(onbebouwde_onbebouwbare_percelen_chart)

df_plot = df_stock.reset_index()
df_plot = df_plot[df_plot["naam"] == "niet_geisoleerde_woningen"]

niet_geisoleerde_woningen_chart = (
    alt.Chart(df_plot)
    .mark_line(point=True)
    .encode(
        x=alt.X("jaar:O", title="Jaar"),
        y=alt.Y("aantal:Q", title="Aantal woningen"),
        color=alt.Color("zone:N", title="Zone"),
        tooltip=["zone", "jaar", "aantal"],
    )
    .properties(title="Evolutie van niet geïsoleerde woningen per zone")
)

df_plot = df_stock.reset_index()
df_plot = df_plot[df_plot["naam"] == "geisoleerde_woningen"]

geisoleerde_woningen_chart = (
    alt.Chart(df_plot)
    .mark_line(point=True)
    .encode(
        x=alt.X("jaar:O", title="Jaar"),
        y=alt.Y("aantal:Q", title="Aantal woningen"),
        color=alt.Color("zone:N", title="Zone"),
        tooltip=["zone", "jaar", "aantal"],
    )
    .properties(title="Evolutie van geïsoleerde woningen per zone")
)
with col2:
    st.altair_chart(niet_geisoleerde_woningen_chart)
    st.altair_chart(geisoleerde_woningen_chart)
