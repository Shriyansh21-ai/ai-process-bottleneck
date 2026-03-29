def prepare_features(df):
    df = df.copy()

    df["rework_flag"] = (df["status"] == "rework").astype(int)
    df["dependency_count"] = df["dependencies"].apply(len)

    features = df[[
        "duration_minutes",
        "waiting_minutes",
        "rework_flag",
        "dependency_count"
    ]]

    target = (df["risk_level"] == "HIGH").astype(int)

    return features, target
