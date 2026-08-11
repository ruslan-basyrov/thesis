from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SURVEY_DTA = ROOT / "data/survey.dta"

BUILD = ROOT / "build"
BUILD.mkdir(exist_ok=True)

SURVEY_CLEAN = BUILD / "survey_clean.parquet"
COUPLES = BUILD / "couples.parquet"

DOCUMENT = ROOT / "index.qmd"
QUARTO_YML = ROOT / "_quarto.yml"
EXTENSIONS = ROOT / "_extensions"
