def compute_risk_score(df):
    df = df.copy()

    df["risk_score"] = (
        0.4 * df["duration_minutes"].rank(pct=True) +
        0.3 * df.get("waiting_minutes", 0).rank(pct=True) +
        0.3 * (df["status"] == "rework").astype(int)
    )

    df["risk_level"] = df["risk_score"].apply(
        lambda x: "HIGH" if x > 0.75 else
                  "MEDIUM" if x > 0.4 else
                  "LOW"
    )

    return df
