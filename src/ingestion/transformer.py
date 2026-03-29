def enrich_data(df):
    df = df.copy()

    df["dependencies"] = df["dependencies"].fillna("").apply(
        lambda x: x.split("|") if x else []
    )

    df["duration_minutes"] = (
        df["end_time"] - df["start_time"]
    ).dt.total_seconds() / 60

    return df
