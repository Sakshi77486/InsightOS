import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def forecast(
    df,
    date_column,
    value_column,
    periods=7
):

    # -----------------------------------------
    # PREPARE DATA
    # -----------------------------------------

    data = df[
        [date_column, value_column]
    ].copy()

    data[date_column] = pd.to_datetime(
        data[date_column],
        errors="coerce"
    )

    data[value_column] = pd.to_numeric(
        data[value_column],
        errors="coerce"
    )

    data = (
        data
        .dropna()
        .sort_values(date_column)
    )

    if len(data) < 3:
        raise ValueError(
            "Not enough data for forecasting."
        )

    # -----------------------------------------
    # HISTORICAL SERIES
    # -----------------------------------------

    series = (
        data
        .set_index(date_column)[value_column]
    )

    latest_value = float(
        series.iloc[-1]
    )

    historical_mean = float(
        series.mean()
    )

    # -----------------------------------------
    # FORECAST MODEL
    # -----------------------------------------

    model = ExponentialSmoothing(
        series,
        trend="add",
        damped_trend=True
    )

    fitted = model.fit()

    forecast_result = fitted.forecast(
        periods
    )

    # -----------------------------------------
    # FORECAST VALUES
    # -----------------------------------------

    forecast_values = [
        float(value)
        for value in forecast_result
    ]

    forecast_average = (
        sum(forecast_values)
        / len(forecast_values)
    )

    forecast_minimum = min(
        forecast_values
    )

    forecast_maximum = max(
        forecast_values
    )

    # -----------------------------------------
    # EXPECTED GROWTH
    # -----------------------------------------

    if latest_value != 0:

        expected_growth = (
            (
                forecast_average
                - latest_value
            )
            / abs(latest_value)
        ) * 100

    else:

        expected_growth = None

    # -----------------------------------------
    # FORECAST DIRECTION
    # -----------------------------------------

    if expected_growth is None:

        direction = "unknown"

    elif expected_growth > 2:

        direction = "increasing"

    elif expected_growth < -2:

        direction = "decreasing"

    else:

        direction = "stable"

    # -----------------------------------------
    # FORECAST OUTPUT
    # -----------------------------------------

    forecast_rows = []

    for index, value in forecast_result.items():

        forecast_rows.append({
            "date": str(index.date()),
            "value": round(
                float(value),
                2
            )
        })

    return {

        "date_column": date_column,

        "value_column": value_column,

        "periods": periods,

        "historical_records": len(series),

        "latest_value": round(
            latest_value,
            2
        ),

        "historical_average": round(
            historical_mean,
            2
        ),

        "forecast_average": round(
            forecast_average,
            2
        ),

        "forecast_minimum": round(
            forecast_minimum,
            2
        ),

        "forecast_maximum": round(
            forecast_maximum,
            2
        ),

        "expected_growth_percentage": (
            round(
                expected_growth,
                2
            )
            if expected_growth is not None
            else None
        ),

        "direction": direction,

        "forecast": forecast_rows
    }