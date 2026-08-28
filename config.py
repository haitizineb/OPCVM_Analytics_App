from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

RAW_DIR = BASE_DIR / "raw"

RAW_ASFIM_DIR = RAW_DIR / "asfim"

RAW_HIST_DIR = RAW_DIR / "historique"

BENCHMARK_DIR = BASE_DIR / "benchmarks"

LIVRABLE_1 = DATA_DIR / "livrable1_base_opcvm.xlsx"