import re
from io import BytesIO, StringIO

import numpy as np
import pandas as pd
import requests
def convertir_date_fr(serie):

    mois = {
        "janv.": "01",
        "févr.": "02",
        "mars": "03",
        "avr.": "04",
        "mai": "05",
        "juin": "06",
        "juil.": "07",
        "août": "08",
        "sept.": "09",
        "oct.": "10",
        "nov.": "11",
        "déc.": "12",
    }

    s = serie.astype(str)

    for fr, num in mois.items():
        s = s.str.replace(fr, num, regex=False)

    return pd.to_datetime(
        s,
        format="%d %m %Y",
        errors="coerce",
    )
def telecharger_monia():

    url = (
        "https://www.bkam.ma/export/blockcsv/566622/"
        "30551c1667f5f2004fb0019220d41795/"
        "4734c7b73113d8d72895a19090974066"
        "?block=4734c7b73113d8d72895a19090974066"
    )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    resp = requests.get(url, headers=headers, timeout=30)

    resp.raise_for_status()

    df = pd.read_csv(
        StringIO(resp.text),
        sep=";",
        skiprows=2,
        encoding="utf-8",
    )

    df.columns = (
        df.columns
        .str.replace('"', "", regex=False)
        .str.strip()
    )

    df["Indice MONIA"] = (
        df["Indice MONIA"]
        .astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )

    df["Date de référence"] = pd.to_datetime(
        df["Date de référence"],
        dayfirst=True,
    )

    df = df.rename(
        columns={
            "Indice MONIA": "MONIA",
            "Date de référence": "Date_Reference",
        }
    )

    return (
        df.sort_values("Date_Reference")
        .reset_index(drop=True)
    )
def telecharger_tmp():

    url = (
        "https://www.bkam.ma/export/blockcsv/973/"
        "d3239ec6d067cd9381f137545720a6c9/"
        "ae14ce1a4ee29af53d5645f51bf0e97d"
        "?block=ae14ce1a4ee29af53d5645f51bf0e97d"
    )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    resp = requests.get(url, headers=headers, timeout=30)

    resp.raise_for_status()

    df = pd.read_csv(
        StringIO(resp.text),
        sep=";",
        skiprows=2,
        encoding="utf-8",
    )

    df.columns = (
        df.columns
        .str.replace('"', "", regex=False)
        .str.strip()
    )

    df["Taux Moyen Pondéré"] = (
        df["Taux Moyen Pondéré"]
        .astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )

    df["Date"] = pd.to_datetime(
        df["Date"],
        dayfirst=True,
    )

    df = df.rename(
        columns={
            "Date": "Date_Reference",
            "Taux Moyen Pondéré": "TMP",
        }
    )

    return (
        df.sort_values("Date_Reference")
        .reset_index(drop=True)
    )
def telecharger_indice_bmce(id_indice, nom_colonne):

    url = "https://www.bmcecapitalbourse.com/bkbbourse/details/hiku/export.xls"

    params = {
        "id": id_indice,
        "from": "01-01-2000",
        "to": pd.Timestamp.today().strftime("%d-%m-%Y"),
        "raw": "true",
    }

    resp = requests.get(
        url,
        params=params,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )

    resp.raise_for_status()

    df = pd.read_excel(BytesIO(resp.content))

    df.columns = (
        df.columns
        .str.strip()
        .str.replace("\n", " ")
    )

    df["Date"] = convertir_date_fr(df["Date"])

    df["Dernier"] = pd.to_numeric(
        df["Dernier"],
        errors="coerce",
    )

    df = df.rename(
        columns={
            "Dernier": nom_colonne
        }
    )

    return (
        df[["Date", nom_colonne]]
        .dropna()
        .sort_values("Date")
        .reset_index(drop=True)
    )
def telecharger_indices():

    monia = telecharger_monia()

    tmp = telecharger_tmp()

    masi = telecharger_indice_bmce(
        "1356351,102,608",
        "MASI",
    )

    masi_rb = telecharger_indice_bmce(
        "1696748,102,608",
        "MASI_RB",
    )

    return monia, tmp, masi, masi_rb
def normaliser_benchmark(texte):

    t = str(texte).strip().upper()

    t = re.sub(r"\s+", " ", t)

    t = t.replace(" %", "%")

    t = t.replace("%+", "% +")

    t = re.sub(r"\s*\+\s*", " + ", t)

    return t.strip()


MAPPING_VARIANTES = {

    "TMP INTERBANCAIRE": "TMP",
    "TMP AU JOUR LE JOUR": "TMP",
    "TMP MARCHE INTERBANCAIRE": "TMP",
    "TMI(JJ)": "TMP",
    "TMJ(JJ)": "TMP",

    "MONIA CAPITALISE": "MONIA",
    "MONIA CAPITALISÉ": "MONIA",

    "MASI RENTABILITE": "MASI RB",
    "MASI RENTABILITE NETTE": "MASI RB",

    "MASI.": "MASI",

    "20 MBI MT": "MBI MT",

    "CFG 25": "CFG 25 FLOTTANT",

    "MBI COURT TERME": "MBI CT",

    "50 PTS DE BASE": None,
}


CORRECTIONS_BENCHMARK = {

    "MA0000041683": "MONIA",

    "MA0000041691": "TMP",
}


def preparer_benchmarks(table_reference):

    table_reference = table_reference.copy()

    table_reference["Indice_Bentchmark_Corrige"] = table_reference.apply(
        lambda row: CORRECTIONS_BENCHMARK.get(
            row["CODE ISIN"],
            row["Indice Bentchmark"],
        ),
        axis=1,
    )

    table_reference["Benchmark_Normalise"] = (
        table_reference["Indice_Bentchmark_Corrige"]
        .apply(normaliser_benchmark)
        .replace(MAPPING_VARIANTES)
    )

    return table_reference
def valeur_indice_a_date(
    serie_indice,
    date_cible,
    tolerance_jours=7,
):

    fenetre = serie_indice[
        serie_indice.index <= date_cible
    ]

    fenetre = fenetre[
        fenetre.index >= date_cible - pd.Timedelta(days=tolerance_jours)
    ]

    if fenetre.empty:
        return np.nan

    return fenetre.iloc[-1]
def performance_indice_niveau(
    serie_indice,
    date_fin,
    jours_arriere,
    tolerance_jours=10,
):

    serie = serie_indice.dropna()

    date_debut = (
        pd.Timestamp(date_fin)
        - pd.Timedelta(days=jours_arriere)
    )

    fenetre = serie[
        (serie.index >= date_debut)
        &
        (serie.index <= date_fin)
    ]

    if len(fenetre) < 2:
        return np.nan

    if (
        serie.index.min()
        >
        date_debut + pd.Timedelta(days=tolerance_jours)
    ):
        return np.nan

    return (fenetre.iloc[-1] / fenetre.iloc[0]) - 1
from utils.performances import HORIZONS


def construire_indices_hebdo(
    vl_corrigee,
    monia,
    tmp,
    masi,
    masi_rb,
):

    indices_disponibles = {

        "MASI":
        masi.set_index("Date")["MASI"],

        "MASI RB":
        masi_rb.set_index("Date")["MASI_RB"],

        "MONIA":
        monia.set_index("Date_Reference")["MONIA"],

        "TMP":
        tmp.set_index("Date_Reference")["TMP"],

    }

    dates = vl_corrigee.index

    indices_hebdo = pd.DataFrame(index=dates)

    for nom, serie in indices_disponibles.items():

        indices_hebdo[nom] = [

            valeur_indice_a_date(
                serie,
                d,
            )

            for d in dates

        ]

    return indices_hebdo, indices_disponibles
def construire_table_benchmarks(indices_disponibles, date_reference):

    table = {}

    for nom in ["MASI", "MASI RB"]:

        table[nom] = {

            h: performance_indice_niveau(
                indices_disponibles[nom],
                date_reference,
                jours,
            )

            for h, jours in HORIZONS.items()

        }

    for nom in ["MONIA", "TMP"]:

        serie = indices_disponibles[nom].dropna()

        ligne = {}

        for h, jours in HORIZONS.items():

            fenetre = serie[
                serie.index
                >=
                date_reference - pd.Timedelta(days=jours)
            ]

            if fenetre.empty:

                ligne[h] = np.nan

            else:

                ligne[h] = (
                    fenetre.mean() / 100
                ) * (jours / 365)

        table[nom] = ligne

    df = pd.DataFrame(table).T

    df.index.name = "Indice"

    return df