import streamlit as st
import plotly.express as px


# =====================================================
# KPI
# =====================================================

def afficher_kpi(base):

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "📦 OPCVM",
        base["CODE ISIN"].nunique()
    )

    c2.metric(
        "📂 Catégories",
        base["Classification"].nunique()
    )

    c3.metric(
        "🏦 Sociétés",
        base["Société de Gestion"].nunique()
    )

    c4.metric(
        "💰 Actif Net (MAD)",
        f"{base['AN'].sum():,.0f}"
    )


# =====================================================
# Répartition catégories
# =====================================================

def graphique_categories(base):

    df = (
        base["Classification"]
        .value_counts()
        .reset_index()
    )

    df.columns = [
        "Classification",
        "Nombre"
    ]

    fig = px.pie(
        df,
        names="Classification",
        values="Nombre",
        hole=0.45,
        title="Répartition des OPCVM par catégorie"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

# =====================================================
# Répartition AN
# =====================================================

def graphique_actif(base):

    df = (
        base
        .groupby("Classification", as_index=False)["AN"]
        .sum()
    )

    fig = px.bar(
        df,
        x="Classification",
        y="AN",
        text="AN",
        title="Répartition de l'Actif Net"
    )

    fig.update_layout(
        height=450
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

# =====================================================
# Top 10 OPCVM
# =====================================================

def graphique_top10(scoring):

    df = (

        scoring

        .sort_values(
            "Score_Global",
            ascending=False
        )

        .head(10)

    )

    fig = px.bar(

        df,

        x="Score_Global",

        y="OPCVM",

        orientation="h",

        color="Classification",

        title="Top 10 OPCVM"

    )

    fig.update_layout(

        yaxis={"categoryorder":"total ascending"}

    )

    st.plotly_chart(
            fig,
            use_container_width=True
        )
    st.dataframe(
        df[
            [
                "OPCVM",
                "Classification",
                "Score_Global",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


# =====================================================
# Distribution Performance
# =====================================================

def graphique_performance(performance):

    fig = px.histogram(

        performance,

        x="Perf_YTD_calculee_%",

        nbins=30,

        title="Distribution des performances YTD"

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )
    st.dataframe(
        performance[
            [
                "OPCVM",
                "Classification",
                "Perf_YTD_calculee_%",
            ]
        ].sort_values(
            "Perf_YTD_calculee_%",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )


# =====================================================
# Distribution Volatilité
# =====================================================

def graphique_volatilite(risque):

    fig = px.histogram(

        risque,

        x="Volatilite_annualisee_%",

        nbins=30,

        title="Distribution des volatilités"

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )
    st.dataframe(
        risque[
            [
                "OPCVM",
                "Classification",
                "Volatilite_annualisee_%",
            ]
        ].sort_values(
            "Volatilite_annualisee_%",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )

# =====================================================
# Courbe historique VL
# =====================================================

def graphique_vl(vl, isin):

    if isin not in vl.columns:
        st.warning("Historique indisponible.")
        return

    df = (
        vl[[isin]]
        .dropna()
        .reset_index()
    )

    fig = px.line(
        df,
        x="Date",
        y=isin,
        title="Evolution de la Valeur Liquidative"
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="VL"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

import time

from datetime import datetime



import pandas as pd

import requests

from io import StringIO





# ==========================================================

# CONFIGURATION

# ==========================================================



BASE_URL = (

    "https://www.bkam.ma/export/blockcsv/2340/"

    "c3367fcefc5f524397748201aee5dab8/"

    "e1d6b9bbf87f86f8ba53e8518e882982"

)



HEADERS = {

    "User-Agent": "Mozilla/5.0"

}





# ==========================================================

# TELECHARGEMENT D'UNE COURBE

# ==========================================================



def telecharger_courbe(date_str):

    """

    Télécharge la courbe des taux BAM pour une date.

    """



    session = requests.Session()

    session.headers.update(HEADERS)



    params = {

        "date": date_str,

        "block": "e1d6b9bbf87f86f8ba53e8518e882982",

        "t": int(datetime.now().timestamp()),

    }



    r = session.get(

        BASE_URL,

        params=params,

        timeout=30,

    )



    r.raise_for_status()



    lignes = r.text.splitlines()



    if len(lignes) <= 3:

        raise ValueError(f"Aucune donnée pour {date_str}")



    csv = "\n".join(lignes[2:])



    df = pd.read_csv(

        StringIO(csv),

        sep=";",

        decimal=",",

    )



    # Suppression de la ligne Total

    df = df[

        df["Date d'échéance"] != "Total"

    ].copy()



    # Dates

    df["Date de la valeur"] = pd.to_datetime(

        df["Date de la valeur"],

        dayfirst=True,

    )



    df["Date d'échéance"] = pd.to_datetime(

        df["Date d'échéance"],

        dayfirst=True,

    )



    # Taux

    df["Taux"] = (

        df["Taux moyen pondéré"]

        .astype(str)

        .str.replace("%", "", regex=False)

        .str.replace(",", ".", regex=False)

        .str.strip()

        .astype(float)

    )



    # Transaction

    df["Transaction"] = pd.to_numeric(

        df["Transaction"]

        .astype(str)

        .str.replace(" ", "", regex=False)

        .str.replace(",", ".", regex=False),

        errors="coerce",

    )



    # Maturité résiduelle

    df["Maturite_annees"] = (

        (

            df["Date d'échéance"]

            - df["Date de la valeur"]

        ).dt.days

        / 365.25

    )



    # Date de référence

    df["Date_reference"] = pd.to_datetime(

        date_str,

        dayfirst=True,

    )



    return (

        df

        .sort_values("Maturite_annees")

        .reset_index(drop=True)

    )





# ==========================================================

# CONSTRUCTION DE L'HISTORIQUE COMPLET

# ==========================================================



def construire_courbe_bam(

    debut="2025-04-18",

    fin=None,

):

    """

    Télécharge toutes les courbes BAM disponibles.

    """



    if fin is None:

        fin = pd.Timestamp.today().normalize()



    dates = pd.date_range(

        start=debut,

        end=fin,

        freq="W-FRI",

    )



    courbes = []



    for d in dates:



        try:



            print(

                f"Téléchargement BAM : {d.date()}"

            )



            df = telecharger_courbe(

                d.strftime("%d/%m/%Y")

            )



            courbes.append(df)



            time.sleep(1)



        except Exception:



            continue



    if len(courbes) == 0:



        raise ValueError(

            "Impossible de télécharger les courbes BAM."

        )



    courbes = pd.concat(

        courbes,

        ignore_index=True,

    )



    # ======================================================

    # Segmentation CT / MT / LT

    # ======================================================



    courbes["Segment"] = pd.cut(



        courbes["Maturite_annees"],



        bins=[0, 2, 7, 100],



        labels=[

            "Court Terme",

            "Moyen Terme",

            "Long Terme",

        ],



        include_lowest=True,

    )



    return courbes
# =====================================================
# Pires performances
# =====================================================

def graphique_pires_performances(scoring):

    df = (
        scoring
        .sort_values("Perf_YTD_calculee_%")
        .head(10)
    )

    fig = px.bar(
        df,
        x="Perf_YTD_calculee_%",
        y="OPCVM",
        orientation="h",
        color="Classification",
        title="10 OPCVM les moins performants (YTD)",
    )

    fig.update_layout(
        yaxis={"categoryorder": "total ascending"}
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.dataframe(
        df[
            [
                "OPCVM",
                "Classification",
                "Perf_YTD_calculee_%",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )

# =====================================================
# Fonds les plus réguliers
# =====================================================

def graphique_plus_reguliers(risque):

    df = (
        risque
        .sort_values(
            "Pct_mois_positifs",
            ascending=False,
        )
        .head(10)
    )

    fig = px.bar(
        df,
        x="Pct_mois_positifs",
        y="OPCVM",
        orientation="h",
        color="Classification",
        title="Fonds les plus réguliers",
    )

    fig.update_layout(
        yaxis={"categoryorder": "total ascending"}
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.dataframe(
        df[
            [
                "OPCVM",
                "Classification",
                "Pct_mois_positifs",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )
# =====================================================
# Fonds les plus volatils
# =====================================================

def graphique_plus_volatils(risque):

    df = (
        risque
        .sort_values(
            "Volatilite_annualisee_%",
            ascending=False,
        )
        .head(10)
    )

    fig = px.bar(
        df,
        x="Volatilite_annualisee_%",
        y="OPCVM",
        orientation="h",
        color="Classification",
        title="Fonds les plus volatils",
    )

    fig.update_layout(
        yaxis={"categoryorder": "total ascending"}
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.dataframe(
        df[
            [
                "OPCVM",
                "Classification",
                "Volatilite_annualisee_%",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )
# =====================================================
# Rendement / Risque
# =====================================================

def graphique_ratio(risque):

    df = (
        risque
        .sort_values(
            "Ratio_Rendement_Volatilite",
            ascending=False,
        )
        .head(10)
    )

    fig = px.bar(
        df,
        x="Ratio_Rendement_Volatilite",
        y="OPCVM",
        orientation="h",
        color="Classification",
        title="Meilleur ratio rendement / risque",
    )

    fig.update_layout(
        yaxis={"categoryorder": "total ascending"}
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.dataframe(
        df[
            [
                "OPCVM",
                "Classification",
                "Ratio_Rendement_Volatilite",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )
# =====================================================
# Evolution des performances par catégorie
# =====================================================

def graphique_evolution_categorie(rendements, table_reference):

    categories = table_reference[
        ["CODE ISIN", "Classification"]
    ]

    data = rendements.T

    data["CODE ISIN"] = data.index

    data = data.merge(
        categories,
        on="CODE ISIN",
        how="left",
    )

    evolution = (
        data
        .groupby("Classification")
        .mean(numeric_only=True)
        .T
    )

    evolution = evolution * 100

    fig = px.line(
        evolution,
        title="Evolution moyenne des performances par catégorie",
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Performance (%)",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )
def graphique_rendement_volatilite(risque):

    df = risque.dropna(
        subset=[
            "Perf_YTD_calculee_%",
            "Volatilite_annualisee_%",
            "AN"
        ]
    )

    fig = px.scatter(
        df,
        x="Volatilite_annualisee_%",
        y="Perf_YTD_calculee_%",
        size="AN",
        color="Classification",
        hover_name="OPCVM",
        title="Rendement vs Volatilité",
        labels={
            "Volatilite_annualisee_%": "Volatilité annualisée (%)",
            "Perf_YTD_calculee_%": "Performance YTD (%)"
        },
        height=600,
    )

    fig.update_layout(template="plotly_white")

    st.plotly_chart(fig, use_container_width=True)