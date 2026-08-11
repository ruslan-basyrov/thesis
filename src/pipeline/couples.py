def make_couples(df):
    known = df[["mother_edu", "father_edu"]].notna().all(axis=1)
    hypo = (df["mother_edu"] > df["father_edu"]).where(known).astype("boolean")
    return df.assign(hypo=hypo)
