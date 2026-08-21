import dagster as dg
import pandas as pd

from pipeline.clean import clean_ess, clean_survey
from pipeline import cohorts, couples
from pipeline.document import install_extension, prerender_figures, render_document
from pipeline.filepaths import (
    DOCUMENT,
    ESS_CLEAN,
    ESS_CSV,
    EXTENSIONS,
    FIGURES,
    COUPLES_SHARES,
    DECOMPOSITION,
    TERTIARY_DIFFERENCE,
    SURVEY_CLEAN,
    SURVEY_DTA,
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


@dg.asset(group_name="document")
def extension() -> dg.MaterializeResult:
    """The custom quarto extension to render both to PDF and HTML,
    added or updated in place."""
    install_extension()
    return dg.MaterializeResult(metadata={"path": dg.MetadataValue.path(EXTENSIONS)})


@dg.asset(
    deps=[tertiary_difference, couples_shares, decomposition, extension],
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
            extension,
            figures,
            document,
        ]
    )
)
