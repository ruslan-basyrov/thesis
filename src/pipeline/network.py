"""The 2014 road network for Austria and 100 km around, routed by Valhalla.

Heavy artifacts are skipped when they already exist. 
You can run the whole chain without dagster:

    uv run python -m pipeline.network
"""

import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

import geopandas as gpd
import osmium
import pandas as pd
import shapely
from valhalla import Actor, get_config

from pipeline.filepaths import (
    BUFFER,
    CENTROIDS,
    GEM_POINTS_ZIP,
    GEM_POLYGONS_ZIP,
    ISOCHRONE_MARKETS,
    OSM_DIR,
    REGION_PBF,
    VALHALLA_CONFIG,
    VALHALLA_DIR,
    VALHALLA_TILES,
)

WFS = (
    "https://www.statistik.at/gs-open/GEODATA/ows?service=WFS&version=1.0.0"
    "&request=GetFeature&typeName=GEODATA:STATISTIK_AUSTRIA_{}_20220101"
    "&outputFormat=SHAPE-ZIP"
)
GEOFABRIK = "https://download.geofabrik.de/europe/{}-140101.osm.pbf"

# Austria and every country within the buffer: the fastest route between two
# Austrian municipalities can cross a border.
COUNTRIES = [
    "austria", "croatia", "czech-republic", "germany", "hungary",
    "italy", "liechtenstein", "slovakia", "slovenia", "switzerland",
]
BUFFER_KM = 100
BATCH = 1_000_000  # nodes per vectorized point-in-polygon test
CONTOURS = [20, 30]  # defined in car minutes


def fetch(url: str, dest: Path) -> None:
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    have = tmp.stat().st_size if tmp.exists() else 0
    headers = {"User-Agent": "thesis-pipeline"} | (
        {"Range": f"bytes={have}-"} if have else {}
    )
    print(f"fetching {url}", flush=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as r:
        with open(tmp, "ab" if r.status == 206 else "wb") as f:
            shutil.copyfileobj(r, f)
    tmp.replace(dest)


def build_geography() -> pd.DataFrame:
    """Statistik Austria municipality polygons and population-weighted
    centroids, Gebietsstand 2022-01-01."""
    fetch(WFS.format("GEM"), GEM_POLYGONS_ZIP)
    fetch(WFS.format("GEM_MP"), GEM_POINTS_ZIP)
    mp = gpd.read_file(f"zip://{GEM_POINTS_ZIP}")
    pts = mp.set_index(mp.g_id.astype(int)).sort_index().geometry.to_crs(4326)
    df = pd.DataFrame({"gkz": pts.index, "lon": pts.x, "lat": pts.y})
    df.to_parquet(CENTROIDS, index=False)
    return df


def clip(src: Path, out: Path, geom: shapely.Geometry) -> None:
    """Keep every node inside the polygon, then let osmium complete the
    references: every way with a node inside, kept whole past the boundary so
    a road crossing the clip line stays routable, and every relation with a
    kept member. Only id sets stay in memory."""
    x0, y0, x1, y1 = geom.bounds
    keep = osmium.IdTracker()
    ids, xs, ys = [], [], []

    def flush() -> None:
        for i, inside in zip(ids, shapely.contains_xy(geom, xs, ys)):
            if inside:
                keep.add_node(i)
        ids.clear()
        xs.clear()
        ys.clear()

    for node in osmium.FileProcessor(src, osmium.osm.NODE):
        loc = node.location
        if loc.valid() and x0 <= loc.lon <= x1 and y0 <= loc.lat <= y1:
            ids.append(node.id)
            xs.append(loc.lon)
            ys.append(loc.lat)
            if len(ids) >= BATCH:
                flush()
    flush()

    keep.complete_forward_references(src)
    keep.complete_backward_references(src)

    tmp = out.with_name("." + out.name)  # a killed run must not look finished
    with osmium.SimpleWriter(str(tmp), overwrite=True) as writer:
        for obj in osmium.FileProcessor(src).with_filter(keep.id_filter()):
            writer.add(obj)
    tmp.replace(out)


def build_region() -> None:
    """One PBF for the whole region: valhalla corrupts its graph when built
    from several extracts that duplicate ways along shared borders, so the
    clipped countries are merged first, border objects written once."""
    if REGION_PBF.exists():
        return
    if not BUFFER.exists():
        gem = gpd.read_file(f"zip://{GEM_POLYGONS_ZIP}")
        shape = gem.geometry.union_all().buffer(BUFFER_KM * 1000).simplify(1000)
        gpd.GeoSeries([shape], crs=gem.crs).to_crs(4326).to_file(BUFFER)
    geom = gpd.read_file(BUFFER).geometry.union_all()
    shapely.prepare(geom)
    for country in COUNTRIES:
        out = OSM_DIR / f"{country}-clipped.osm.pbf"
        if out.exists():
            continue
        fetch(GEOFABRIK.format(country), OSM_DIR / f"{country}.osm.pbf")
        print(f"clipping {country}", flush=True)
        clip(OSM_DIR / f"{country}.osm.pbf", out, geom)
    merged = osmium.MergeInputReader()
    for country in COUNTRIES:
        merged.add_file(str(OSM_DIR / f"{country}-clipped.osm.pbf"))
    tmp = REGION_PBF.with_name("." + REGION_PBF.name)
    with osmium.SimpleWriter(str(tmp), overwrite=True) as writer:
        merged.apply(writer, simplify=True)
    tmp.replace(REGION_PBF)


def valhalla_config() -> Path:
    # get_config resolves both tile paths strictly, hence mkdir and touch
    (VALHALLA_DIR / "tiles").mkdir(parents=True, exist_ok=True)
    VALHALLA_TILES.touch()
    cfg = get_config(tile_extract=VALHALLA_TILES, tile_dir=VALHALLA_DIR / "tiles")
    VALHALLA_CONFIG.write_text(json.dumps(cfg))
    return VALHALLA_CONFIG


def build_tiles() -> None:
    if VALHALLA_TILES.exists() and VALHALLA_TILES.stat().st_size:
        return
    cfg = valhalla_config()
    subprocess.run(
        [shutil.which("valhalla_build_tiles"), "-c", cfg, REGION_PBF], check=True
    )
    subprocess.run(
        [shutil.which("valhalla_build_extract"), "-c", cfg, "-O"], check=True
    )


def route_minutes(a: int, b: int) -> float:
    cent = pd.read_parquet(CENTROIDS).set_index("gkz")
    locations = [{"lat": cent.lat[g], "lon": cent.lon[g]} for g in (a, b)]
    actor = Actor(str(valhalla_config()))
    trip = actor.route({"locations": locations, "costing": "auto"})
    return trip["trip"]["summary"]["time"] / 60


def build_markets() -> dict[str, tuple[str, int]]:
    """The two showcase mate markets for the isochrone figure, as GeoJSON in
    WGS84: 20/30-minute contours, seed centroid, and how many of the 2,115
    municipality centroids the 30-minute contour holds."""
    gem = gpd.read_file(f"zip://{GEM_POLYGONS_ZIP}")
    gem = gem.set_index(gem.g_id.astype(int))
    mp = gpd.read_file(f"zip://{GEM_POINTS_ZIP}")
    mp = mp.set_index(mp.g_id.astype(int))

    # alpine showcase: settlement pinned to a valley, the largest offset
    # between the population-weighted and the geometric centroid
    alpine = int(mp.geometry.distance(gem.geometry.centroid).idxmax())
    # lowland showcase: canon's densest 30-minute market, to be re-derived
    # once our own durations matrix is built
    lowland = int(gem.index[gem.g_name == "Meggenhofen"][0])

    cent = pd.read_parquet(CENTROIDS).set_index("gkz")
    actor = Actor(str(valhalla_config()))
    panels = {}
    for label, gkz in {"alpine": alpine, "lowland": lowland}.items():
        seed = cent.loc[gkz]
        iso = actor.isochrone({
            "locations": [{"lat": seed.lat, "lon": seed.lon}],
            "costing": "auto",
            "contours": [{"time": t} for t in CONTOURS],
            "polygons": True,
        })
        # d3 winds exterior rings clockwise; valhalla emits the RFC 7946 order
        for f in iso["features"]:
            f["geometry"] = shapely.geometry.mapping(shapely.orient_polygons(
                shapely.geometry.shape(f["geometry"]), exterior_cw=True
            ))
        outer = shapely.union_all([
            shapely.geometry.shape(f["geometry"])
            for f in iso["features"]
            if f["properties"]["contour"] == max(CONTOURS)
        ])
        panels[label] = {
            "name": gem.loc[gkz, "g_name"],
            "gkz": gkz,
            "within": int(shapely.contains_xy(outer, cent.lon, cent.lat).sum()),
            "seed": [round(float(seed.lon), 6), round(float(seed.lat), 6)],
            "contours": iso,
        }

    backdrop = gem.geometry.simplify(100).to_crs(4326).apply(
        lambda g: shapely.orient_polygons(g, exterior_cw=True)
    )
    # the union of the municipalities is the national border, which the figure
    # draws to show where the register data stop
    border = gpd.GeoSeries([gem.geometry.union_all()], crs=gem.crs).simplify(200)
    border = border.to_crs(4326).apply(
        lambda g: shapely.orient_polygons(g, exterior_cw=True)
    )
    ISOCHRONE_MARKETS.write_text(json.dumps({
        **panels,
        "municipalities": json.loads(backdrop.to_json()),
        "austria": json.loads(border.to_json()),
    }))
    return {label: (p["name"], p["within"]) for label, p in panels.items()}


if __name__ == "__main__":
    build_geography()
    build_region()
    build_tiles()
    print(build_markets())
