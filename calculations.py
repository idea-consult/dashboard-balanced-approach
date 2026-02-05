import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")
# onbebouwde bebouwbare onbebouwde_bebouwbare_percelen st
# woningen
df_stock = pd.read_csv("input/stock.csv")
df_flow_u = pd.read_csv("input/flow.csv")

with st.sidebar:
    "Kies welke maatregelen worden toegepast."
    df_flow = st.data_editor(
        df_flow_u,
        column_order=("naam", "maatregel_toepassen"),
        hide_index=True,
        height="content",
    )

df_stock.set_index(["naam", "jaar", "zone"], inplace=True)
df_flow.set_index(["naam", "zone"], inplace=True)


def set_aantal(naam, jaar, zone, aantal):
    df_stock.loc[(naam, jaar, zone), "aantal"] = aantal
    df_stock.sort_index(inplace=True)


def get_aantal(naam, jaar, zone):
    return df_stock.loc[(naam, jaar, zone), "aantal"]


def get_flow(naam, zone):
    maatregel_toepassen = df_flow.loc[(naam, zone), "maatregel_toepassen"]
    if maatregel_toepassen:
        print(f"De maatregel '{naam}' wordt wel toegepast.")
        return df_flow.loc[(naam, zone), "waarde_na_maatregel"]
    else:
        print(f"De maatregel '{naam}' wordt niet toegepast.")
        return df_flow.loc[(naam, zone), "waarde_normaal"]


zones = ("A", "B", "C", "D", "E")

begin_jaar = 2026
looptijd = 5  # in jaar

jaren = range(2026, begin_jaar + looptijd)
for j in jaren:
    print(j)
    for z in zones:
        print(z)
        # * Onbebouwde bebouwbare onbebouwde_bebouwbare_percelen
        huidige_onbebouwde_bebouwbare_percelen = get_aantal(
            "onbebouwde_bebouwbare_percelen", j, z
        )

        bijkomende_percelen_opsplitsing = (
            huidige_onbebouwde_bebouwbare_percelen
            * get_flow("woonverdichtingsverbod_percelen", "A")
        )
        bijkomende_percelen_woongebied = (
            huidige_onbebouwde_bebouwbare_percelen * get_flow("woongebiedverbod", "A")
        )

        percelen_gekocht_door_overheid = (
            huidige_onbebouwde_bebouwbare_percelen
            * get_flow("aankoopbeleid_percelen", "A")
            + huidige_onbebouwde_bebouwbare_percelen
            * get_flow("voorkooprecht_percelen", "A")
        )

        onteigende_percelen = huidige_onbebouwde_bebouwbare_percelen * get_flow(
            "onteigening_percelen", "A"
        )

        vergunde_kleine_woningen = huidige_onbebouwde_bebouwbare_percelen * get_flow(
            "verbod_kleine_woning", "A"
        )
        vergunde_grote_woningen = huidige_onbebouwde_bebouwbare_percelen * get_flow(
            "verbod_grote_woning", "A"
        )
        vergunde_kwetsbare_groepen = huidige_onbebouwde_bebouwbare_percelen * get_flow(
            "verbod_grote_woning", "A"
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
            * get_flow("woonverdichtingsverbod_woningen", "A")
        )
        bijkomende_geisoleerde_woningen_opsplitsing = (
            huidige_geisoleerde_woningen
            * get_flow("woonverdichtingsverbod_woningen", "A")
        )
        onteigende_niet_geisoleerde_woningen = (
            huidige_niet_geisoleerde_woningen * get_flow("onteigening_woningen", "A")
        )
        onteigende_geisoleerde_woningen = huidige_geisoleerde_woningen * get_flow(
            "onteigening_woningen", "A"
        )

        niet_geisoleerde_woningen_gekocht_door_overheid = (
            huidige_niet_geisoleerde_woningen * get_flow("aankoopbeleid_woningen", "A")
            + huidige_niet_geisoleerde_woningen
            * get_flow("voorkooprecht_woningen", "A")
        )
        geisoleerde_woningen_gekocht_door_overheid = (
            huidige_geisoleerde_woningen * get_flow("aankoopbeleid_woningen", "A")
            + huidige_geisoleerde_woningen * get_flow("voorkooprecht_woningen", "A")
        )

        isolatie_huidige_woningen = (
            huidige_niet_geisoleerde_woningen
            * get_flow("verplicht_isoleren_renovatie", "A")
            + huidige_niet_geisoleerde_woningen
            * get_flow("gesubsidieerd_isolatieprogramma", "A")
            + huidige_niet_geisoleerde_woningen
            * get_flow("gestuurd_isolatieprogramma", "A")
            + huidige_niet_geisoleerde_woningen * get_flow("aanleg_geluidsbuffers", "A")
        )

        bijkomende_geisoleerde_woningen = bijkomende_woningen * get_flow(
            "isolatievoorschriften_nieuwbouw", "A"
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

        if df_flow.loc[("landingsbaan_verschuiven", "A"), "maatregel_toepassen"]:
            continue


df_stock.to_csv("output/stock.csv")

import altair as alt

with st.sidebar:
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
    .properties(title="Evolutie van niet geïsoleerde woningen per zone")
)
with col2:
    st.altair_chart(niet_geisoleerde_woningen_chart)
    st.altair_chart(geisoleerde_woningen_chart)
