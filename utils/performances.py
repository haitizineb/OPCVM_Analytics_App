from matplotlib import dates, table
import numpy as np
import pandas as pd
from pathlib import Path

# =====================================================
# HORIZONS
# =====================================================

HORIZONS = {
    "Perf_1_mois": 30,
    "Perf_3_mois": 91,
    "Perf_6_mois": 182,
    "Perf_1_an": 365,
    "Perf_3_ans": 365 * 3,
}

# =====================================================
# RENDEMENTS HEBDOMADAIRES
# =====================================================

def construire_rendements(
    vl_corrigee,
    log_ruptures=None,
):

    rendements = vl_corrigee.pct_change(fill_method=None)

    if log_ruptures is not None:

        for _, row in log_ruptures.iterrows():

            isin = row["CODE ISIN"]
            date = row["Date"]

            if (
                isin in rendements.columns
                and date in rendements.index
            ):
                rendements.loc[date, isin] = np.nan

    return rendements


# =====================================================
# PERFORMANCE CUMULÉE
# =====================================================

def performance_cumulee(
    vl_corrigee,
    isin,
    date_fin,
    jours,
    tolerance=10,
):

    serie = vl_corrigee[isin].dropna()

    if len(serie) < 2:
        return np.nan

    date_debut = (
        pd.Timestamp(date_fin)
        - pd.Timedelta(days=jours)
    )

    fenetre = serie.loc[
        (serie.index >= date_debut)
        &
        (serie.index <= pd.Timestamp(date_fin))
    ]

    if len(fenetre) < 2:
        return np.nan

    if serie.index.min() > date_debut + pd.Timedelta(days=tolerance):
        return np.nan

    return (
        fenetre.iloc[-1]
        / fenetre.iloc[0]
    ) - 1


# =====================================================
# PERFORMANCE YTD
# =====================================================

def performance_ytd(
    vl_corrigee,
    isin,
    date_fin,
):

    serie = vl_corrigee[isin].dropna()

    if len(serie) < 2:
        return np.nan

    debut = pd.Timestamp(
        year=date_fin.year,
        month=1,
        day=1,
    )

    fenetre = serie.loc[
        (serie.index >= debut)
        &
        (serie.index <= date_fin)
    ]

    if len(fenetre) < 2:
        return np.nan

    return (
        fenetre.iloc[-1]
        / fenetre.iloc[0]
    ) - 1


# =====================================================
# TABLE DES PERFORMANCES
# =====================================================

def construire_table_performances(vl_corrigee):

    date_ref = vl_corrigee.index.max()

    lignes = []

    for isin in vl_corrigee.columns:

        ligne = {
            "CODE ISIN": isin
        }

        for nom, jours in HORIZONS.items():

            ligne[nom] = performance_cumulee(
                vl_corrigee,
                isin,
                date_ref,
                jours,
            )

        ligne["Perf_YTD"] = performance_ytd(
            vl_corrigee,
            isin,
            date_ref,
        )

        lignes.append(ligne)
    table = pd.DataFrame(lignes)

    nb_exclus = table["Perf_YTD"].isna().sum()

    print(
        f"{nb_exclus} fonds exclus (historique insuffisant)."
    )

    return table
    return pd.DataFrame(lignes)

# =====================================================
# PERFORMANCE ANNUALISÉE
# =====================================================

def performance_annualisee(
    performance,
    nb_jours,
):

    if pd.isna(performance):
        return np.nan

    if performance <= -1:
        return np.nan

    return (
        (1 + performance) ** (365 / nb_jours)
    ) - 1


def ajouter_performances_annualisees(
    table_performances,
):

    table = table_performances.copy()

    correspondance = {
        "Perf_1_an": 365,
        "Perf_3_ans": 365 * 3,
    }

    for colonne, jours in correspondance.items():

        table[colonne + "_Annualisee"] = (
            table[colonne]
            .apply(
                lambda x:
                performance_annualisee(
                    x,
                    jours,
                )
            )
        )

    return table


# =====================================================
# VL ET RENDEMENTS MENSUELS
# =====================================================

def construire_rendements_mensuels(
    vl_corrigee,
):

    vl_mensuelle = (
        vl_corrigee
        .resample("ME")
        .last()
    )

    rendement_mensuel = (
        vl_mensuelle
        .pct_change(fill_method=None)
        * 100
    )

    return (
        vl_mensuelle,
        rendement_mensuel,
    )


# =====================================================
# RÉSUMÉ PERFORMANCE
# =====================================================

def construire_resume_performance(
    vl_corrigee,
):

    derniere_date = vl_corrigee.index.max()

    vl_actuelle = vl_corrigee.loc[derniere_date]

    vl_depart = vl_corrigee.iloc[0]

    perf_totale = (
        vl_actuelle
        / vl_depart
        - 1
    )

    nb_jours = (
        derniere_date
        - vl_corrigee.index.min()
    ).days

    perf_annualisee = (
        ((1 + perf_totale) ** (365 / nb_jours) - 1)
        * 100
    )

    annee = derniere_date.year

    date_ytd = pd.Timestamp(f"{annee-1}-12-31")

    vl_mensuelle, _ = construire_rendements_mensuels(
        vl_corrigee
    )

    dates = vl_mensuelle.index[
        vl_mensuelle.index <= date_ytd
    ]

    if len(dates) == 0:
        return pd.DataFrame({
            "Perf_YTD_calculee_%": np.nan,
            "Perf_annualisee_%": perf_annualisee,
        })

    debut = vl_mensuelle.loc[dates[-1]]

    perf_ytd = (
        (vl_actuelle / debut) - 1
    ) * 100

    return pd.DataFrame({

        "Perf_YTD_calculee_%":
            perf_ytd,

        "Perf_annualisee_%":
            perf_annualisee,

    })


# =====================================================
# RÉGULARITÉ
# =====================================================

def construire_regularite(
    rendement_mensuel,
):

    return pd.DataFrame({

        "Ecart_type_mensuel_%":
            rendement_mensuel.std(),

        "Pct_mois_positifs":
            (
                (rendement_mensuel > 0).sum()
                /
                rendement_mensuel.notna().sum()
            ) * 100,

    })
    
# =====================================================
# TABLE COMPLÈTE DES PERFORMANCES
# =====================================================

def construire_performance_complete(
    table_reference,
    table_performances,
    vl_corrigee,
):

    resume = construire_resume_performance(
        vl_corrigee
    )

    _, rendement_mensuel = (
        construire_rendements_mensuels(
            vl_corrigee
        )
    )

    regularite = construire_regularite(
        rendement_mensuel
    )

    meta = (
        table_reference
        .set_index("CODE ISIN")
    )

    perf = (
        meta
        .join(
            table_performances.set_index("CODE ISIN")
        )
        .join(resume)
        .join(regularite)
    )

    # ===================================
    # Rangs par catégorie
    # ===================================

    colonnes_perf = [
        "Perf_1_mois",
        "Perf_3_mois",
        "Perf_6_mois",
        "Perf_1_an",
        "Perf_3_ans",
        "Perf_YTD_calculee_%",
    ]

    for col in colonnes_perf:

        if col in perf.columns:

            perf[f"Rang_{col}"] = (

                perf
                .groupby("Classification")[col]
                .rank(
                    ascending=False,
                    method="dense",
                )

            )

    # ===================================
    # Tri
    # ===================================

    perf = perf.sort_values(
        [
            "Classification",
            "Rang_Perf_YTD_calculee_%",
        ]
        if "Rang_Perf_YTD_calculee_%"
        in perf.columns
        else "Classification"
    )

    return perf.reset_index()

# =====================================================
# CLASSEMENTS
# =====================================================

def top_performances(
    performance_complete,
    colonne="Perf_1_an",
    n=10,
):

    return (

        performance_complete

        .dropna(subset=[colonne])

        .sort_values(colonne, ascending=False)

        .head(n)

    )


def pires_performances(
    performance_complete,
    colonne="Perf_1_an",
    n=10,
):

    return (

        performance_complete

        .dropna(subset=[colonne])

        .sort_values(colonne, ascending=True)

        .head(n)

    )


# =====================================================
# STATISTIQUES PAR CATÉGORIE
# =====================================================

def statistiques_categories(
    performance_complete,
):

    return (

        performance_complete

        .groupby("Classification")

        .agg(

            Nb_Fonds=("OPCVM", "count"),

            Perf_1M_Moy=("Perf_1_mois", "mean"),

            Perf_3M_Moy=("Perf_3_mois", "mean"),

            Perf_6M_Moy=("Perf_6_mois", "mean"),

            Perf_1A_Moy=("Perf_1_an", "mean"),

            Perf_YTD_Moy=("Perf_YTD_calculee_%", "mean"),

            Perf_Ann_Moy=("Perf_annualisee_%", "mean"),

            Volatilite_Mensuelle=("Ecart_type_mensuel_%", "mean"),

            Regularite=("Pct_mois_positifs", "mean"),

        )

        .round(2)

        .reset_index()

    )


# =====================================================
# EXPORT
# =====================================================

def exporter_performances(
    performance_complete,
    fichier="data/performance_complete.xlsx",
):
    Path(fichier).parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(
        fichier,
        engine="openpyxl",
    ) as writer:

        performance_complete.to_excel(
            writer,
            sheet_name="Performances",
            index=False,
        )

        statistiques_categories(
            performance_complete
        ).to_excel(
            writer,
            sheet_name="Statistiques",
            index=False,
        )