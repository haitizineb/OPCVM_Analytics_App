import os
import time
from datetime import date, timedelta

import requests

BASE_URL_NOUVELLE = (
    "https://fundshare.asfim.ma/api/performances/export/?date={}"
)

BASE_URL_ANCIENNE = (
    "https://asfim.ma/static/tableau-des-performances/"
    "Tableau%20des%20Performances%20Hebdomadaires%20au%20{}.xlsx"
)

DECALAGES_JOURS_A_ESSAYER = [0, -1, 1, -2, 2, -3, 3]


# ==========================================================
# VENDREDIS
# ==========================================================

def vendredis_entre(debut, fin):

    jours_a_ajouter = (4 - debut.weekday()) % 7
    d = debut + timedelta(days=jours_a_ajouter)

    while d <= fin:
        yield d
        d += timedelta(days=7)


# ==========================================================
# TELECHARGEMENT D'UN FICHIER
# ==========================================================


def _telecharger_depuis_url(url, session, cible, dossier):

    for tentative in range(2):

        try:
            resp = session.get(url, timeout=20)

            if (
                resp.status_code == 200
                and "application" in resp.headers.get("Content-Type", "").lower()
                and len(resp.content) > 5000
            ):

                chemin = os.path.join(
                    dossier,
                    f"{cible.isoformat()}.xlsx"
                )

                with open(chemin, "wb") as f:
                    f.write(resp.content)

                return True

        except requests.RequestException:

            if tentative == 0:
                time.sleep(1)

    return False


# ==========================================================
# TELECHARGEMENT D'UNE DATE
# ==========================================================

def telecharger_fichier(cible, session, dossier):

    for decalage in DECALAGES_JOURS_A_ESSAYER:

        d = cible + timedelta(days=decalage)

        url = BASE_URL_NOUVELLE.format(
            d.isoformat()
        )

        if _telecharger_depuis_url(
            url,
            session,
            cible,
            dossier,
        ):
            return True

    for decalage in DECALAGES_JOURS_A_ESSAYER:

        d = cible + timedelta(days=decalage)

        url = BASE_URL_ANCIENNE.format(
            d.strftime("%d-%m-%Y")
        )

        if _telecharger_depuis_url(
            url,
            session,
            cible,
            dossier,
        ):
            return True

    return False


# ==========================================================
# TELECHARGEMENT DES SEMAINES MANQUANTES
# ==========================================================

def telecharger_nouvelles_semaines(
    date_debut,
    date_fin,
    dossier,
):

    dates_cibles = list(
        vendredis_entre(
            date_debut,
            date_fin,
        )
    )

    reussies = []
    echouees = []

    with requests.Session() as session:

        session.headers.update({
            "User-Agent":
            "Mozilla/5.0 (compatible; OPCVM-Analytics/1.0)"
        })

        for cible in dates_cibles:

            chemin = os.path.join(
                dossier,
                f"{cible.isoformat()}.xlsx"
            )

            if os.path.exists(chemin):
                continue

            if telecharger_fichier(
                cible,
                session,
                dossier,
            ):

                print(f"✓ {cible}")
                reussies.append(cible)

            else:

                print(f"✗ {cible}")
                echouees.append(cible)

    return reussies, echouees


# ==========================================================
# FONCTION PRINCIPALE
# ==========================================================

def telecharger_asfim(
    date_debut,
    date_fin,
    dossier,
):

    os.makedirs(
        dossier,
        exist_ok=True,
    )

    reussies, echouees = telecharger_nouvelles_semaines(
        date_debut=date_debut,
        date_fin=date_fin,
        dossier=dossier,
    )

    print(
        f"\nTéléchargement terminé : {len(reussies)} nouveau(x) fichier(s)."
    )

    if echouees:

        print(
            f"{len(echouees)} semaine(s) non récupérée(s)."
        )

        with open(
            os.path.join(
                dossier,
                "telechargements_echoues.txt",
            ),
            "w",
            encoding="utf-8",
        ) as f:

            for d in echouees:
                f.write(f"{d}\n")

    if echouees:

        with open(
            os.path.join(dossier, "semaines_non_telechargees.txt"),
            "w",
            encoding="utf-8",
        ) as f:

            for d in echouees:
                f.write(f"{d}\n")
    return reussies, echouees