from anyio import Path
from openpyxl import writer
import pandas as pd
from scipy import stats
def construire_base_finale(
    table_reference,
    table_performances,
    table_perf_benchmarks,
):

    base_finale = table_reference[
        [
            "CODE ISIN",
            "OPCVM",
            "Société de Gestion",
            "Classification",
            "AN",
            "Sensibilité",
            "Indice Bentchmark",
            "Benchmark_Normalise",
        ]
    ].merge(
        table_performances,
        on="CODE ISIN",
        how="left",
    )

    horizons = [
        "Perf_1_mois",
        "Perf_3_mois",
        "Perf_6_mois",
        "Perf_1_an",
        "Perf_3_ans",
    ]
    table_perf_benchmarks.index = (
        table_perf_benchmarks.index
        .astype(str)
        .str.strip()
        .str.upper()
    )

    base_finale["Benchmark_Normalise"] = (
        base_finale["Benchmark_Normalise"]
        .astype(str)
        .str.strip()
        .str.upper()
    )
    for h in horizons:

        base_finale[f"{h}_Benchmark"] = (
            base_finale["Benchmark_Normalise"]
            .map(
                lambda b:
                table_perf_benchmarks.at[b, h]
                if b in table_perf_benchmarks.index
                else pd.NA
            )
        )

        base_finale[
            f"Ecart_{h.replace('Perf_', '')}"
        ] = (
            base_finale[h]
            -
            base_finale[f"{h}_Benchmark"]
        )

    return base_finale
def exporter_livrable1(
    chemin_excel,
    base_finale,
    vl_corrigee,
    indices_hebdo,
    rendements_hebdo,
    log_virgule,
    log_rupture,
    courbe_bam,
):
    Path(chemin_excel).parent.mkdir(
        parents=True,
        exist_ok=True
    )
    with pd.ExcelWriter(
        chemin_excel,
        engine="openpyxl",
    ) as writer:

        base_finale.to_excel(
            writer,
            sheet_name="Base_OPCVM",
            index=False,
        )

        vl_corrigee.to_excel(
            writer,
            sheet_name="VL_Historique",
        )

        indices_hebdo.to_excel(
            writer,
            sheet_name="Indices_Hebdo",
        )

        rendements_hebdo.to_excel(
            writer,
            sheet_name="Rendements_Hebdo",
        )
        
        stats = (
            base_finale
            .groupby("Classification")
            .agg(
                Nombre=("CODE ISIN", "count"),
                Perf_1_an=("Perf_1_an", "mean"),
                Perf_3_ans=("Perf_3_ans", "mean"),
            )
            .reset_index()
        )

        stats.to_excel(
            writer,
            sheet_name="Statistiques_Categorie",
            index=False,
        ) 
        
        courbe_bam.to_excel(
            writer,
            sheet_name="Courbe_Taux_BAM",
            index=False,
        )
        
        log_virgule.to_excel(
            writer,
            sheet_name="Log_Anomalies_Virgule",
            index=False,
        )

        log_rupture.to_excel(
            writer,
            sheet_name="Log_Anomalies_Rupture",
            index=False,
        )

    print("Livrable 1 exporté avec succès.")