import pandas as pd

from pipeline.filepaths import SURVEY_DTA

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
