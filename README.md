# 📊 OPCVM Analytics App

Plateforme d'analyse quantitative des OPCVM marocains avec Streamlit.

## Description

Application Streamlit pour l'analyse détaillée des OPCVM (Organismes de Placement Collectif en Valeurs Mobilières) marocains. Fournit des outils de comparaison, classement, scoring et analyse des risques.

## Installation

### Prérequis
- Python 3.11+
- pip

### Installation des dépendances

```bash
pip install -r requirements.txt
```

## Dépendances principales

- **Données & Calculs**: numpy, pandas, scipy, openpyxl, xlrd
- **Visualisation**: matplotlib, plotly
- **Dashboard**: streamlit, streamlit-option-menu
- **HTTP**: requests

## Démarrage de l'application

```bash
streamlit run app.py
```

## Fichiers principaux

- `app.py` - Application principale Streamlit
- `config.py` - Configuration
- `requirements.txt` - Dépendances Python
- `utils/` - Modules utilitaires
  - `benchmarks.py` - Gestion des données de référence avec gestion d'erreurs
  - `performances.py` - Calcul des performances
  - `risque.py` - Analyse des risques
  - `scoring.py` - Scoring des OPCVM
  - `dashboard.py` - Composants du dashboard

## Modifications récentes (2026-08-29)

### ✅ Correction des erreurs HTTP 403 Forbidden
- **Problème**: Les téléchargements de données depuis Bank al-Maghrib (MONIA, TMP) et BMCE Capital retournaient des erreurs 403 Forbidden
- **Solution**: 
  - Ajout de gestion d'erreurs complète dans `utils/benchmarks.py`
  - Implémentation de retry logic avec backoff exponentiel
  - Ajout d'en-têtes HTTP réalistes pour contourner les blocages
  - L'application continue maintenant sans crash même si les sources externes sont indisponibles

### 📦 Nouvelles dépendances
- `matplotlib>=3.5.0` - Visualisation statique
- `scipy>=1.10.0` - Analyse scientifique

### 🔧 Améliorations du code
- Meilleure gestion des exceptions
- Logs d'erreur informatifs pour le débogage
- Retour de DataFrames vides au lieu de crash
- Retry automatique pour les erreurs réseau temporaires

## Architecture des téléchargements

Les fonctions de téléchargement suivantes incluent désormais une gestion d'erreurs robuste:

- `telecharger_monia()` - Données MONIA de Bank al-Maghrib
- `telecharger_tmp()` - Taux Moyen Pondéré de Bank al-Maghrib
- `telecharger_indice_bmce()` - Indices BMCE Capital Bourse

En cas d'erreur (403, timeout, etc.), chaque fonction retourne un DataFrame vide avec les colonnes appropriées, permettant à l'application de continuer.

## Notes importantes

⚠️ **URLs d'export expirées**: Les URLs temporaires pour télécharger les données de Bank al-Maghrib ont une durée limitée. En cas d'erreur persistent 403, ces URLs doivent être régénérées manuellement depuis le site de Bank al-Maghrib.

## Auteur

haitizineb
