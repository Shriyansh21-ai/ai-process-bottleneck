def detect_duration_bottlenecks(df, percentile=0.90):
    threshold = df["duration_minutes"].quantile(percentile)

    bottlenecks = df[df["duration_minutes"] >= threshold].copy()
    bottlenecks["bottleneck_reason"] = "LONG_DURATION"

    return bottlenecks, threshold
