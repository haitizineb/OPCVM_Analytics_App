import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


# =====================================================
# Chargement de la courbe BAM
# =====================================================

CHEMIN_COURBE_BAM_DEFAUT = (
    Path("data") / "raw" / "courbe_taux_BAM_2025_2026.csv"
)


def charger_courbe_bam(chemin=CHEMIN_COURBE_BAM_DEFAUT):
    """
    Charge la courbe des taux BAM depuis un CSV.
    `chemin` peut être surchargé (ex: pour Streamlit, un chemin uploadé
    par l'utilisateur ou un fichier packagé avec l'app).
    """

    courbe = pd.read_csv(
        chemin,
        parse_dates=[
            "Date_reference",
            "Date d'échéance",
            "Date de la valeur",
        ],
    )

    return courbe


# =====================================================
# Nettoyage de la sensibilité
# =====================================================

def extraire_sensibilite(valeur):

    if pd.isna(valeur) or str(valeur).strip() in ["", "-"]:
        return np.nan

    texte = re.sub(r"(\d),(\d)", r"\1.\2", str(valeur))
    nombres = re.findall(r"[\d.]+", texte)

    if len(nombres) < 2:
        return np.nan

    borne_min = float(nombres[0])
    borne_max = float(nombres[1])

    return (borne_min + borne_max) / 2


# =====================================================
# Extraction des fonds obligataires
# =====================================================

def preparer_fonds_obligataires(base):
    """
    Prépare les fonds obligataires pour les stress tests.
    Conserve également les informations utiles au scoring.
    """

    fonds = base.copy()

    # Colonnes obligatoires
    colonnes = [
        "CODE ISIN",
        "OPCVM",
        "Classification",
        "AN",
        "Sensibilité",
    ]

    colonnes_existantes = [c for c in colonnes if c in fonds.columns]
    fonds = fonds[colonnes_existantes]

    # Garder uniquement les fonds obligataires
    fonds = fonds[
        fonds["Classification"].isin(["OCT", "OMLT"])
    ].copy()

    # Sensibilité numérique
    fonds["Sensibilite"] = (
        fonds["Sensibilité"]
        .apply(extraire_sensibilite)
    )

    return fonds


# =====================================================
# Construction de la courbe simplifiée
# =====================================================

def segment_maturite(maturite):

    if maturite < 2:
        return "Court_terme"
    if maturite < 7:
        return "Moyen_terme"
    return "Long_terme"


def construire_courbe_simplifiee(courbe):

    courbe = courbe.copy()
    courbe["Segment"] = courbe["Maturite_annees"].apply(segment_maturite)

    courbe_simple = (
        courbe.groupby(["Date_reference", "Segment"])["Taux"]
        .median()
        .unstack()
        .sort_index()
    )

    return courbe_simple


# =====================================================
# Rendements moyens des fonds obligataires
# =====================================================

def calculer_rendements_obligataires(fonds_obligataires, rendements_hebdo):

    isin_oct = fonds_obligataires.loc[
        fonds_obligataires["Classification"] == "OCT", "CODE ISIN"
    ].unique()

    isin_omlt = fonds_obligataires.loc[
        fonds_obligataires["Classification"] == "OMLT", "CODE ISIN"
    ].unique()

    colonnes_oct = [c for c in isin_oct if c in rendements_hebdo.columns]
    colonnes_omlt = [c for c in isin_omlt if c in rendements_hebdo.columns]

    rendement_oct = rendements_hebdo[colonnes_oct].mean(axis=1)
    rendement_omlt = rendements_hebdo[colonnes_omlt].mean(axis=1)

    return rendement_oct, rendement_omlt


# =====================================================
# Variations de la courbe des taux
# =====================================================

def calculer_variations_taux(courbe_simplifiee):
    return courbe_simplifiee.diff().dropna()


# =====================================================
# Jeu de données pour corrélations / régressions
# =====================================================

def construire_base_regression(rendement_oct, rendement_omlt, variations_taux):

    base = pd.DataFrame({
        "Rendement_OCT": rendement_oct,
        "Rendement_OMLT": rendement_omlt,
    })

    base = base.join(variations_taux, how="inner").dropna()

    return base


# =====================================================
# Corrélations
# =====================================================

def calculer_correlations(base_regression):
    return base_regression.corr().round(3)


# =====================================================
# Régression linéaire
# =====================================================

def calculer_regression(base_regression):

    resultat = {}

    pente_oct, intercept_oct, r_oct, p_oct, err_oct = stats.linregress(
        base_regression["Court_terme"], base_regression["Rendement_OCT"]
    )
    resultat["OCT"] = {
        "Duration_implicite": -pente_oct,
        "Pente": pente_oct,
        "Intercept": intercept_oct,
        "R2": r_oct ** 2,
        "Correlation": r_oct,
        "P_value": p_oct,
        "Erreur_std": err_oct,
    }

    pente_omlt, intercept_omlt, r_omlt, p_omlt, err_omlt = stats.linregress(
        base_regression["Moyen_terme"], base_regression["Rendement_OMLT"]
    )
    resultat["OMLT"] = {
        "Duration_implicite": -pente_omlt,
        "Pente": pente_omlt,
        "Intercept": intercept_omlt,
        "R2": r_omlt ** 2,
        "Correlation": r_omlt,
        "P_value": p_omlt,
        "Erreur_std": err_omlt,
    }

    return pd.DataFrame(resultat).T


# =====================================================
# Sensibilité moyenne déclarée
# =====================================================

def calculer_sensibilite_moyenne(fonds_obligataires):
    return (
        fonds_obligataires.groupby("Classification")["Sensibilite"]
        .mean()
        .round(2)
    )


# =====================================================
# Fonds les plus exposés
# =====================================================

def construire_table_sensibilite(fonds_obligataires):

    table = (
        fonds_obligataires.sort_values("Date")
        .groupby("CODE ISIN")
        .last()[["OPCVM", "Classification", "Sensibilite"]]
        .dropna()
    )

    table["Rang_exposition"] = table["Sensibilite"].rank(ascending=False, method="min")

    return table


# =====================================================
# Comparaison duration implicite
# =====================================================

def comparer_duration(regression, sensibilite_moyenne):

    comparaison = pd.DataFrame({
        "Duration_implicite": regression["Duration_implicite"],
        "Sensibilite_moyenne": sensibilite_moyenne,
    })

    comparaison["Ecart"] = (
        comparaison["Duration_implicite"] - comparaison["Sensibilite_moyenne"]
    )

    return comparaison.round(3)


# =====================================================
# Stress tests : chocs parallèles
# =====================================================

CHOCS_BPS = [25, 50, 100]


def construire_stress_parallele(table_sensibilite):

    stress = table_sensibilite.copy()

    for choc in CHOCS_BPS:
        choc_decimal = choc / 10000
        stress[f"Impact_+{choc}bps_%"] = -stress["Sensibilite"] * choc_decimal
        stress[f"Impact_-{choc}bps_%"] = stress["Sensibilite"] * choc_decimal

    return stress


# =====================================================
# Pentification / Aplatissement
# =====================================================

SCENARIOS_COURBE = {
    "Pentification": {"Court_terme": -0.25, "Long_terme": 0.25},
    "Aplatissement": {"Court_terme": 0.25, "Long_terme": -0.25},
}


def construire_stress_courbe(table_sensibilite):

    resultat = table_sensibilite.copy()

    for nom, choc in SCENARIOS_COURBE.items():

        def impact(row, choc=choc):
            if row["Classification"] == "OCT":
                return -row["Sensibilite"] * choc["Court_terme"]
            return -row["Sensibilite"] * choc["Long_terme"]

        resultat[f"Impact_{nom}_%"] = resultat.apply(impact, axis=1)

    return resultat


# =====================================================
# Détection des semaines de tension
# =====================================================

def detecter_tension_marche(courbe_simplifiee):

    variation = courbe_simplifiee["Moyen_terme"].diff()
    seuil = variation.std() * 1.5

    semaines_tension = variation[variation > seuil].sort_values(ascending=False)
    semaines_detente = variation[variation < -seuil].sort_values()

    return variation, semaines_tension, semaines_detente, seuil


# =====================================================
# Lecture des performances pendant les tensions
# =====================================================

def analyser_tension_obligataire(rendement_omlt, semaines_tension, semaines_detente):

    return {
        "Rendement_Moyen": rendement_omlt.mean(),
        "Rendement_Tension": rendement_omlt.reindex(semaines_tension.index).mean(),
        "Rendement_Detente": rendement_omlt.reindex(semaines_detente.index).mean(),
    }


# =====================================================
# Synthèse pratique
# =====================================================

def construire_synthese_taux(table_sensibilite):

    synthese = table_sensibilite.copy()

    synthese["Impact_hausse_taux_%"] = -synthese["Sensibilite"]
    synthese["Impact_baisse_taux_%"] = synthese["Sensibilite"]

    synthese["Scenario_defavorable"] = np.where(
        synthese["Classification"] == "OMLT",
        "Hausse des taux longs",
        "Hausse des taux courts",
    )

    synthese["Scenario_favorable"] = np.where(
        synthese["Classification"] == "OMLT",
        "Baisse des taux longs",
        "Baisse des taux courts",
    )

    return synthese


# =====================================================
# Pipeline complet Phase D
# =====================================================

def construire_stress(
    base_complete,
    rendements_hebdo,
    chemin_courbe_bam=CHEMIN_COURBE_BAM_DEFAUT,
):
    """
    Pipeline complet de la Phase D.

    Paramètres
    ----------
    base_complete : DataFrame
        Base complète des OPCVM.
    rendements_hebdo : DataFrame
        Rendements hebdomadaires corrigés.
    chemin_courbe_bam : str ou Path
        Chemin vers le CSV de la courbe des taux BAM (paramétrable,
        au lieu d'un chemin codé en dur).

    Retour
    ------
    dict contenant tous les résultats de la phase D.
    """

    fonds_obligataires = preparer_fonds_obligataires(base_complete)

    courbe = charger_courbe_bam(chemin_courbe_bam)
    courbe_simplifiee = construire_courbe_simplifiee(courbe)

    rendement_oct, rendement_omlt = calculer_rendements_obligataires(
        fonds_obligataires, rendements_hebdo
    )

    variations_taux = calculer_variations_taux(courbe_simplifiee)

    base_regression = construire_base_regression(
        rendement_oct, rendement_omlt, variations_taux
    )
    correlations = calculer_correlations(base_regression)

    regression = calculer_regression(base_regression)
    sensibilite_moyenne = calculer_sensibilite_moyenne(fonds_obligataires)
    comparaison_duration = comparer_duration(regression, sensibilite_moyenne)

    table_sensibilite = construire_table_sensibilite(fonds_obligataires)

    stress_parallele = construire_stress_parallele(table_sensibilite)
    stress_courbe = construire_stress_courbe(table_sensibilite)

    variation_taux, semaines_tension, semaines_detente, seuil = detecter_tension_marche(
        courbe_simplifiee
    )
    analyse_tension = analyser_tension_obligataire(
        rendement_omlt, semaines_tension, semaines_detente
    )

    synthese = construire_synthese_taux(table_sensibilite)

    return {
        "fonds_obligataires": fonds_obligataires,
        "courbe": courbe,
        "courbe_simplifiee": courbe_simplifiee,
        "variations_taux": variations_taux,
        "base_regression": base_regression,
        "correlations": correlations,
        "regression": regression,
        "comparaison_duration": comparaison_duration,
        "table_sensibilite": table_sensibilite,
        "stress_parallele": stress_parallele,
        "stress_courbe": stress_courbe,
        "semaines_tension": semaines_tension,
        "semaines_detente": semaines_detente,
        "analyse_tension": analyse_tension,
        "synthese": synthese,
    }
