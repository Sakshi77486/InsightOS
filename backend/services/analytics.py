import pandas as pd


def analyze_dataset(df: pd.DataFrame):
    df = df.copy()

    datetime_columns = []

    # =========================================================
    # AUTOMATIC DATE DETECTION
    # =========================================================

    for column in df.columns:

        if pd.api.types.is_datetime64_any_dtype(df[column]):
            datetime_columns.append(column)
            continue

        if (
            pd.api.types.is_object_dtype(df[column])
            or pd.api.types.is_string_dtype(df[column])
        ):

            converted = pd.to_datetime(
                df[column],
                errors="coerce",
                format="mixed"
            )

            valid_ratio = converted.notna().mean()

            if valid_ratio >= 0.80:
                df[column] = converted
                datetime_columns.append(column)

    # =========================================================
    # SORTED DATA FOR TIME-SERIES ANALYSIS
    # =========================================================

    if datetime_columns:

        date_column = datetime_columns[0]

        trend_df = df.copy()

        trend_df[date_column] = pd.to_datetime(
            trend_df[date_column],
            errors="coerce"
        )

        trend_df = (
            trend_df
            .dropna(subset=[date_column])
            .sort_values(date_column)
        )

    else:
        trend_df = df.copy()

    # =========================================================
    # COLUMN CLASSIFICATION
    # =========================================================

    numeric = df.select_dtypes(
        include="number"
    )

    categorical = df.select_dtypes(
        include=["object", "category", "bool"]
    )

    categorical_columns = [
        column
        for column in categorical.columns
        if column not in datetime_columns
    ]

    # =========================================================
    # BASE RESULT
    # =========================================================

    result = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),

        "numeric_columns": [
            str(column)
            for column in numeric.columns
        ],

        "categorical_columns": [
            str(column)
            for column in categorical_columns
        ],

        "datetime_columns": [
            str(column)
            for column in datetime_columns
        ],

        "missing_values": int(
            df.isna().sum().sum()
        ),

        "duplicate_rows": int(
            df.duplicated().sum()
        ),

        "statistics": {},
        "categorical_summary": {},
        "correlations": {},
        "trend": {}
    }

    # =========================================================
    # NUMERIC STATISTICS
    # =========================================================

    for column in numeric.columns:

        series = numeric[column].dropna()

        if series.empty:
            continue

        mean_value = float(series.mean())
        std_value = float(series.std())

        coefficient_of_variation = (
            (std_value / abs(mean_value)) * 100
            if mean_value != 0
            else None
        )

        result["statistics"][str(column)] = {

            "count": int(series.count()),

            "sum": round(
                float(series.sum()),
                2
            ),

            "mean": round(
                mean_value,
                2
            ),

            "median": round(
                float(series.median()),
                2
            ),

            "minimum": round(
                float(series.min()),
                2
            ),

            "maximum": round(
                float(series.max()),
                2
            ),

            "std": round(
                std_value,
                2
            ),

            "standard_deviation": round(
                std_value,
                2
            ),

            "variance": round(
                float(series.var()),
                2
            ),

            "range": round(
                float(
                    series.max()
                    - series.min()
                ),
                2
            ),

            "coefficient_of_variation": (
                round(
                    coefficient_of_variation,
                    2
                )
                if coefficient_of_variation is not None
                else None
            )
        }

    # =========================================================
    # CATEGORICAL SUMMARY
    # =========================================================

    for column in categorical_columns:

        values = (
            df[column]
            .dropna()
            .value_counts()
            .head(10)
        )

        result["categorical_summary"][str(column)] = {

            "unique_values": int(
                df[column].nunique(
                    dropna=True
                )
            ),

            "top_values": {
                str(key): int(value)
                for key, value in values.items()
            }
        }

    # =========================================================
    # CORRELATIONS
    # =========================================================

    if len(numeric.columns) > 1:

        correlation_df = (
            numeric
            .corr()
            .round(3)
        )

        result["correlations"] = (
            correlation_df
            .to_dict()
        )

    # =========================================================
    # TREND ANALYSIS
    # =========================================================

    result["trend"] = detect_trends(
        trend_df,
        datetime_columns
    )

    return result


def detect_trends(
    df: pd.DataFrame,
    datetime_columns
):

    numeric = df.select_dtypes(
        include="number"
    )

    trends = {}

    # =========================================================
    # PROCESS EVERY NUMERIC COLUMN
    # =========================================================

    for column in numeric.columns:

        series = pd.to_numeric(
            df[column],
            errors="coerce"
        )

        series = series.dropna()

        if len(series) < 3:
            continue

        # =====================================================
        # BASIC VALUES
        # =====================================================

        first_value = float(
            series.iloc[0]
        )

        last_value = float(
            series.iloc[-1]
        )

        minimum = float(
            series.min()
        )

        maximum = float(
            series.max()
        )

        mean = float(
            series.mean()
        )

        median = float(
            series.median()
        )

        std = float(
            series.std()
        )

        # =====================================================
        # OVERALL GROWTH
        # =====================================================

        if first_value != 0:

            growth_percentage = (
                (
                    last_value
                    - first_value
                )
                / abs(first_value)
            ) * 100

        else:

            growth_percentage = None

        # =====================================================
        # DIRECTION
        # =====================================================

        if growth_percentage is None:

            direction = "unknown"

        elif growth_percentage > 5:

            direction = "increasing"

        elif growth_percentage < -5:

            direction = "decreasing"

        else:

            direction = "stable"

        # =====================================================
        # PERIOD GROWTH
        # =====================================================

        period_size = max(
            1,
            min(
                30,
                len(series) // 4
            )
        )

        first_period = series.iloc[
            :period_size
        ]

        last_period = series.iloc[
            -period_size:
        ]

        first_period_average = float(
            first_period.mean()
        )

        last_period_average = float(
            last_period.mean()
        )

        if first_period_average != 0:

            period_growth = (
                (
                    last_period_average
                    - first_period_average
                )
                / abs(first_period_average)
            ) * 100

        else:

            period_growth = None

        # =====================================================
        # MOVING AVERAGE
        # =====================================================

        window = min(
            7,
            len(series)
        )

        moving_average = (
            series
            .rolling(
                window=window
            )
            .mean()
            .dropna()
        )

        moving_average_current = (
            float(
                moving_average.iloc[-1]
            )
            if not moving_average.empty
            else None
        )

        moving_average_previous = (
            float(
                moving_average.iloc[-2]
            )
            if len(moving_average) >= 2
            else None
        )

        # =====================================================
        # MOVING AVERAGE GROWTH
        # =====================================================

        if (
            moving_average_previous is not None
            and moving_average_previous != 0
        ):

            moving_average_growth = (
                (
                    moving_average_current
                    - moving_average_previous
                )
                / abs(moving_average_previous)
            ) * 100

        else:

            moving_average_growth = None

        # =====================================================
        # VOLATILITY
        # =====================================================

        if mean != 0:

            coefficient_of_variation = (
                std
                / abs(mean)
            ) * 100

        else:

            coefficient_of_variation = None

        # =====================================================
        # BEST / WORST RECORD
        # =====================================================

        max_index = series.idxmax()
        min_index = series.idxmin()

        best_record = {
            "value": round(
                maximum,
                2
            )
        }

        worst_record = {
            "value": round(
                minimum,
                2
            )
        }

        if (
            datetime_columns
            and datetime_columns[0] in df.columns
        ):

            date_column = datetime_columns[0]

            best_record["date"] = (
                str(
                    df.loc[
                        max_index,
                        date_column
                    ]
                )
            )

            worst_record["date"] = (
                str(
                    df.loc[
                        min_index,
                        date_column
                    ]
                )
            )

        # =====================================================
        # TREND RESULT
        # =====================================================

        trends[str(column)] = {

            "first_value": round(
                first_value,
                2
            ),

            "last_value": round(
                last_value,
                2
            ),

            "growth_percentage": (
                round(
                    growth_percentage,
                    2
                )
                if growth_percentage is not None
                else None
            ),

            "direction": direction,

            "first_period_average": round(
                first_period_average,
                2
            ),

            "last_period_average": round(
                last_period_average,
                2
            ),

            "period_growth_percentage": (
                round(
                    period_growth,
                    2
                )
                if period_growth is not None
                else None
            ),

            "moving_average_window": window,

            "moving_average_current": (
                round(
                    moving_average_current,
                    2
                )
                if moving_average_current is not None
                else None
            ),

            "moving_average_previous": (
                round(
                    moving_average_previous,
                    2
                )
                if moving_average_previous is not None
                else None
            ),

            "moving_average_growth_percentage": (
                round(
                    moving_average_growth,
                    2
                )
                if moving_average_growth is not None
                else None
            ),

            "mean": round(
                mean,
                2
            ),

            "median": round(
                median,
                2
            ),

            "standard_deviation": round(
                std,
                2
            ),

            "coefficient_of_variation": (
                round(
                    coefficient_of_variation,
                    2
                )
                if coefficient_of_variation is not None
                else None
            ),

            "minimum": round(
                minimum,
                2
            ),

            "maximum": round(
                maximum,
                2
            ),

            "range": round(
                maximum - minimum,
                2
            ),

            "best_record": best_record,

            "worst_record": worst_record
        }

    return trends