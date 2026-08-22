import dagster as dg
import pandas as pd

from pipeline.clean import clean_ess, clean_survey
from pipeline import cohorts, couples, network
from pipeline.document import install_extension, prerender_figures, render_document
from pipeline.filepaths import (
    DOCUMENT,
    ESS_CLEAN,
    ESS_CSV,
    EXTENSIONS,
    FIGURES,
    COUPLES_SHARES,
    DECOMPOSITION,
    REGION_PBF,
    TERTIARY_DIFFERENCE,
    SURVEY_CLEAN,
    SURVEY_DTA,
    VALHALLA_TILES,
)

survey = dg.AssetSpec(
    key="survey",
    group_name="sources",
    description="Hand-placed register microdata (1990-2007), not committed in git.",
    metadata={"path": dg.MetadataValue.path(SURVEY_DTA)},
)


ess = dg.AssetSpec(
    key="ess",
    group_name="sources",
    description="Hand-placed European Social Survey extract, not committed in git.",
    metadata={"path": dg.MetadataValue.path(ESS_CSV)},
)


@dg.asset(deps=[survey], group_name="cleaning")
def survey_clean() -> dg.MaterializeResult:
    """The whole register microdata, renamed, plus the birth year."""
    df = clean_survey()
    df.to_parquet(SURVEY_CLEAN)
    return dg.MaterializeResult(
        metadata={
            "rows": len(df),
            "columns": len(df.columns),
            "years": f"{df.year.min()}-{df.year.max()}",
        }
    )


@dg.asset(deps=[ess], group_name="cleaning")
def ess_clean() -> dg.MaterializeResult:
    """Own education on three levels, with the survey weights."""
    df = clean_ess()
    df.to_parquet(ESS_CLEAN)
    return dg.MaterializeResult(
        metadata={
            "rows": len(df),
            "countries": int(df.country.nunique()),
            "with_education": int(df.own_edu.notna().sum()),
        }
    )


@dg.asset(deps=[ess_clean], group_name="cohorts")
def tertiary_difference() -> dg.MaterializeResult:
    """The female educational advantage by country and by the respondent's
    birth cohort: the share of women holding tertiary education minus the
    share of men."""
    df = cohorts.tertiary_difference(pd.read_parquet(ESS_CLEAN))
    df.to_json(TERTIARY_DIFFERENCE, orient="records")

    at = df[df.country == "AT"].set_index("cohort").lead
    return dg.MaterializeResult(
        metadata={
            "rows": len(df),
            "countries": int(df.country.nunique()),
            "austria_oldest": round(float(at[cohorts.COHORT_LABELS[0]]), 4),
            "austria_youngest": round(float(at[cohorts.COHORT_LABELS[-1]]), 4),
        }
    )


@dg.asset(deps=[survey_clean], group_name="couples")
def couples_shares() -> dg.MaterializeResult:
    """Couples in each mother x father cell in 1990 and 2007, with each
    cell's share of its year."""
    df = couples.couples_shares(pd.read_parquet(SURVEY_CLEAN), [1990, 2007])
    df.to_json(COUPLES_SHARES, orient="records")
    return dg.MaterializeResult(
        metadata={
            "couples_1990": int(df[df.year == 1990]["count"].sum()),
            "couples_2007": int(df[df.year == 2007]["count"].sum()),
            "largest_cell_1990": int(df[df.year == 1990]["count"].max()),
            "largest_cell_2007": int(df[df.year == 2007]["count"].max()),
        }
    )


@dg.asset(deps=[survey_clean], group_name="couples")
def decomposition() -> dg.MaterializeResult:
    """Both observed tables and the two counterfactuals: what the margins
    add to the rise in hypogamy."""
    df = couples.decomposition(pd.read_parquet(SURVEY_CLEAN), base=1990, target=2007)
    df.to_json(DECOMPOSITION, orient="records")
    base, fitted, reverse, observed = (
        couples.hypogamy_share(df, column)
        for column in ("base", "counterfactual", "reverse", "observed")
    )
    return dg.MaterializeResult(
        metadata={
            "hypogamy_1990": round(base, 4),
            "hypogamy_counterfactual": round(fitted, 4),
            "hypogamy_reverse": round(reverse, 4),
            "hypogamy_2007": round(observed, 4),
            "margins_share": round((fitted - base) / (observed - base), 4),
            "margins_share_reverse": round((observed - reverse) / (observed - base), 4),
            "couples": int(df.observed.sum()),
        }
    )


@dg.asset(group_name="network")
def geography() -> dg.MaterializeResult:
    """Statistik Austria municipality polygons and population-weighted
    centroids, Gebietsstand 2022-01-01, with Vienna as its 23 districts."""
    df = network.build_geography()
    return dg.MaterializeResult(metadata={"municipalities": len(df)})


@dg.asset(deps=[geography], group_name="network")
def region_osm() -> dg.MaterializeResult:
    """The ten Geofabrik 2014-01-01 extracts, clipped to 100 km around
    Austria with ways kept whole, merged into one region PBF."""
    network.build_region()
    return dg.MaterializeResult(
        metadata={"size_mb": round(REGION_PBF.stat().st_size / 1e6)}
    )


@dg.asset(deps=[region_osm], group_name="network")
def routing_graph() -> dg.MaterializeResult:
    """The Valhalla tile extract over the region, the graph every route,
    isochrone and duration is read from."""
    network.build_tiles()
    return dg.MaterializeResult(
        metadata={
            "size_mb": round(VALHALLA_TILES.stat().st_size / 1e6),
            "vienna_innsbruck_min": round(network.route_minutes(90101, 70101), 1),
        }
    )


@dg.asset(deps=[routing_graph, geography], group_name="network")
def isochrone_markets() -> dg.MaterializeResult:
    """The two showcase mate markets as 20/30-car-minute isochrone GeoJSON:
    the strongest alpine case and the densest lowland market."""
    picks = network.build_markets()
    return dg.MaterializeResult(
        metadata={
            label: f"{name}, {within} municipalities within 30 min"
            for label, (name, within) in picks.items()
        }
    )


@dg.asset(group_name="document")
def extension() -> dg.MaterializeResult:
    """The custom quarto extension to render both to PDF and HTML,
    added or updated in place."""
    install_extension()
    return dg.MaterializeResult(metadata={"path": dg.MetadataValue.path(EXTENSIONS)})


@dg.asset(
    deps=[tertiary_difference, couples_shares, decomposition,
          isochrone_markets, extension],
    group_name="document",
)
def figures() -> dg.MaterializeResult:
    """Every figures/*.fig.js drawn to SVG, with the include quarto stitches in.

    Quarto expands includes before it runs its own pre-render, so the include
    has to exist before the document builds."""
    prerender_figures()
    return dg.MaterializeResult(metadata={"path": dg.MetadataValue.path(FIGURES)})


@dg.asset(deps=[figures], group_name="document")
def document() -> dg.MaterializeResult:
    """The thesis' document."""
    render_document()
    return dg.MaterializeResult(metadata={"path": dg.MetadataValue.path(DOCUMENT)})


defs = dg.Definitions(
    assets=dg.with_source_code_references(
        [
            survey,
            survey_clean,
            ess,
            ess_clean,
            tertiary_difference,
            couples_shares,
            decomposition,
            geography,
            region_osm,
            routing_graph,
            isochrone_markets,
            extension,
            figures,
            document,
        ]
    )
)
