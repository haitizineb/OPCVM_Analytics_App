import numpy as np
import pandas as pd
from pathlib import Path

from utils import risque


# =====================================================
# PONDÉRATIONS
# =====================================================

POIDS = {
    "Score_Performance": 0.30,
    "Score_Volatilite": 0.25,
    "Score_Regularite": 0.20,
    "Score_Drawdown": 0.15,
    "Score_Taille": 0.10,
}


# =====================================================
# SCORE PERCENTILE
# =====================================================

def score_percentile(serie, meilleur_grand=True):

    serie = pd.to_numeric(serie, errors="coerce")

    if serie.notna().sum() <= 1:
        return pd.Series(50.0, index=serie.index)

    if meilleur_grand:
        rang = serie.rank(
            ascending=True,
            method="average"
        )
    else:
        rang = serie.rank(
            ascending=False,
            method="average"
        )

    return rang / rang.max() * 100

# =====================================================
# CONSTRUCTION DU SCORING
# =====================================================

def construire_scoring(
    risque,
):

    scoring = risque.copy()
    colonnes_obligatoires = [
        "CODE ISIN",
        "OPCVM",
        "Société de Gestion",
        "Classification",
        "AN",
        "Perf_YTD_calculee_%",
        "Pct_mois_positifs",
        "Volatilite_annualisee_%",
        "Max_Drawdown_%",
    ]

    manquantes = [
        c for c in colonnes_obligatoires
        if c not in risque.columns
]

    if manquantes:
        raise ValueError(
            f"Colonnes manquantes : {manquantes}"
        )

    colonnes = [
        "CODE ISIN",
        "OPCVM",
        "Société de Gestion",
        "Classification",
        "AN",
        "Perf_YTD_calculee_%",
        "Pct_mois_positifs",
        "Volatilite_annualisee_%",
        "Max_Drawdown_%",
    ]

    scoring = scoring[colonnes].copy()

    # ===============================
    # Scores normalisés
    # ===============================

    scoring["Score_Performance"] = (
        scoring.groupby("Classification")["Perf_YTD_calculee_%"]
        .transform(lambda x: score_percentile(x, True))
    )

    scoring["Score_Volatilite"] = (
        scoring.groupby("Classification")["Volatilite_annualisee_%"]
        .transform(lambda x: score_percentile(x, False))
    )

    scoring["Score_Regularite"] = (
        scoring.groupby("Classification")["Pct_mois_positifs"]
        .transform(lambda x: score_percentile(x, True))
    )

    scoring["Score_Drawdown"] = (
        scoring.groupby("Classification")["Max_Drawdown_%"]
        .transform(lambda x: score_percentile(x, False))
    )


    if "AN" in scoring.columns:

        scoring["Score_Taille"] = (
        scoring.groupby("Classification")["AN"]
        .transform(lambda x: score_percentile(x, True))
     )

    else:

        scoring["Score_Taille"] = np.nan

    # ===============================
    # Score global
    # ===============================

    scoring["Score_Global"] = (

        scoring["Score_Performance"] * POIDS["Score_Performance"]

        + scoring["Score_Volatilite"] * POIDS["Score_Volatilite"]

        + scoring["Score_Regularite"] * POIDS["Score_Regularite"]

        + scoring["Score_Drawdown"] * POIDS["Score_Drawdown"]

        + scoring["Score_Taille"] * POIDS["Score_Taille"]

    )

    scoring["Rang_Categorie"] = (

        scoring

        .groupby("Classification")["Score_Global"]

        .rank(
            ascending=False,
            method="dense",
        )

    )

    scoring["Rang_Global"] = (

        scoring["Score_Global"]

        .rank(
            ascending=False,
            method="dense",
        )

    )

    return scoring



# =====================================================
# TOP N PAR CATÉGORIE
# =====================================================

def top_par_categorie(
    scoring,
    n=10,
):

    return (

        scoring

        .sort_values(
            ["Classification", "Score_Global"],
            ascending=[True, False],
        )

        .groupby("Classification")

        .head(n)

        .reset_index(drop=True)

    )


# =====================================================
# TOP GLOBAL
# =====================================================

def top_global(
    scoring,
    n=20,
):

    return (

        scoring

        .sort_values(
            "Score_Global",
            ascending=False,
        )

        .head(n)

        .reset_index(drop=True)

    )


# =====================================================
# EXPORT CSV
# =====================================================

def exporter_csv(
    scoring,
    dossier="data",
):

    dossier = Path(dossier)

    dossier.mkdir(
        parents=True,
        exist_ok=True
    )

    scoring.to_csv(
        dossier / "score_global.csv",
        index=False,
        encoding="utf-8-sig",
    )

    top_par_categorie(scoring).to_csv(
        dossier / "top10_par_categorie.csv",
        index=False,
        encoding="utf-8-sig",
    )

    top_global(scoring).to_csv(
        dossier / "top20_global.csv",
        index=False,
        encoding="utf-8-sig",
    )


# =====================================================
# EXPORT EXCEL
# =====================================================

def exporter_excel(
    scoring,
    fichier="data/scoring.xlsx",
):

    Path(fichier).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with pd.ExcelWriter(
        fichier,
        engine="openpyxl",
    ) as writer:

        scoring.to_excel(
            writer,
            sheet_name="Scores",
            index=False,
        )

        top_par_categorie(scoring).to_excel(
            writer,
            sheet_name="Top_Categories",
            index=False,
        )

        top_global(scoring).to_excel(
            writer,
            sheet_name="Top_Global",
            index=False,
        )


# =====================================================
# RÉSUMÉ
# =====================================================

def resume_scoring(
    scoring,
):

    print("=" * 60)
    print("PHASE E - SCORING")
    print("=" * 60)

    print(f"Nombre de fonds scorés : {len(scoring)}")

    print("\nTop 10 global :")

    print(

        top_global(
            scoring,
            10,
        )[

            [
                "OPCVM",
                "Classification",
                "Score_Global",
            ]

        ]

    )

    print("\nTop 5 par catégorie :")

    for categorie in sorted(scoring["Classification"].dropna().unique()):

        print(f"\n--- {categorie} ---")

        print(

            top_par_categorie(
                scoring,
                5,
            )

            .query(
                "Classification == @categorie"
            )[

                [
                    "OPCVM",
                    "Score_Global",
                    "Rang_Categorie",
                ]

            ]

        )
