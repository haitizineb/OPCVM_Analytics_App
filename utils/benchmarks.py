import re
from io import BytesIO, StringIO

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =====================================================
# Conversion des dates françaises
# =====================================================

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


# =====================================================
# Téléchargement MONIA
# =====================================================

def telecharger_monia():
    """
    Télécharge les données MONIA depuis Bank al-Maghrib.
    Retourne un DataFrame vide en cas d'erreur pour permettre à l'app de continuer.
    """
    try:
        url = (
            "https://www.bkam.ma/export/blockcsv/"
            "566622/30551c1667f5f2004fb0019220d41795/"
            "4734c7b73113d8d72895a19090974066"
            "?block=4734c7b73113d8d72895a19090974066"
        )

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/csv",
            "Referer": "https://www.bkam.ma/",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # Create session with retry logic
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[403, 429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        r = session.get(
            url,
            headers=headers,
            timeout=30,
        )

        r.raise_for_status()

        df = pd.read_csv(
            StringIO(r.text),
            sep=";",
            skiprows=2,
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

        return (
            df.rename(
                columns={
                    "Date de référence": "Date_Reference",
                    "Indice MONIA": "MONIA",
                }
            )
            .sort_values("Date_Reference")
            .reset_index(drop=True)
        )

    except Exception as e:
        print(f"⚠️  Erreur lors du téléchargement des données MONIA: {e}")
        print("   Continuant sans données MONIA...")
        # Retourner un DataFrame vide avec les colonnes attendues
        return pd.DataFrame(columns=["Date_Reference", "MONIA"])


# =====================================================
# Téléchargement TMP
# =====================================================

def telecharger_tmp():
    """
    Télécharge les données TMP (Taux Moyen Pondéré) depuis Bank al-Maghrib.
    Retourne un DataFrame vide en cas d'erreur pour permettre à l'app de continuer.
    """
    try:
        url = (
            "https://www.bkam.ma/export/blockcsv/"
            "973/d3239ec6d067cd9381f137545720a6c9/"
            "ae14ce1a4ee29af53d5645f51bf0e97d"
            "?block=ae14ce1a4ee29af53d5645f51bf0e97d"
        )

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/csv",
            "Referer": "https://www.bkam.ma/",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # Create session with retry logic
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[403, 429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        r = session.get(
            url,
            headers=headers,
            timeout=30,
        )

        r.raise_for_status()

        df = pd.read_csv(
            StringIO(r.text),
            sep=";",
            skiprows=2,
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

        return (
            df.rename(
                columns={
                    "Date": "Date_Reference",
                    "Taux Moyen Pondéré": "TMP",
                }
            )
            .sort_values("Date_Reference")
            .reset_index(drop=True)
        )

    except Exception as e:
        print(f"⚠️  Erreur lors du téléchargement des données TMP: {e}")
        print("   Continuant sans données TMP...")
        # Retourner un DataFrame vide avec les colonnes attendues
        return pd.DataFrame(columns=["Date_Reference", "TMP"])


# =====================================================
# Téléchargement BMCE
# =====================================================

def telecharger_indice_bmce(
    id_indice,
    nom_colonne,
):
    """
    Télécharge les indices BMCE depuis BMCE Capital Bourse.
    Retourne un DataFrame vide en cas d'erreur pour permettre à l'app de continuer.
    """
    try:
        url = (
            "https://www.bmcecapitalbourse.com/"
            "bkbbourse/details/hiku/export.xls"
        )

        params = {
            "id": id_indice,
            "from": "01-01-2000",
            "to": pd.Timestamp.today().strftime("%d-%m-%Y"),
            "raw": "true",
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/vnd.ms-excel",
            "Referer": "https://www.bmcecapitalbourse.com/",
        }

        # Create session with retry logic
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[403, 429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        r = session.get(
            url,
            params=params,
            headers=headers,
            timeout=30,
        )

        r.raise_for_status()

        df = pd.read_excel(
            BytesIO(r.content)
        )

        df.columns = (
            df.columns
            .str.strip()
            .str.replace("\n", " ")
        )

        df["Date"] = convertir_date_fr(
            df["Date"]
        )

        df["Dernier"] = pd.to_numeric(
            df["Dernier"],
            errors="coerce",
        )

        return (
            df.rename(
                columns={
                    "Dernier": nom_colonne
                }
            )[["Date", nom_colonne]]
            .dropna()
            .sort_values("Date")
            .reset_index(drop=True)
        )

    except Exception as e:
        print(f"⚠️  Erreur lors du téléchargement de l'indice BMCE ({nom_colonne}): {e}")
        print("   Continuant sans ces données...")
        # Retourner un DataFrame vide avec les colonnes attendues
        return pd.DataFrame(columns=["Date", nom_colonne])


# =====================================================
# Normalisation benchmark
# =====================================================

MAPPING_VARIANTES = {

    "TMP INTERBANCAIRE": "TMP",
    "TMP AU JOUR LE JOUR": "TMP",
    "TMP MARCHE INTERBANCAIRE": "TMP",

    "TMI(JJ)": "TMP",
    "TMJ(JJ)": "TMP",

    "MONIA CAPITALISÉ": "MONIA",
    "MONIA CAPITALISE": "MONIA",

    "MASI RENTABILITE": "MASI RN",
    "MASI RENTABILITE NETTE": "MASI RN",

    "MASI.": "MASI",

    "20 MBI MT": "MBI MT",

    "CFG 25": "CFG 25 FLOTTANT",

    "MBI COURT TERME": "MBI CT",

    "50 PTS DE BASE": None,

}


def normaliser_benchmark(texte):

    t = str(texte).upper().strip()

    t = re.sub(r"\s+", " ", t)

    t = re.sub(r"\s*\+\s*", " + ", t)

    return t


def appliquer_mapping(nom):

    return MAPPING_VARIANTES.get(
        nom,
        nom,
    )
# =====================================================
# Construction des indices disponibles
# =====================================================

CORRECTIONS_BENCHMARK = {
    "MA0000041683": "MONIA",
    "MA0000041691": "TMP",
}


def construire_indices():

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
    
    indices = {

        "MASI":
            masi.set_index("Date")["MASI"],

        "MASI RB":
            masi_rb.set_index("Date")["MASI_RB"],

        "MONIA":
            monia.set_index("Date_Reference")["MONIA"],

        "TMP":
            tmp.set_index("Date_Reference")["TMP"],

    }

    return indices


# =====================================================
# Préparation des benchmarks des fonds
# =====================================================

def preparer_benchmarks(
    table_reference,
    indices_disponibles,
):

    table = table_reference.copy()

    table["Indice_Benchmark_Corrige"] = table.apply(
        lambda r:
        CORRECTIONS_BENCHMARK.get(
            r["CODE ISIN"],
            r["Indice Bentchmark"],
        ),
        axis=1,
    )

    table["Benchmark_Normalise"] = (

        table["Indice_Benchmark_Corrige"]

        .apply(normaliser_benchmark)

        .apply(appliquer_mapping)

    )

    table["Benchmark_Disponible"] = (

        table["Benchmark_Normalise"]

        .isin(indices_disponibles.keys())

    )

    return table


# =====================================================
# Reconstruction hebdomadaire
# =====================================================

def valeur_indice_a_date(
    serie,
    date,
    tolerance=7,
):

    fenetre = serie[
        (serie.index <= date)
        &
        (
            serie.index
            >= date - pd.Timedelta(days=tolerance)
        )
    ]

    if fenetre.empty:
        return np.nan

    return fenetre.iloc[-1]


def construire_indices_hebdo(
    indices_disponibles,
    dates_vl,
):

    indices_hebdo = pd.DataFrame(
        index=dates_vl
    )

    for nom, serie in indices_disponibles.items():

        indices_hebdo[nom] = [

            valeur_indice_a_date(
                serie,
                d,
            )

            for d in dates_vl

        ]

    return indices_hebdo
# =====================================================
# Performances des benchmarks
# =====================================================

HORIZONS = {
    "Perf_1_mois": 30,
    "Perf_3_mois": 91,
    "Perf_6_mois": 182,
    "Perf_1_an": 365,
    "Perf_3_ans": 365 * 3,
}


def performance_indice_niveau(
    serie,
    date_fin,
    jours_arriere,
    tolerance_jours=10,
):

    serie = serie.dropna()

    date_debut = (
        pd.Timestamp(date_fin)
        - pd.Timedelta(days=jours_arriere)
    )

    fenetre = serie[
        (serie.index >= date_debut)
        &
        (serie.index <= pd.Timestamp(date_fin))
    ]

    if len(fenetre) < 2:
        return np.nan

    if (
        serie.index.min()
        >
        date_debut + pd.Timedelta(days=tolerance_jours)
    ):
        return np.nan

    return (
        fenetre.iloc[-1]
        / fenetre.iloc[0]
    ) - 1


def construire_table_benchmarks(
    indices_disponibles,
    date_reference,
):

    performances = {}

    for indice in ["MASI", "MASI RB"]:

        performances[indice] = {}

        for nom, jours in HORIZONS.items():

            performances[indice][nom] = (
                performance_indice_niveau(
                    indices_disponibles[indice],
                    date_reference,
                    jours,
                )
            )

    for indice in ["MONIA", "TMP"]:

        serie = indices_disponibles[indice].dropna()

        ligne = {}

        for nom, jours in HORIZONS.items():

            fenetre = serie[
                serie.index
                >= date_reference - pd.Timedelta(days=jours)
            ]

            if fenetre.empty:
                ligne[nom] = np.nan
            else:
                ligne[nom] = (
                    fenetre.mean()
                    / 100
                ) * (jours / 365)

        performances[indice] = ligne

    table = pd.DataFrame(
        performances
    ).T

    table.index.name = "Indice"

    return table


# =====================================================
# Fusion fonds / benchmark
# =====================================================

def ajouter_benchmarks(
    base_fonds,
    table_benchmarks,
):

    base = base_fonds.copy()

    for horizon in HORIZONS:

        base[f"{horizon}_Benchmark"] = (

            base["Benchmark_Normalise"]

            .map(

                lambda x:
                table_benchmarks.loc[x, horizon]

                if x in table_benchmarks.index
                else np.nan

            )

        )

        base[f"Ecart_{horizon.replace('Perf_', '')}"] = (

            base[horizon]

            -

            base[f"{horizon}_Benchmark"]

        )

    return base


# =====================================================
# Pipeline complet
# =====================================================

def construire_benchmarks(
    table_reference,
    table_performances,
    vl_corrigee,
):

    indices = construire_indices()

    table_reference = preparer_benchmarks(
        table_reference,
        indices,
    )

    indices_hebdo = construire_indices_hebdo(
        indices,
        vl_corrigee.index,
    )

    table_benchmarks = construire_table_benchmarks(
        indices,
        vl_corrigee.index.max(),
    )

    base = table_reference.merge(
        table_performances,
        on="CODE ISIN",
        how="left",
    )

    base = ajouter_benchmarks(
        base,
        table_benchmarks,
    )

    return (
        base,
        indices_hebdo,
        table_benchmarks,
    )
