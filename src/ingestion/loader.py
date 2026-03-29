import pandas as pd

def load_raw_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)
