import numpy as np
import pandas as pd

# Dávid Erát's rule from his footnote 3, applied to 2 more rounds (now 11): 
#  - exclude countries with less than four rounds, 
#  - exclude Israel as outside Europe
# Rounds 10 and 11 lift Croatia, Iceland and Latvia over the bar, so 30 countries
# remain where he kept 27.
# The ages are the same as in his paper.
EXCLUDED_COUNTRIES = ["AL", "IL", "LU", "ME", "MK", "RO", "RS", "TR", "XK"]
AGES = (25, 55)

# Erát stops at an open 1980-, which rounds 10 and 11 would fill with a mix of
# later births seen at older ages. Closed bands instead, out to the last one the
# 25-year floor can reach.
COHORTS = [1899, 1954, 1959, 1964, 1969, 1974, 1979, 1984, 1989, 1998]
COHORT_LABELS = [
    "-1954",
    "1955-59",
    "1960-64",
    "1965-69",
    "1970-74",
    "1975-79",
    "1980-84",
    "1985-89",
    "1990-98",
]

def tertiary_difference(df):
    """The female educational advantage by country and by the respondent's own
    birth cohort: the share of women holding tertiary education minus the share
    of men.

    Everyone in range counts, partnered or not, so nothing here depends on who
    found a partner."""
    kept = df[
        df.age.between(*AGES)
        & ~df.country.isin(EXCLUDED_COUNTRIES)
        & df.own_edu.notna()
        & df.birth_year.notna()
        & df.sex.notna()
    ].copy()
    kept["cohort"] = pd.cut(kept.birth_year, COHORTS, labels=COHORT_LABELS)
    kept["high"] = kept.own_edu.eq("High").astype(float)

    out = []
    for (country, cohort), g in kept.groupby(["country", "cohort"], observed=True):
        women, men = g[g.sex == "woman"], g[g.sex == "man"]
        lead = np.average(women.high, weights=women.weight) - np.average(
            men.high, weights=men.weight
        )
        out.append(
            {"country": country, "cohort": str(cohort), "lead": lead, "n": len(g)}
        )
    return pd.DataFrame(out)
