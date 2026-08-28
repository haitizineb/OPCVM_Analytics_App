"""
maj.py
======
Mise à jour automatique de la base OPCVM.

Stratégie :
    1. Téléchargement incrémental des nouvelles semaines ASFIM
    2. Reconstruction complète du pipeline (plus sûr que la mise à jour colonne par colonne)
    3. Export du nouveau livrable Excel

Usage :
    python maj.py
    # ou depuis app.py : import maj; maj.mettre_a_jour()
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

# ==========================================================
# CHEMINS
# ==========================================================

ROOT = Path(__file__).resolve().parent

DATA = ROOT / "data"
RAW = DATA / "raw"
RAW_HISTORIQUE = DATA / "raw_historique"
EXPORTS = DATA / "exports"

LIVRABLE = DATA / "livrable1_base_opcvm.xlsx"
COURBE_BAM_CSV = DATA / "courbe_taux_BAM_2025_2026.csv"

# Création des dossiers si besoin
for dossier in [DATA, RAW, RAW_HISTORIQUE, EXPORTS]:
    dossier.mkdir(parents=True, exist_ok=True)

# ==========================================================
# IMPORTS DES MODULES UTILS
# ==========================================================

try:
    from utils.telechargement import telecharger_asfim
    from utils.nettoyage import charger_donnees_nettoyees
    from utils.performances import (
        construire_table_performances,
        construire_performance_complete,
    )
    from utils.benchmarks import construire_benchmarks
    from utils.risque import (
        construire_risque,
        ajouter_classements,
        ajouter_score,
    )
    from utils.scoring import construire_scoring
    from utils.courbe_bam import construire_courbe_bam
    from utils.export import (
        construire_base_finale,
        exporter_livrable1,
    )
except ImportError as e:
    print(f"❌ Erreur d'import : {e}")
    print("Vérifie que le dossier 'utils/' est bien présent.")
    sys.exit(1)


# ==========================================================
# ETAPE 1 — Téléchargement ASFIM
# ==========================================================

def derniere_semaine_disponible(dossier: Path) -> date | None:
    """Retourne la date de la semaine la plus récente déjà présente."""
    fichiers = sorted(dossier.glob("*.xlsx"))
    if not fichiers:
        return None

    dates = []
    for f in fichiers:
        try:
            dates.append(pd.to_datetime(f.stem).date())
        except Exception:
            continue
    return max(dates) if dates else None


def etape_telechargement():
    """Télécharge les semaines manquantes depuis ASFIM."""
    print("\n" + "=" * 60)
    print("ETAPE 1 — Téléchargement ASFIM")
    print("=" * 60)

    derniere = derniere_semaine_disponible(RAW)

    if derniere is None:
        print("Aucun historique trouvé. Téléchargement complet depuis 2020...")
        date_debut = date(2020, 1, 1)
    else:
        print(f"Dernière semaine disponible : {derniere}")
        date_debut = derniere + timedelta(days=7)

    date_fin = date.today()

    if date_debut > date_fin:
        print("✓ Base déjà à jour. Aucun téléchargement nécessaire.")
        return False

    reussies, echouees = telecharger_asfim(
        date_debut=date_debut,
        date_fin=date_fin,
        dossier=RAW,
    )

    if echouees:
        print(f"⚠️  {len(echouees)} semaine(s) non récupérée(s).")

    return len(reussies) > 0


# ==========================================================
# ETAPE 2 — Reconstruction complète du pipeline
# ==========================================================

def etape_pipeline_complet():
    """Reconstruit toute la base de données depuis zéro."""
    print("\n" + "=" * 60)
    print("ETAPE 2 — Reconstruction de la base")
    print("=" * 60)

    # --- Nettoyage ---
    print("\n  → Nettoyage des données...")
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
    print(f"     ✓ {base_complete['CODE ISIN'].nunique()} fonds | {len(vl_corrigee)} semaines")

    # --- Performances ---
    print("\n  → Calcul des performances...")
    table_performances = construire_table_performances(vl_corrigee)
    perf_complete = construire_performance_complete(
        table_reference,
        table_performances,
        vl_corrigee,
    )
    print(f"     ✓ {len(table_performances)} fonds analysés")

    # --- Benchmarks ---
    print("\n  → Téléchargement des benchmarks...")
    base_benchmarks, indices_hebdo, table_perf_benchmarks = construire_benchmarks(
        table_reference,
        table_performances,
        vl_corrigee,
    )
    print(f"     ✓ Indices : {', '.join(table_perf_benchmarks.index)}")

    # --- Risque ---
    print("\n  → Analyse du risque...")
    table_risque = construire_risque(
        perf_complete,
        vl_corrigee,
        rendements_hebdo,
    )
    table_risque = ajouter_classements(table_risque)
    table_risque = ajouter_score(table_risque)
    print(f"     ✓ Volatilité & drawdown calculés")

    # --- Scoring ---
    print("\n  → Scoring OPCVM...")
    table_scoring = construire_scoring(table_risque)
    print(f"     ✓ Top 1 : {table_scoring.iloc[0]['OPCVM']} ({table_scoring.iloc[0]['Score_Global']:.1f})")

    # --- Courbe BAM ---
    print("\n  → Courbe des taux BAM...")
    try:
        courbe_bam = construire_courbe_bam()
        courbe_bam.to_csv(COURBE_BAM_CSV, index=False, encoding="utf-8-sig")
        print(f"     ✓ {courbe_bam['Date_reference'].nunique()} semaines de courbes")
    except Exception as e:
        print(f"     ⚠️  Erreur BAM : {e}")
        courbe_bam = pd.DataFrame()

    # --- Base finale ---
    print("\n  → Construction de la base finale...")
    base_finale = construire_base_finale(
        base_benchmarks,
        table_performances,
        table_perf_benchmarks,
    )

    return (
        base_finale,
        vl_corrigee,
        indices_hebdo,
        rendements_hebdo,
        log_virgule,
        log_rupture,
        courbe_bam,
        table_scoring,
    )


# ==========================================================
# ETAPE 3 — Export
# ==========================================================

def etape_export(
    base_finale,
    vl_corrigee,
    indices_hebdo,
    rendements_hebdo,
    log_virgule,
    log_rupture,
    courbe_bam,
    table_scoring,
):
    """Exporte le livrable et les données pour Streamlit."""
    print("\n" + "=" * 60)
    print("ETAPE 3 — Export des données")
    print("=" * 60)

    # Livrable 1 Excel
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
    print(f"✓ Livrable 1 : {LIVRABLE}")

    # Exports CSV pour l'app Streamlit
    table_scoring.to_csv(
        EXPORTS / "scoring.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print(f"✓ Scoring : {EXPORTS / 'scoring.csv'}")

    base_finale.to_csv(
        EXPORTS / "performances.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print(f"✓ Performances : {EXPORTS / 'performances.csv'}")

    print("\n" + "=" * 60)
    print("✅ MISE À JOUR TERMINÉE AVEC SUCCÈS")
    print("=" * 60)


# ==========================================================
# FONCTION PRINCIPALE
# ==========================================================

def mettre_a_jour():
    """
    Pipeline complet de mise à jour.
    Appelée depuis app.py ou en ligne de commande.
    """
    print("\n" + "=" * 60)
    print("OPCVM ANALYTICS — MISE À JOUR")
    print("=" * 60)

    # 1. Téléchargement
    a_telecharge = etape_telechargement()

    # 2. Reconstruction (même si pas de nouveau fichier, pour être sûr)
    (
        base_finale,
        vl_corrigee,
        indices_hebdo,
        rendements_hebdo,
        log_virgule,
        log_rupture,
        courbe_bam,
        table_scoring,
    ) = etape_pipeline_complet()

    # 3. Export
    etape_export(
        base_finale,
        vl_corrigee,
        indices_hebdo,
        rendements_hebdo,
        log_virgule,
        log_rupture,
        courbe_bam,
        table_scoring,
    )

    return True


# ==========================================================
# POINT D'ENTRÉE
# ==========================================================

if __name__ == "__main__":
    mettre_a_jour()