import pandas as pd

from pipeline.filepaths import ESS_CSV, SURVEY_DTA

COLUMNS = {
    "c_birth_date": "birth_date",
    "marr_date": "marriage_date",
    "m_age_at_birth": "mother_age",
    "f_age_at_birth": "father_age",
    "m_edu4": "mother_edu",
    "f_edu4": "father_edu",
    "edu4_comp": "edu_comparison",
    "m_annual_salary_tm2": "mother_salary_2y_before",
    "f_annual_salary_tm2": "father_salary_2y_before",
    "gr_m_community": "mother_municipality",
    "gr_m_family_status": "family_status",
}

# the source file's ordering
EDU = ["compulsory", "apprenticeship", "Matura", "tertiary"]


def clean_survey():
    df = pd.read_stata(SURVEY_DTA).rename(columns=COLUMNS)
    for c in ["mother_edu", "father_edu"]:
        df[c] = pd.Categorical(df[c].map(dict(enumerate(EDU, 1))), EDU, ordered=True)
    for c in ["edu_comparison", "family_status"]:
        df[c] = df[c].cat.as_unordered()
    df["year"] = df["birth_date"].dt.year
    return df


ESS_COLUMNS = {
    "cntry": "country",
    "gndr": "sex",
    "yrbrn": "birth_year",
    "agea": "age",
    "edulvla": "own_edu",
    "edulvlb": "own_edu_later",
    "pspwght": "weight",
}

# ESS codes 1-5 run from less than lower secondary to tertiary, collapsed to
# three as Dávid Erát does in https://doi.org/10.4054/DemRes.2021.44.7.
ESS_EDU = {1: "Low", 2: "Low", 3: "Middle", 4: "Middle", 5: "High"}
ESS_LEVELS = ["Low", "Middle", "High"]

# unclassifiable answers (0 — unharmonisable, 55 — other) and non-answers
# 
ESS_MISSING = [0, 55, 66, 77, 88, 99]

# Round 5 retires edulvla for edulvlb, and no respondent has both. The
# first digit of edulvlb is the ISCED level, so one `cut` collapses it to the same
# three: 0 to 2 lower secondary or less, 3 and 4 upper secondary, 5 and above
# tertiary. A doctorate at 800 is the highest real code; past it sit "other" and
# the non-answers.
ESS_LATER = [-1, 299, 499, 800]


def clean_ess():
    df = pd.read_csv(ESS_CSV, usecols=list(ESS_COLUMNS)).rename(columns=ESS_COLUMNS)
    early = df.own_edu.where(~df.own_edu.isin(ESS_MISSING)).map(ESS_EDU)
    later = pd.cut(df.pop("own_edu_later"), ESS_LATER, labels=ESS_LEVELS)
    df["own_edu"] = pd.Categorical(
        early.fillna(later.astype(object)), ESS_LEVELS, ordered=True
    )
    df["birth_year"] = df["birth_year"].where(df["birth_year"] < 2200) # 2200 — not a specific value
    df["sex"] = df["sex"].map({1: "man", 2: "woman"})
    return df
