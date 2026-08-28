from pathlib import Path
from datetime import date

from utils.telechargement import telecharger_asfim

from utils.nettoyage import (
    charger_donnees_nettoyees,
)

from utils.performances import (
    construire_table_performances,
    construire_performance_complete,
)

from utils.benchmarks import (
    construire_benchmarks,
)

from utils.courbe_bam import (
    construire_courbe_bam,
)

from utils.courbe_analyse import (
    construire_resume_courbe,
)

from utils.stress import (
    construire_stress,
)

from utils.risque import (
    construire_risque,
    ajouter_classements,
    ajouter_score,
)

from utils.scoring import (
    construire_scoring,
)

from utils.export import (
    construire_base_finale,
    exporter_livrable1,
)


# ==========================================================
# DOSSIERS
# ==========================================================

ROOT = Path(__file__).resolve().parent.parent

DATA = ROOT / "data"

RAW = DATA / "raw"

RAW_HISTORIQUE = DATA / "raw_historique"

EXPORTS = DATA / "exports"

LIVRABLE = EXPORTS / "livrable1_base_opcvm.xlsx"

EXPORTS.mkdir(parents=True, exist_ok=True)


# ==========================================================
# PIPELINE PRINCIPAL
# ==========================================================

def mettre_a_jour():

    print("=" * 60)
    print("MISE A JOUR DES DONNEES OPCVM")
    print("=" * 60)

    # ------------------------------------------------------
    # Téléchargement des nouvelles semaines ASFIM
    # ------------------------------------------------------

    print("\nTéléchargement des nouvelles semaines...")

    telecharger_asfim(
        date_debut=date(2025, 4, 18),
        date_fin=date.today(),
        dossier=RAW,
    )

    print("✓ Téléchargement terminé.")
        # ------------------------------------------------------
    # Chargement et nettoyage des données
    # ------------------------------------------------------

    print("\nConstruction de la base...")

    (
        base_complete,
        table_reference,
        vl_corrigee,
        rendements_hebdo,
        log_virgule,
        log_rupture,
    ) = charger_donnees_nettoyees(
        dossier_raw=RAW,
        dossier_historique=RAW_HISTORIQUE,
    )

    print(f"✓ {base_complete.shape[0]} observations")
    print(f"✓ {table_reference.shape[0]} OPCVM")


    # ------------------------------------------------------
    # Calcul des performances
    # ------------------------------------------------------

    print("\nCalcul des performances...")

    table_performances = construire_table_performances(
        vl_corrigee
    )

    performance_complete = construire_performance_complete(
        table_reference,
        table_performances,
        vl_corrigee,
    )

    print("✓ Performances calculées.")


    # ------------------------------------------------------
    # Construction des benchmarks
    # ------------------------------------------------------

    print("\nConstruction des benchmarks...")

    (
        base_benchmarks,
        indices_hebdo,
        table_perf_benchmarks,
    ) = construire_benchmarks(
        table_reference,
        table_performances,
        vl_corrigee,
    )

    print("✓ Benchmarks calculés.")
        # ------------------------------------------------------
    # Courbe des taux BAM
    # ------------------------------------------------------

    print("\nConstruction de la courbe des taux BAM...")

    courbe_bam = construire_courbe_bam()

    resume_courbe = construire_resume_courbe(
        courbe_bam
    )

    print(
        f"✓ {courbe_bam['Date_reference'].nunique()} courbes téléchargées."
    )


    # ------------------------------------------------------
    # Stress tests
    # ------------------------------------------------------

    print("\nCalcul des stress tests...")

    stress, resume_stress = construire_stress(
        base_benchmarks
    )

    print("✓ Stress tests calculés.")


    # ------------------------------------------------------
    # Scoring
    # ------------------------------------------------------

    print("\nCalcul des scores...")

    scores = construire_scores(
        performance_complete
    )

    print("✓ Scores calculés.")


    # ------------------------------------------------------
    # Base finale
    # ------------------------------------------------------

    print("\nConstruction de la base finale...")

    base_finale = construire_base_finale(
        table_reference,
        table_performances,
        table_perf_benchmarks,
    )

    print("✓ Base finale construite.")


    # ------------------------------------------------------
    # Export
    # ------------------------------------------------------

    print("\nExport du livrable...")

    exporter_livrable1(
        chemin_excel=LIVRABLE,
        base_finale=base_finale,
        vl_corrigee=vl_corrigee,
        indices_hebdo=indices_hebdo,
        rendements_hebdo=rendements_hebdo,
        log_virgule=log_virgule,
        log_rupture=log_rupture,
        courbe_bam=courbe_bam,
    )

    print("\n✓ Livrable exporté avec succès.")

    print("=" * 60)
    print("MISE A JOUR TERMINEE")
    print("=" * 60)
        print("\nCalcul des indicateurs de risque...")

    risque = construire_risque(
        performance_complete,
        rendements_hebdo,
        vl_corrigee,
    )

    print("✓ Risque calculé.")
    risque = ajouter_classements(risque)

    risque = ajouter_score(risque)
    
    print("\nCalcul du scoring...")

    scoring = construire_scoring(
        risque
    )

    print("✓ Scoring calculé.")
    return {
        "base_complete": base_complete,
        "table_reference": table_reference,
        "performance_complete": performance_complete,
        "risque": risque,
        "scoring": scoring,
        "stress": stress,
        "resume_stress": resume_stress,
        "resume_courbe": resume_courbe,
        "base_finale": base_finale,
    }

    
if __name__ == "__main__":
    mettre_a_jour()