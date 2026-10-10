from pathlib import Path
import pandas as pd


def load_dataset(file_path: str, file_format: str):
    path = Path(file_path)

    if file_format == "CSV":
        return pd.read_csv(path)
    if file_format in {"XLSX", "XLS"}:
        return pd.read_excel(path)
    if file_format == "JSON":
        return pd.read_json(path)

    raise ValueError("Unsupported dataset format")


def clean_dataset(
    df: pd.DataFrame,
    remove_duplicates=True,
    fill_missing=False
):
    original_rows = len(df)

    if remove_duplicates:
        df = df.drop_duplicates()

    if fill_missing:
        for column in df.columns:
            if pd.api.types.is_numeric_dtype(df[column]):
                df[column] = df[column].fillna(df[column].median())
            else:
                df[column] = df[column].fillna("Unknown")

    return df, {
        "original_rows": original_rows,
        "cleaned_rows": len(df),
        "duplicates_removed": original_rows - len(df),
        "missing_values_remaining": int(df.isna().sum().sum())
    }