from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SURVEY_DTA = ROOT / "data/survey.dta"
ESS_CSV = ROOT / "data/ESS.csv"

BUILD = ROOT / "build"
BUILD.mkdir(exist_ok=True)

SURVEY_CLEAN = BUILD / "survey_clean.parquet"
ESS_CLEAN = BUILD / "ess_clean.parquet"

GEM_POLYGONS_ZIP = BUILD / "geo/gem_polygons.zip"
GEM_POINTS_ZIP = BUILD / "geo/gem_points.zip"
CENTROIDS = BUILD / "geo/centroids.parquet"
BUFFER = BUILD / "geo/buffer.geojson"
OSM_DIR = BUILD / "osm"
REGION_PBF = BUILD / "osm/region.osm.pbf"
VALHALLA_DIR = BUILD / "valhalla"
VALHALLA_CONFIG = BUILD / "valhalla/valhalla.json"
VALHALLA_TILES = BUILD / "valhalla/tiles.tar"

# the figures read their data as text, from quarto's deno
TERTIARY_DIFFERENCE = BUILD / "tertiary_difference.json"
COUPLES_SHARES = BUILD / "couples_shares.json"
DECOMPOSITION = BUILD / "decomposition.json"
ISOCHRONE_MARKETS = BUILD / "isochrone_markets.json"
FIGURES = BUILD / "figures"

DOCUMENT = ROOT / "index.qmd"
QUARTO_YML = ROOT / "_quarto.yml"
EXTENSIONS = ROOT / "_extensions"
PRERENDER = EXTENSIONS / "ruslan-basyrov/acuity-figures/prerender.ts"
