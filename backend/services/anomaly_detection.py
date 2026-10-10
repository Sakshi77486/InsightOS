import pandas as pd
from sklearn.ensemble import IsolationForest

from services.column_profiler import profile_columns


def detect_anomalies(df: pd.DataFrame):

    profiles = profile_columns(df)

    # Exclude identifier columns
    identifier_columns = [
        item["column"]
        for item in profiles
        if item["role"] == "identifier"
    ]

    numeric_df = df.select_dtypes(
        include="number"
    ).copy()

    numeric_df = numeric_df.drop(
        columns=identifier_columns,
        errors="ignore"
    )

    if numeric_df.empty:
        return {
            "message": "No suitable numeric columns available.",
            "total_records": len(df),
            "features_used": [],
            "anomalies_found": 0,
            "anomaly_rate": 0,
            "anomalies": []
        }

    # Fill missing numeric values
    data = numeric_df.fillna(
        numeric_df.median()
    )

    # Isolation Forest
    model = IsolationForest(
        contamination=0.05,
        random_state=42
    )

    predictions = model.fit_predict(data)

    # Decision scores
    scores = model.decision_function(data)

    anomaly_indexes = [
        index
        for index, prediction in enumerate(predictions)
        if prediction == -1
    ]

    anomalies = []

    for index in anomaly_indexes:

        row = df.iloc[index].to_dict()

        # Calculate anomaly details
        details = {}

        for column in numeric_df.columns:

            value = numeric_df.iloc[index][column]

            median = numeric_df[column].median()

            std = numeric_df[column].std()

            if pd.isna(value):
                continue

            if std and std != 0:
                deviation_percentage = (
                    (value - median) / abs(median)
                ) * 100

                z_score = (
                    (value - median) / std
                )

            else:
                deviation_percentage = 0
                z_score = 0

            anomaly_type = (
                "high"
                if value > median
                else "low"
            )

            details[column] = {
                "value": round(float(value), 2),
                "median": round(float(median), 2),
                "deviation_percentage": round(
                    float(deviation_percentage),
                    2
                ),
                "z_score": round(
                    float(z_score),
                    2
                ),
                "type": anomaly_type
            }

        anomalies.append({
            "record": row,
            "anomaly_score": round(
                float(scores[index]),
                4
            ),
            "details": details
        })

    anomaly_count = len(anomalies)

    anomaly_rate = (
        (anomaly_count / len(df)) * 100
        if len(df)
        else 0
    )

    return {
        "total_records": len(df),
        "identifier_columns_excluded": identifier_columns,
        "features_used": list(numeric_df.columns),
        "anomalies_found": anomaly_count,
        "anomaly_rate": round(
            anomaly_rate,
            2
        ),
        "anomalies": anomalies
    }