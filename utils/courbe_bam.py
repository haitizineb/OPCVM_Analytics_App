import time
from datetime import datetime
from pathlib import Path
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

            print(f"Téléchargement BAM : {d.date()}")

            df = telecharger_courbe(
                d.strftime("%d/%m/%Y")
            )

            courbes.append(df)

            time.sleep(1)

        except Exception:

            try:

                jeudi = d - pd.Timedelta(days=1)

                print(
                    f"Vendredi indisponible → essai du jeudi {jeudi.date()}"
                )

                df = telecharger_courbe(
                    jeudi.strftime("%d/%m/%Y")
                )

                courbes.append(df)

            except Exception as e:

                print(
                    f"Echec {d.date()} : {e}"
                )

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
    Path("data").mkdir(exist_ok=True)

    courbes.to_csv(
        "data/courbe_taux_BAM_2025_2026.csv",
        index=False,
        encoding="utf-8-sig",
    )

    courbes.to_excel(
        "data/courbe_taux_BAM_2025_2026.xlsx",
        index=False,
    )
    return courbes