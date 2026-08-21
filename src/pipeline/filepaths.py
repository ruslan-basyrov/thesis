from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SURVEY_DTA = ROOT / "data/survey.dta"
ESS_CSV = ROOT / "data/ESS.csv"

BUILD = ROOT / "build"
BUILD.mkdir(exist_ok=True)

SURVEY_CLEAN = BUILD / "survey_clean.parquet"
ESS_CLEAN = BUILD / "ess_clean.parquet"

# the figures read their data as text, from quarto's deno
TERTIARY_DIFFERENCE = BUILD / "tertiary_difference.json"
COUPLES_SHARES = BUILD / "couples_shares.json"
DECOMPOSITION = BUILD / "decomposition.json"
FIGURES = BUILD / "figures"

DOCUMENT = ROOT / "index.qmd"
QUARTO_YML = ROOT / "_quarto.yml"
EXTENSIONS = ROOT / "_extensions"
PRERENDER = EXTENSIONS / "ruslan-basyrov/acuity-figures/prerender.ts"
