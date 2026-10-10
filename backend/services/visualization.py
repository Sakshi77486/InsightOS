import pandas as pd

from services.column_profiler import profile_columns


# =========================================================
# JSON SAFE CONVERSION
# =========================================================

def _json_safe(value):
    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


def _records_to_xy(dataframe: pd.DataFrame, x=None, y=None):
    result = {
        "x": [],
        "y": [],
    }

    if dataframe.empty:
        return result

    if x and x in dataframe.columns:
        result["x"] = [
            _json_safe(value)
            for value in dataframe[x].tolist()
        ]

    if y and y in dataframe.columns:
        result["y"] = [
            _json_safe(value)
            for value in dataframe[y].tolist()
        ]

    return result


# =========================================================
# EXISTING CHART GENERATOR
# =========================================================

def generate_chart_data(
    df: pd.DataFrame,
    chart_type: str,
    x: str = None,
    y: str = None
):
    if df is None or df.empty:
        raise ValueError("Dataset is empty")

    if chart_type == "bar":

        if not x or not y:
            raise ValueError("Bar chart requires x and y columns")

        if x not in df.columns or y not in df.columns:
            raise ValueError("Invalid bar chart columns")

        data = (
            df.groupby(x, dropna=False)[y]
            .sum()
            .reset_index()
            .sort_values(y, ascending=False)
        )

        xy = _records_to_xy(data, x, y)

    elif chart_type == "line":

        if not x or not y:
            raise ValueError("Line chart requires x and y columns")

        if x not in df.columns or y not in df.columns:
            raise ValueError("Invalid line chart columns")

        data = df[[x, y]].copy()

        try:
            parsed_dates = pd.to_datetime(
                data[x],
                errors="coerce"
            )

            if parsed_dates.notna().any():
                data["_sort_date"] = parsed_dates
                data = (
                    data
                    .sort_values("_sort_date")
                    .drop(columns="_sort_date")
                )
            else:
                data = data.sort_values(x)

        except Exception:
            data = data.sort_values(x)

        xy = _records_to_xy(data, x, y)

    elif chart_type == "scatter":

        if not x or not y:
            raise ValueError("Scatter chart requires x and y columns")

        if x not in df.columns or y not in df.columns:
            raise ValueError("Invalid scatter chart columns")

        data = df[[x, y]].dropna()

        xy = _records_to_xy(data, x, y)

    elif chart_type == "histogram":

        if not x:
            raise ValueError("Histogram requires x column")

        if x not in df.columns:
            raise ValueError("Invalid histogram column")

        data = df[[x]].dropna()

        xy = {
            "x": [
                _json_safe(value)
                for value in data[x].tolist()
            ],
            "y": [],
        }

    elif chart_type == "heatmap":

        numeric = df.select_dtypes(include="number")

        if numeric.shape[1] < 2:
            return {
                "type": "heatmap",
                "columns": list(numeric.columns),
                "values": [],
                "available": False,
                "message": "At least two numeric columns are required."
            }

        correlation = numeric.corr().round(3)

        return {
            "type": "heatmap",
            "columns": list(correlation.columns),
            "values": correlation.values.tolist(),
            "available": True,
        }

    else:
        raise ValueError("Unsupported chart type")

    return {
        "type": chart_type,
        "x": xy["x"],
        "y": xy["y"],
    }


# =========================================================
# AUTOMATIC VISUALIZATION ENGINE
# =========================================================

def auto_generate_visualizations(df: pd.DataFrame):
    """
    Automatically selects useful visualizations according
    to the detected column types.
    """

    if df is None or df.empty:
        return {
            "visualizations": []
        }

    profiles = profile_columns(df)

    datetime_columns = []
    numeric_columns = []
    categorical_columns = []

    for profile in profiles:

        column = profile["column"]
        detected_type = profile["detected_type"]
        role = profile["role"]

        # Identifier columns should not drive business charts.
        if role == "identifier":
            continue

        if detected_type == "datetime":
            datetime_columns.append(column)

        elif detected_type == "numeric":
            numeric_columns.append(column)

        elif detected_type == "categorical":
            categorical_columns.append(column)

    visualizations = []

    # =====================================================
    # 1. DATETIME + NUMERIC
    # =====================================================

    if datetime_columns and numeric_columns:

        date_column = datetime_columns[0]
        value_column = numeric_columns[0]

        chart = generate_chart_data(
            df,
            "line",
            date_column,
            value_column
        )

        visualizations.append({
            "id": "trend",
            "type": "line",
            "title": f"{value_column} over time",
            "x_column": date_column,
            "y_column": value_column,
            "data": chart,
        })

    # =====================================================
    # 2. NUMERIC DISTRIBUTION
    # =====================================================

    if numeric_columns:

        value_column = numeric_columns[0]

        chart = generate_chart_data(
            df,
            "histogram",
            value_column
        )

        visualizations.append({
            "id": "distribution",
            "type": "histogram",
            "title": f"{value_column} distribution",
            "x_column": value_column,
            "y_column": None,
            "data": chart,
        })

    # =====================================================
    # 3. CATEGORICAL + NUMERIC
    # =====================================================

    if categorical_columns and numeric_columns:

        category_column = categorical_columns[0]
        value_column = numeric_columns[0]

        chart = generate_chart_data(
            df,
            "bar",
            category_column,
            value_column
        )

        # Keep chart readable for high-cardinality categories.
        if len(chart["x"]) > 20:
            chart["x"] = chart["x"][:20]
            chart["y"] = chart["y"][:20]

        visualizations.append({
            "id": "category_comparison",
            "type": "bar",
            "title": f"{value_column} by {category_column}",
            "x_column": category_column,
            "y_column": value_column,
            "data": chart,
        })

    # =====================================================
    # 4. CATEGORICAL DISTRIBUTION
    # =====================================================

    elif categorical_columns:

        category_column = categorical_columns[0]

        distribution = (
            df[category_column]
            .fillna("Missing")
            .value_counts()
            .reset_index()
        )

        distribution.columns = [
            category_column,
            "count"
        ]

        distribution = distribution.head(20)

        visualizations.append({
            "id": "category_distribution",
            "type": "bar",
            "title": f"{category_column} distribution",
            "x_column": category_column,
            "y_column": "count",
            "data": {
                "type": "bar",
                "x": [
                    _json_safe(value)
                    for value in distribution[category_column]
                ],
                "y": [
                    _json_safe(value)
                    for value in distribution["count"]
                ],
            },
        })

    # =====================================================
    # 5. NUMERIC + NUMERIC
    # =====================================================

    if len(numeric_columns) >= 2:

        x_column = numeric_columns[0]
        y_column = numeric_columns[1]

        chart = generate_chart_data(
            df,
            "scatter",
            x_column,
            y_column
        )

        visualizations.append({
            "id": "relationship",
            "type": "scatter",
            "title": f"{x_column} vs {y_column}",
            "x_column": x_column,
            "y_column": y_column,
            "data": chart,
        })

    # =====================================================
    # 6. CORRELATION HEATMAP
    # =====================================================

    if len(numeric_columns) >= 2:

        chart = generate_chart_data(
            df,
            "heatmap"
        )

        if chart.get("available", True):

            visualizations.append({
                "id": "correlation",
                "type": "heatmap",
                "title": "Numeric correlation",
                "x_column": None,
                "y_column": None,
                "data": chart,
            })

    return {
        "visualizations": visualizations,
        "detected_columns": {
            "datetime": datetime_columns,
            "numeric": numeric_columns,
            "categorical": categorical_columns,
        }
    }