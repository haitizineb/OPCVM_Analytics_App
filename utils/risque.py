import numpy as np
import pandas as pd

"""
Calcul des indicateurs de risque des OPCVM.

Contient :
- volatilité annualisée
- maximum drawdown
- ratio rendement / volatilité
- classements
- sous-score risque
"""

def calculer_volatilite(rendements_hebdo):
    """
    Volatilité annualisée (%)
    """

    volatilite = (
        rendements_hebdo
        .drop(columns="Date", errors="ignore")
        .std(ddof=1)
        * np.sqrt(52)
        * 100
    )

    return volatilite

def calculer_drawdown(vl_historique):
    """
    Maximum Drawdown (%)
    """

    vl = vl_historique.drop(columns="Date", errors="ignore")

    plus_haut = vl.cummax()

    drawdown = (
        (vl - plus_haut)
        / plus_haut
    ) * 100

    return drawdown.min().abs()

def calculer_ratio(base):

    volatilite = (
        base["Volatilite_annualisee_%"]
        .replace(0, np.nan)
    )

    return (
        base["Perf_YTD_calculee_%"]
        / volatilite
    )

def construire_risque(
    base_opcvm,
    vl_historique,
    rendements_hebdo,
):

    risque = base_opcvm.copy()

    if "Sensibilité" in risque.columns:

        risque["Sensibilité"] = (
            risque["Sensibilité"]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .str.replace("%", "", regex=False)
        )

        risque["Sensibilité"] = pd.to_numeric(
            risque["Sensibilité"],
            errors="coerce",
        )

    volatilite = calculer_volatilite(
        rendements_hebdo
    )

    drawdown = calculer_drawdown(
        vl_historique
    )

    risque["Volatilite_annualisee_%"] = (
        risque["CODE ISIN"]
        .map(volatilite)
    )

    risque["Max_Drawdown_%"] = (
        risque["CODE ISIN"]
        .map(drawdown)
    )

    risque["Ratio_Rendement_Volatilite"] = (
        calculer_ratio(risque)
    )
    risque.replace(
        [np.inf, -np.inf],
        np.nan,
        inplace=True,
    )
    return risque

def ajouter_classements(risque):

    base = risque.copy()

    base["Rang_Volatilite"] = (

        base.groupby("Classification")[
            "Volatilite_annualisee_%"
        ]

        .rank(
            ascending=True,
            method="dense",
        )

    )

    base["Rang_Drawdown"] = (

        base.groupby("Classification")[
            "Max_Drawdown_%"
        ]

        .rank(
            ascending=True,
            method="dense",
        )

    )

    base["Rang_Ratios"] = (

        base.groupby("Classification")[
            "Ratio_Rendement_Volatilite"
        ]

        .rank(
            ascending=False,
            method="dense",
        )

    )

    return base

def ajouter_score(risque):

    base = risque.copy()

    base["Sous_Score_Risque"] = (

        base["Rang_Volatilite"]
        +
        base["Rang_Drawdown"]
        +
        base["Rang_Ratios"]

    ) / 3

    return base

