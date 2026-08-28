import numpy as np
import pandas as pd


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

SEUIL_MIN_MOIS_HISTORIQUE = 6


# =====================================================
# SCORE PERCENTILE
# =====================================================

def score_percentile(serie, meilleur_grand=True):
    """
    Convertit une série en score entre 0 et 100.

    meilleur_grand=True  -> grande valeur = meilleur score
    meilleur_grand=False -> petite valeur = meilleur score
    """
    return serie.rank(pct=True, ascending=not meilleur_grand) * 100


# =====================================================
# NEUTRALISATION DES FONDS À HISTORIQUE TROP COURT
# =====================================================

def neutraliser_historique_court(
    scoring,
    vl_corrigee,
    seuil_min_mois=SEUIL_MIN_MOIS_HISTORIQUE,
):
    """
    Remplace les scores de risque (volatilité, régularité, drawdown) des
    fonds ayant moins de `seuil_min_mois` mois d'historique par la médiane
    de leur catégorie. Un historique trop court rend ces indicateurs
    artificiellement "parfaits" (pas assez de temps pour révéler une
    vraie baisse de marché).
    """

    base = scoring.copy()

    nb_semaines = vl_corrigee.notna().sum()
    base["Nb_mois_historique"] = (
        (nb_semaines / 4.33).reindex(base.index)
    )

    masque_court = base["Nb_mois_historique"] < seuil_min_mois

    for col in ["Score_Volatilite", "Score_Regularite", "Score_Drawdown"]:
        mediane_categorie = base.groupby("Classification")[col].transform("median")
        base.loc[masque_court, col] = mediane_categorie[masque_court]

    return base


# =====================================================
# CONSTRUCTION DU SCORING
# =====================================================

def construire_scoring(
    risque_complet,
    vl_corrigee=None,
    seuil_min_mois=SEUIL_MIN_MOIS_HISTORIQUE,
):
    """
    Construit le score global à partir de la table déjà enrichie par
    performances.py + risque.py (indexée par CODE ISIN, contenant déjà
    OPCVM, Classification, AN, Perf_YTD_calculee_%, Ecart_type_mensuel_%,
    Pct_mois_positifs, Volatilite_annualisee_%, Max_Drawdown_%).

    Paramètres
    ----------
    risque_complet : DataFrame
        Sortie de risque.construire_risque(...), indexée par CODE ISIN.
    vl_corrigee : DataFrame ou None
        VL corrigées (index=Date, colonnes=CODE ISIN). Si fournie, un
        filtre d'historique minimum est appliqué avant le scoring.
    seuil_min_mois : int
        Nombre de mois minimum d'historique requis pour être noté sur les
        critères de risque sans neutralisation.
    """

    scoring = risque_complet.copy()

    colonnes_requises = [
        "OPCVM", "Classification", "AN",
        "Perf_YTD_calculee_%", "Ecart_type_mensuel_%",
        "Volatilite_annualisee_%", "Max_Drawdown_%",
    ]
    manquantes = [c for c in colonnes_requises if c not in scoring.columns]
    if manquantes:
        raise KeyError(
            f"Colonnes manquantes dans risque_complet : {manquantes}. "
            "Vérifiez que construire_risque() a bien été appliqué en amont."
        )

    # ===============================
    # Scores normalisés (par catégorie)
    # ===============================

    scoring["Score_Performance"] = (
        scoring.groupby("Classification")["Perf_YTD_calculee_%"]
        .transform(lambda x: score_percentile(x, meilleur_grand=True))
    )

    scoring["Score_Volatilite"] = (
        scoring.groupby("Classification")["Volatilite_annualisee_%"]
        .transform(lambda x: score_percentile(x, meilleur_grand=False))
    )

    scoring["Score_Regularite"] = (
        scoring.groupby("Classification")["Ecart_type_mensuel_%"]
        .transform(lambda x: score_percentile(x, meilleur_grand=False))
    )

    scoring["Score_Drawdown"] = (
        scoring.groupby("Classification")["Max_Drawdown_%"]
        .transform(lambda x: score_percentile(x, meilleur_grand=False))
    )

    scoring["Score_Taille"] = (
        scoring.groupby("Classification")["AN"]
        .transform(lambda x: score_percentile(x, meilleur_grand=True))
    )

    # ===============================
    # Neutralisation historique court
    # ===============================

    if vl_corrigee is not None:
        scoring = neutraliser_historique_court(
            scoring, vl_corrigee, seuil_min_mois
        )

    # ===============================
    # Score global pondéré
    # ===============================

    scoring["Score_Global"] = sum(
        scoring[col] * poids for col, poids in POIDS.items()
    )

    scoring["Rang_Categorie"] = (
        scoring.groupby("Classification")["Score_Global"]
        .rank(ascending=False, method="min")
    )

    scoring["Rang_Global"] = (
        scoring["Score_Global"].rank(ascending=False, method="min")
    )

    return scoring


# =====================================================
# TOP N PAR CATÉGORIE / GLOBAL
# =====================================================

def top_par_categorie(scoring, n=10):
    return (
        scoring.reset_index()
        .sort_values(["Classification", "Score_Global"], ascending=[True, False])
        .groupby("Classification")
        .head(n)
        .reset_index(drop=True)
    )


def top_global(scoring, n=20):
    return (
        scoring.reset_index()
        .sort_values("Score_Global", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


# =====================================================
# EXPORTS
# =====================================================

def exporter_csv(scoring, dossier="data"):
    from pathlib import Path

    dossier = Path(dossier)
    dossier.mkdir(exist_ok=True)

    scoring.reset_index().to_csv(
        dossier / "score_global.csv", index=False, encoding="utf-8-sig"
    )
    top_par_categorie(scoring).to_csv(
        dossier / "top10_par_categorie.csv", index=False, encoding="utf-8-sig"
    )
    top_global(scoring).to_csv(
        dossier / "top20_global.csv", index=False, encoding="utf-8-sig"
    )


def exporter_excel(scoring, fichier="data/scoring.xlsx"):
    from pathlib import Path

    Path(fichier).parent.mkdir(exist_ok=True, parents=True)

    with pd.ExcelWriter(fichier, engine="openpyxl") as writer:
        scoring.reset_index().to_excel(writer, sheet_name="Scores", index=False)
        top_par_categorie(scoring).to_excel(writer, sheet_name="Top_Categories", index=False)
        top_global(scoring).to_excel(writer, sheet_name="Top_Global", index=False)


# =====================================================
# RÉSUMÉ (affichage console)
# =====================================================

def resume_scoring(scoring):
    print("=" * 60)
    print("PHASE E - SCORING")
    print("=" * 60)
    print(f"Nombre de fonds scorés : {len(scoring)}")

    print("\nTop 10 global :")
    print(top_global(scoring, 10)[["OPCVM", "Classification", "Score_Global"]])

    print("\nTop 5 par catégorie :")
    for categorie in sorted(scoring["Classification"].dropna().unique()):
        print(f"\n--- {categorie} ---")
        print(
            top_par_categorie(scoring, 5)
            .query("Classification == @categorie")[
                ["OPCVM", "Score_Global", "Rang_Categorie"]
            ]
        )
