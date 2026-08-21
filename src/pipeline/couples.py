import pandas as pd

MOTHER_EDU = ["compulsory", "apprenticeship", "Matura", "tertiary"]


def couples_shares(df: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    """Couples in each mother x father cell for the given years, with each
    cell's share of its year."""
    kept = df.dropna(subset=["mother_edu", "father_edu"])
    kept = kept[kept.year.isin(years)]
    cells = (
        kept.groupby(["year", "mother_edu", "father_edu"], observed=False)
        .size()
        .rename("count")
        .reset_index()
    )
    cells["share"] = cells["count"] / cells.groupby("year")["count"].transform("sum")
    return cells.rename(columns={"mother_edu": "mother", "father_edu": "father"})


def decomposition(df: pd.DataFrame, base: int, target: int) -> pd.DataFrame:
    """One row per cell of the mother x father table, with the counts for both
    years and for the two counterfactual tables.

    Iterative proportional fitting scales whole rows and whole columns, so the
    odds ratios do not change. Each fitted table keeps one year's association
    and takes the other year's margins."""
    kept = df.dropna(subset=["mother_edu", "father_edu"])

    def table(year: int) -> pd.DataFrame:
        """The year's couples as a mother x father table of counts."""
        return (
            kept[kept.year == year]
            .groupby(["mother_edu", "father_edu"], observed=False)
            .size()
            .unstack(fill_value=0)
            .astype(float)
        )

    def fit(start: pd.DataFrame, goal: pd.DataFrame) -> pd.DataFrame:
        """The start table scaled by rows and columns to the goal's margins."""
        rows, cols = goal.sum(axis=1), goal.sum(axis=0)
        fitted = start
        # In the text, each iteration fits table only to one side of margins.
        # Here, both sides are fitted in a single iteration for brevity of code.
        # The two approaches do not differ in the results.
        for _ in range(100):
            fitted = fitted.mul(rows / fitted.sum(axis=1), axis=0)
            fitted = fitted.mul(cols / fitted.sum(axis=0), axis=1)
            if (fitted.sum(axis=1) - rows).abs().max() < 1e-9:
                return fitted
        raise RuntimeError("the fit did not reach the target margins")

    start, observed = table(base), table(target)
    cells = start.stack().rename("base").reset_index()
    cells["counterfactual"] = fit(start, observed).stack().values
    cells["reverse"] = fit(observed, start).stack().values
    cells["observed"] = observed.stack().values
    cells["difference"] = cells.observed - cells.counterfactual
    return cells.rename(columns={"mother_edu": "mother", "father_edu": "father"})


def hypogamy_share(cells: pd.DataFrame, column: str) -> float:
    """The share of `column` in the cells where the mother's level is higher."""
    rank = {level: i for i, level in enumerate(MOTHER_EDU)}
    higher = cells.mother.map(rank) > cells.father.map(rank)
    return float(cells.loc[higher, column].sum() / cells[column].sum())
