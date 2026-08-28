import pandas as pd
import numpy as np
from utils.nettoyage import calculer_centre_sensibilite

# =====================================================
# STRESS SUR LA COURBE DES TAUX
# =====================================================

SCENARIOS = {
    "Hausse +25 pb": 0.25,
    "Hausse +50 pb": 0.50,
    "Hausse +100 pb": 1.00,
    "Baisse -50 pb": -0.50,
    "Baisse -100 pb": -1.00,
}


# =====================================================
# CHARGEMENT COURBE BAM
# =====================================================
# Fonction conservée pour les futurs scénarios
# utilisant directement la courbe BAM.
def charger_courbe_bam(chemin):

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
# STRESS D'UN FONDS
# =====================================================

def calculer_stress_fonds(base):

    stress = base.copy()

    stress["Sensibilite_num"] = (
        stress["Sensibilité"]
        .apply(calculer_centre_sensibilite)
    )

    for nom, choc in SCENARIOS.items():

        stress[nom] = (
            -stress["Sensibilite_num"]
            * choc
        )

    return stress


# =====================================================
# RÉSUMÉ PAR CATÉGORIE
# =====================================================

def resume_stress(stress):

    colonnes = list(SCENARIOS.keys())

    return (

        stress

        .groupby("Classification")[colonnes]

        .mean()

        .round(2)

        .reset_index()

    )


# =====================================================
# PIPELINE COMPLET
# =====================================================

def construire_stress(base_opcvm):

    stress = calculer_stress_fonds(
        base_opcvm
    )

    stats = resume_stress(
        stress
    )

    return stress, stats
