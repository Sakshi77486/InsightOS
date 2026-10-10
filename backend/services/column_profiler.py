import re

import pandas as pd


# =========================================================
# IDENTIFIER PATTERNS
# =========================================================

IDENTIFIER_PATTERNS = [
    r"^id$",
    r".*_id$",
    r"^id_.*",
    r".*code$",
    r".*_code$",
    r".*key$",
    r".*_key$",
    r".*uuid$",
    r".*phone.*",
    r".*mobile.*",
    r".*postal.*",
    r".*zip.*",
    r".*pincode.*",
]


# =========================================================
# DATE NAME HINTS
# =========================================================

DATE_NAME_PATTERNS = [
    r"^date$",
    r".*date$",
    r"^date_.*",
    r".*_date$",
    r".*datetime.*",
    r".*timestamp.*",
    r".*time$",
    r".*_time$",
    r".*dob$",
    r".*birth.*",
    r".*joined.*",
    r".*joining.*",
    r".*created.*",
    r".*updated.*",
]


# =========================================================
# IDENTIFIER DETECTION
# =========================================================

def is_identifier_column(column_name: str) -> bool:
    name = str(column_name).strip().lower()

    return any(
        re.match(pattern, name)
        for pattern in IDENTIFIER_PATTERNS
    )


# =========================================================
# DATE NAME DETECTION
# =========================================================

def looks_like_date_name(column_name: str) -> bool:
    name = str(column_name).strip().lower()

    return any(
        re.match(pattern, name)
        for pattern in DATE_NAME_PATTERNS
    )


# =========================================================
# DATETIME DETECTION
# =========================================================

def is_datetime_column(
    series: pd.Series,
    column_name: str
) -> bool:

    # Already a pandas datetime column
    if pd.api.types.is_datetime64_any_dtype(series):
        return True

    # Empty columns are not useful for datetime detection
    non_null = series.dropna()

    if non_null.empty:
        return False

    # If the column name strongly indicates a date,
    # give datetime parsing a chance.
    name_hint = looks_like_date_name(column_name)

    # Try normal pandas conversion
    try:

        converted = pd.to_datetime(
            non_null,
            errors="coerce"
        )

        success_ratio = (
            converted.notna().mean()
        )

    except Exception:
        return False

    # Strongly named date column
    if name_hint and success_ratio >= 0.80:
        return True

    # Unnamed date-like column
    # Require a higher confidence level.
    if success_ratio >= 0.95:

        # Avoid treating very small integer sequences
        # as dates.
        if pd.api.types.is_numeric_dtype(
            non_null
        ):
            return False

        return True

    return False


# =========================================================
# BOOLEAN DETECTION
# =========================================================

def is_boolean_column(
    series: pd.Series
) -> bool:

    if pd.api.types.is_bool_dtype(series):
        return True

    non_null = series.dropna()

    if non_null.empty:
        return False

    if not pd.api.types.is_object_dtype(series):
        return False

    normalized = (
        non_null.astype(str)
        .str.strip()
        .str.lower()
    )

    allowed = {
        "true",
        "false",
        "yes",
        "no",
        "y",
        "n",
    }

    unique_values = set(
        normalized.unique()
    )

    return (
        len(unique_values) > 0
        and unique_values.issubset(allowed)
    )


# =========================================================
# MAIN PROFILER
# =========================================================

def profile_columns(
    df: pd.DataFrame
):

    results = []

    if df is None or df.empty:
        return results

    for column in df.columns:

        series = df[column]

        column_name = str(column)

        name = (
            column_name
            .strip()
            .lower()
        )

        # -------------------------------------------------
        # BASIC COUNTS
        # -------------------------------------------------

        missing_count = int(
            series.isna().sum()
        )

        unique_count = int(
            series.nunique(
                dropna=True
            )
        )

        non_null_count = int(
            series.notna().sum()
        )

        if non_null_count > 0:
            uniqueness_ratio = round(
                unique_count / non_null_count,
                4
            )
        else:
            uniqueness_ratio = 0.0

        # -------------------------------------------------
        # IDENTIFIER CHECK
        # -------------------------------------------------

        identifier = is_identifier_column(
            name
        )

        # -------------------------------------------------
        # DATETIME
        # -------------------------------------------------

        if is_datetime_column(
            series,
            column_name
        ):

            detected_type = "datetime"
            role = "datetime"

        # -------------------------------------------------
        # BOOLEAN
        # -------------------------------------------------

        elif is_boolean_column(series):

            detected_type = "boolean"
            role = "boolean"

        # -------------------------------------------------
        # NUMERIC
        # -------------------------------------------------

        elif pd.api.types.is_numeric_dtype(
            series
        ):

            detected_type = "numeric"

            if identifier:
                role = "identifier"
            else:
                role = "numeric"

        # -------------------------------------------------
        # STRING / OBJECT
        # -------------------------------------------------

        else:

            detected_type = "categorical"

            if identifier:
                role = "identifier"
            else:
                role = "categorical"

        # -------------------------------------------------
        # RESULT
        # -------------------------------------------------

        results.append(
            {
                "column": column_name,
                "detected_type": detected_type,
                "role": role,
                "unique_count": unique_count,
                "missing_count": missing_count,
                "uniqueness_ratio": uniqueness_ratio,
            }
        )

    return results