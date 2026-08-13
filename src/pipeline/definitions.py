import dagster as dg
import pandas as pd

from pipeline.clean import clean_ess, clean_survey
from pipeline import cohorts
from pipeline.document import install_extension, prerender_figures, render_document
from pipeline.filepaths import (
    DOCUMENT,
    ESS_CLEAN,
    ESS_CSV,
    EXTENSIONS,
    FIGURES,
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


@dg.asset(group_name="document")
def extension() -> dg.MaterializeResult:
    """The custom quarto extension to render both to PDF and HTML,
    added or updated in place."""
    install_extension()
    return dg.MaterializeResult(metadata={"path": dg.MetadataValue.path(EXTENSIONS)})


@dg.asset(deps=[tertiary_difference, extension], group_name="document")
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
        [survey, survey_clean, ess, ess_clean, tertiary_difference, extension, figures, document]
    )
)
