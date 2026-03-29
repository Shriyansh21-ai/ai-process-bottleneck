import pandas as pd

def detect_waiting_time(df):
    df = df.sort_values(["case_id", "start_time"]).copy()
    df["previous_end"] = df.groupby("case_id")["end_time"].shift(1)

    df["waiting_minutes"] = (
        df["start_time"] - df["previous_end"]
    ).dt.total_seconds() / 60

    df["waiting_minutes"] = df["waiting_minutes"].fillna(0)

    threshold = df["waiting_minutes"].quantile(0.90)

    bottlenecks = df[df["waiting_minutes"] >= threshold].copy()
    bottlenecks["bottleneck_reason"] = "LONG_WAITING"

    return bottlenecks, threshold
