def detect_resource_overload(df):
    resource_load = (
        df.groupby("resource_id")["duration_minutes"]
        .sum()
        .reset_index(name="total_work_minutes")
    )

    threshold = resource_load["total_work_minutes"].quantile(0.90)

    overloaded = resource_load[
        resource_load["total_work_minutes"] >= threshold
    ].copy()

    overloaded["bottleneck_reason"] = "RESOURCE_OVERLOAD"

    return overloaded, threshold
