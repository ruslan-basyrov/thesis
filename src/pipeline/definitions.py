import dagster as dg
import pandas as pd

from pipeline.clean import clean_survey
from pipeline.couples import make_couples
from pipeline.document import install_extension, render_document
from pipeline.filepaths import COUPLES, DOCUMENT, EXTENSIONS, SURVEY_CLEAN, SURVEY_DTA

survey = dg.AssetSpec(
    key="survey",
    group_name="sources",
    description="Hand-placed register microdata (1990-2007), never committed in git.",
    metadata={"path": dg.MetadataValue.path(SURVEY_DTA)},
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


@dg.asset(deps=[survey_clean], group_name="couples")
def couples() -> dg.MaterializeResult:
    """One first-birth couple per row, with whether the mother is the more
    educated."""
    df = make_couples(pd.read_parquet(SURVEY_CLEAN))
    df.to_parquet(COUPLES)

    ed = df.dropna(subset=["hypo"])
    return dg.MaterializeResult(
        metadata={
            "rows": len(df),
            "with_education": len(ed),
            "hypogamous": int(ed.hypo.sum()),
            "share": round(float(ed.hypo.mean()), 4),
        }
    )


@dg.asset_check(asset=couples, description="Verify that counts are correct.")
def correct_counts() -> dg.AssetCheckResult:
    df = pd.read_parquet(COUPLES)
    ed = df.dropna(subset=["hypo"])
    counts = {
        "rows": len(df),
        "with_education": len(ed),
        "hypogamous": int(ed.hypo.sum()),
    }
    expected = {"rows": 32234, "with_education": 29482, "hypogamous": 6208}
    return dg.AssetCheckResult(
        passed=counts == expected,
        metadata={**counts, "expected": str(expected)},
    )


@dg.asset(group_name="document")
def extension() -> dg.MaterializeResult:
    """The custom quarto extension to render both to PDF and HTML, 
    added or updated in place."""
    install_extension()
    return dg.MaterializeResult(metadata={"path": dg.MetadataValue.path(EXTENSIONS)})


@dg.asset(deps=[couples, extension], group_name="document")
def document() -> dg.MaterializeResult:
    """The thesis' document."""
    render_document()
    return dg.MaterializeResult(metadata={"path": dg.MetadataValue.path(DOCUMENT)})


defs = dg.Definitions(
    assets=dg.with_source_code_references(
        [survey, survey_clean, couples, extension, document]
    ),
    asset_checks=[correct_counts],
)
