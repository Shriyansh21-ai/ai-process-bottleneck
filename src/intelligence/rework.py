def detect_rework_loops(df):
    rework_tasks = df[df["status"] == "rework"].copy()

    rework_summary = (
        rework_tasks
        .groupby("task_name")
        .size()
        .reset_index(name="rework_count")
    )

    rework_summary["bottleneck_reason"] = "REWORK_LOOP"

    return rework_summary
