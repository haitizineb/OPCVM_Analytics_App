import glob
import os
import re

import numpy as np
import pandas as pd

# =====================================================
# Colonnes ASFIM
# =====================================================

COLONNES_NUMERIQUES = [
    "AN",
    "VL",
    "YTD",
    "1 jour",
    "1 semaine",
    "1 mois",
    "3 mois",
    "6 mois",
    "1 an",
    "2 ans",
    "3 ans",
    "5 ans",
]

COLONNES_TEXTE_A_NORMALISER = [
    "Classification",
    "Souscripteurs",
    "Sensibilité",
]

ALIAS_COLONNES = {
    "Dénomination OPCVM": "OPCVM",
    "Indice Benchmark": "Indice Bentchmark",
}

COLONNES_UTILES = [
    "Date",
    "CODE ISIN",
    "OPCVM",
    "Société de Gestion",
    "Classification",
    "Sensibilité",
    "Indice Bentchmark",
    "AN",
    "VL",
    "YTD",
    "1 jour",
    "1 semaine",
    "1 mois",
    "3 mois",
    "6 mois",
    "1 an",
    "2 ans",
    "3 ans",
    "5 ans",
]

# =====================================================
# Nettoyage
# =====================================================

def nettoyer_numerique(serie):

    if serie.dtype != object:
        return pd.to_numeric(serie, errors="coerce")

    serie = (
        serie.astype(str)
        .str.replace("\xa0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    return pd.to_numeric(serie, errors="coerce")


def extraire_date_depuis_nom_fichier(chemin):

    m = re.match(
        r"(\d{4})-(\d{2})-(\d{2})",
        os.path.basename(chemin),
    )

    if m is None:
        return None

    annee, mois, jour = m.groups()

    return pd.Timestamp(
        year=int(annee),
        month=int(mois),
        day=int(jour),
    )


# =====================================================
# Lecture d'un fichier ASFIM
# =====================================================

def lire_un_fichier(
    chemin,
    souscripteur_cible="FGP",
):

    date_rapport = extraire_date_depuis_nom_fichier(chemin)

    df = pd.read_excel(
        chemin,
        skiprows=1,
    )

    df.columns = [str(c).strip() for c in df.columns]

    df = df.rename(columns=ALIAS_COLONNES)

    df = df[df["CODE ISIN"].notna()].copy()

    for col in COLONNES_TEXTE_A_NORMALISER:

        if col in df.columns:

            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.upper()
            )

    if "Souscripteurs" in df.columns:

        df = df[
            df["Souscripteurs"] == souscripteur_cible
        ].copy()

    for col in COLONNES_NUMERIQUES:

        if col in df.columns:

            df[col] = nettoyer_numerique(df[col])

    df["Date"] = date_rapport
    df["Fichier_source"] = os.path.basename(chemin)

    return df


# =====================================================
# Construction d'une base depuis un dossier
# =====================================================

def construire_base_brute(dossier):

    fichiers = sorted(
        glob.glob(
            os.path.join(dossier, "*.xlsx")
        )
    )

    print(f"{len(fichiers)} fichiers trouvés.")

    tous_les_df = []
    erreurs = []

    for chemin in fichiers:

        try:

            df = lire_un_fichier(chemin)

            tous_les_df.append(df)

        except Exception as e:

            erreurs.append(
                (
                    os.path.basename(chemin),
                    str(e),
                )
            )

    if erreurs:

        print(f"{len(erreurs)} erreur(s).")

    if len(tous_les_df) == 0:

        return None

    base = pd.concat(
        tous_les_df,
        ignore_index=True,
    )

    colonnes_presentes = [
        c
        for c in COLONNES_UTILES
        if c in base.columns
    ]

    base = base[
        colonnes_presentes + ["Fichier_source"]
    ]

    base = (
        base
        .sort_values(["CODE ISIN", "Date"])
        .drop_duplicates(
            subset=["CODE ISIN", "Date"]
        )
        .reset_index(drop=True)
    )

    return base
# =====================================================
# Fusion des bases
# =====================================================

def fusionner_bases(
    base_historique,
    base_recente,
):

    base = pd.concat(
        [
            base_historique,
            base_recente,
        ],
        ignore_index=True,
    )

    base = (
        base
        .sort_values(
            ["CODE ISIN", "Date"]
        )
        .drop_duplicates(
            subset=["CODE ISIN", "Date"]
        )
        .reset_index(drop=True)
    )

    return base


# =====================================================
# Construction de la base complète
# =====================================================

def construire_base_complete(
    dossier_raw,
    dossier_historique,
):

    print("Lecture historique...")

    base_historique = construire_base_brute(
        dossier_historique
    )

    print("Lecture période récente...")

    base_recente = construire_base_brute(
        dossier_raw
    )

    base_complete = fusionner_bases(
        base_historique,
        base_recente,
    )

    print(
        f"{base_complete.shape[0]} lignes"
    )

    print(
        f"{base_complete['CODE ISIN'].nunique()} fonds"
    )

    return base_complete

import re
import numpy as np


def calculer_centre_sensibilite(valeur):
    """
    Convertit les intervalles ASFIM en valeur numérique (centre).
    Gère : [a b[, ]a b], [a b], <a, -, nombres simples, etc.
    """
    if pd.isna(valeur):
        return np.nan

    valeur = str(valeur).strip()

    if valeur in ["-", "", "nan", "None", "NaN"]:
        return np.nan

    # Si c'est déjà un nombre simple (ex: "5", "2.4", "0.25")
    try:
        return float(valeur.replace(",", "."))
    except:
        pass

    # Remplace les virgules par des points pour les décimaux
    valeur = valeur.replace(",", ".")

    # Cas "<0.5" → borne sup = 0.5, on prend 0.25 (moitié)
    if valeur.startswith("<"):
        nombres = re.findall(r"\d+\.?\d*", valeur)
        if len(nombres) >= 1:
            return float(nombres[0]) / 2
        return np.nan

    # Extrait les nombres de l'intervalle [3  7[ ou ]0.5  1.1]
    nombres = re.findall(r"\d+\.?\d*", valeur)

    if len(nombres) >= 2:
        try:
            borne_inf = float(nombres[0])
            borne_sup = float(nombres[1])
            return (borne_inf + borne_sup) / 2
        except:
            return np.nan

    return np.nan
# =====================================================
# Tableau des VL
# =====================================================

def construire_vl_wide(base):

    return (
        base
        .pivot_table(
            index="Date",
            columns="CODE ISIN",
            values="VL",
            aggfunc="first",
        )
        .sort_index()
    )


# =====================================================
# TABLE DE RÉFÉRENCE
# =====================================================

def construire_table_reference(base):

    colonnes = [
        "CODE ISIN",
        "OPCVM",
        "Société de Gestion",
        "Classification",
        "AN",
        "Sensibilité",
        "Indice Bentchmark",
    ]

    # On ne garde que les colonnes réellement présentes
    colonnes = [
        c for c in colonnes
        if c in base.columns
    ]

    table_reference = (
        base[colonnes]
        .sort_values("CODE ISIN")
        .drop_duplicates(
            subset="CODE ISIN",
            keep="last"
        )
        .reset_index(drop=True)
    )
    table_reference["Sensibilité"] = (
        table_reference["Sensibilité"]
        .apply(calculer_centre_sensibilite)
    )

    return table_reference


# =====================================================
# Paramètres anomalies
# =====================================================

SEUIL_RUPTURE = 0.30

FACTEURS_VIRGULE = [
    10,
    100,
    1000,
]

TOLERANCE_CORRECTION = 0.25

FENETRE_PERSISTANCE = 2
# =====================================================
# Détection et correction des anomalies de VL
# =====================================================

def detecter_corriger_anomalies(vl_wide):

    vl_corrigee = vl_wide.copy()

    log_virgule = []
    log_rupture = []

    for isin in vl_wide.columns:

        serie = vl_wide[isin].copy()

        valides = serie.dropna()

        if len(valides) < 5:
            continue

        mediane = valides.median()

        # --------------------------------------------
        # Correction erreurs de virgule
        # --------------------------------------------

        for date_idx, val in serie.items():

            if pd.isna(val) or mediane == 0:
                continue

            ratio = val / mediane

            for facteur in FACTEURS_VIRGULE:

                valeur_corrigee = val / facteur

                if (
                    abs(valeur_corrigee - mediane) / mediane
                    < TOLERANCE_CORRECTION
                    and abs(ratio) > 3
                ):

                    log_virgule.append(
                        {
                            "CODE ISIN": isin,
                            "Date": date_idx,
                            "VL_originale": val,
                            "VL_corrigee": valeur_corrigee,
                            "Facteur": facteur,
                        }
                    )

                    vl_corrigee.loc[
                        date_idx,
                        isin,
                    ] = valeur_corrigee

                    break

        # --------------------------------------------
        # Détection des ruptures permanentes
        # --------------------------------------------

        serie_corrigee = vl_corrigee[isin]

        rendements = serie_corrigee.pct_change(
            fill_method=None
        )

        for i in range(
            1,
            len(rendements) - 1,
        ):

            r = rendements.iloc[i]

            if pd.isna(r):
                continue

            if abs(r) < SEUIL_RUPTURE:
                continue

            date_rupture = rendements.index[i]

            niveau_avant = serie_corrigee.iloc[i - 1]

            niveau_apres = serie_corrigee.iloc[i]

            fenetre = (
                serie_corrigee.iloc[
                    i : i + 1 + FENETRE_PERSISTANCE
                ]
                .dropna()
            )

            if len(fenetre) < 2:
                continue

            retour = (
                abs(
                    fenetre.iloc[-1]
                    - niveau_avant
                )
                / niveau_avant
            ) < TOLERANCE_CORRECTION

            if not retour:

                log_rupture.append(
                    {
                        "CODE ISIN": isin,
                        "Date": date_rupture,
                        "Variation": r,
                        "VL_avant": niveau_avant,
                        "VL_apres": niveau_apres,
                    }
                )

    log_virgule = pd.DataFrame(log_virgule)

    log_rupture = pd.DataFrame(log_rupture)

    return (
        vl_corrigee,
        log_virgule,
        log_rupture,
    )
# =====================================================
# Préparation complète des VL
# =====================================================

def preparer_vl(base_complete):
    """
    Pipeline complet :
        Base complète
            ↓
        VL wide
            ↓
        Correction des anomalies
            ↓
        Rendements hebdomadaires
    """

    vl_wide = construire_vl_wide(base_complete)

    (
        vl_corrigee,
        log_virgule,
        log_rupture,
    ) = detecter_corriger_anomalies(vl_wide)

    rendements_hebdo = vl_corrigee.pct_change(
        fill_method=None
    )

    if not log_rupture.empty:

        for _, row in log_rupture.iterrows():

            isin = row["CODE ISIN"]
            date_rupture = row["Date"]

            if (
                isin in rendements_hebdo.columns
                and date_rupture in rendements_hebdo.index
            ):

                rendements_hebdo.loc[
                    date_rupture,
                    isin,
                ] = np.nan

    return (
        vl_corrigee,
        rendements_hebdo,
        log_virgule,
        log_rupture,
    )


# =====================================================
# Fonction principale du module
# =====================================================

def charger_donnees_nettoyees(
    dossier_raw,
    dossier_historique,
):
    """
    Fonction principale utilisée par maj.py.

    Retourne :
        - base_complete
        - table_reference
        - vl_corrigee
        - rendements_hebdo
        - log_virgule
        - log_rupture
    """

    base_complete = construire_base_complete(
        dossier_raw,
        dossier_historique,
    )

    table_reference = construire_table_reference(
        base_complete
    )

    (
        vl_corrigee,
        rendements_hebdo,
        log_virgule,
        log_rupture,
    ) = preparer_vl(
        base_complete
    )

    return (
        base_complete,
        table_reference,
        vl_corrigee,
        rendements_hebdo,
        log_virgule,
        log_rupture,
    )