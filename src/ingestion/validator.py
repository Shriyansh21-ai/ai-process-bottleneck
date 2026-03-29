import yaml
import pandas as pd

def validate_schema(df: pd.DataFrame, schema_path: str):
    with open(schema_path) as f:
        schema = yaml.safe_load(f)

    missing_cols = set(schema["required_columns"]) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing columns: {missing_cols}")

    if not df["resource_type"].isin(schema["allowed_resource_types"]).all():
        raise ValueError("Invalid resource type detected")

    if not df["status"].isin(schema["allowed_status"]).all():
        raise ValueError("Invalid status detected")


def validate_timestamps(df: pd.DataFrame):
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])

    if (df["end_time"] < df["start_time"]).any():
        raise ValueError("End time earlier than start time detected")

    return df
