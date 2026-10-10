from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import timedelta
import re

import numpy as np
import pandas as pd

from database import get_db

from models.database_models import (
    Project,
    ProjectDataset,
    Dataset,
    DatasetVersion,
    AnalysisRun,
    AIInsight,
    Report,
    ProjectRun,
    User,
)

from services.auth_dependency import get_current_user
from services.data_cleaning import load_dataset
from services.analytics import analyze_dataset
from services.anomaly_detection import detect_anomalies
from services.ollama_service import generate_insight
from services.report_generator import generate_report


router = APIRouter()


# =========================================================
# DATASET COLUMN DETECTION
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
    r".*index$",
    r"^index$",
    r".*phone.*",
    r".*postal.*",
    r".*zip.*",
]


def is_identifier_column(column_name: str) -> bool:
    name = str(column_name).strip().lower()

    return any(
        re.match(pattern, name)
        for pattern in IDENTIFIER_PATTERNS
    )


def get_numeric_columns(df: pd.DataFrame):
    result = []

    for column in df.columns:
        if not pd.api.types.is_numeric_dtype(df[column]):
            continue

        series = pd.to_numeric(
            df[column],
            errors="coerce",
        ).dropna()

        if series.empty:
            continue

        if series.nunique() <= 1:
            continue

        result.append(column)

    return result


def score_metric_column(df: pd.DataFrame, column):
    series = pd.to_numeric(
        df[column],
        errors="coerce",
    ).dropna()

    if series.empty:
        return -999

    score = 0
    name = str(column).strip().lower()

    if is_identifier_column(name):
        score -= 100

    completeness = len(series) / max(len(df), 1)
    score += int(completeness * 30)

    unique_count = series.nunique()

    if unique_count >= 2:
        score += 15

    if unique_count >= 5:
        score += 10

    if unique_count >= 10:
        score += 5

    try:
        if float(series.std()) > 0:
            score += 10
    except Exception:
        pass

    if len(series) >= 5:
        values = series.reset_index(drop=True)
        differences = values.diff().dropna()

        if (
            len(differences) > 0
            and differences.eq(1).mean() >= 0.95
        ):
            score -= 80

        if (
            len(differences) > 0
            and differences.eq(-1).mean() >= 0.95
        ):
            score -= 80

    return score


def find_metric_columns(df: pd.DataFrame):
    columns = get_numeric_columns(df)
    results = []

    for column in columns:
        results.append(
            {
                "column": str(column),
                "score": score_metric_column(df, column),
            }
        )

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results


def find_metric_column(df: pd.DataFrame):
    ranked = find_metric_columns(df)

    if not ranked:
        return None

    best = ranked[0]

    if best["score"] < 0:
        return None

    return best["column"]


# =========================================================
# DATE DETECTION
# =========================================================


def find_date_column(df: pd.DataFrame):
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            if df[column].nunique(dropna=True) >= 2:
                return column

    for column in df.columns:
        if pd.api.types.is_numeric_dtype(df[column]):
            continue

        parsed = pd.to_datetime(
            df[column],
            errors="coerce",
        )

        valid_ratio = parsed.notna().mean()

        if (
            valid_ratio >= 0.80
            and parsed.nunique(dropna=True) >= 2
        ):
            return column

    return None


# =========================================================
# AGGREGATION
# =========================================================


def get_metric_aggregation(metric_name, series):
    numeric = pd.to_numeric(
        series,
        errors="coerce",
    ).dropna()

    if numeric.empty:
        return "sum"

    name = str(metric_name).lower()

    if (
        "percent" in name
        or "%" in name
        or "rate" in name
        or "ratio" in name
    ):
        return "mean"

    if (
        numeric.min() >= 0
        and numeric.max() <= 1
        and numeric.nunique() > 2
    ):
        return "mean"

    if (
        numeric.min() >= 0
        and numeric.max() <= 100
        and numeric.nunique() > 2
    ):
        return "mean"

    return "sum"


# =========================================================
# SAFE NUMBER
# =========================================================


def safe_round(value, digits=2):
    if value is None:
        return None

    try:
        value = float(value)

        if not np.isfinite(value):
            return None

        return round(value, digits)

    except Exception:
        return None


# =========================================================
# GROWTH
# =========================================================


def calculate_growth(first_value, last_value):
    try:
        first_value = float(first_value)
        last_value = float(last_value)

        if first_value == 0:
            return None

        return safe_round(
            (
                (last_value - first_value)
                / abs(first_value)
            )
            * 100
        )

    except Exception:
        return None


# =========================================================
# AUTOMATIC FORECAST
# =========================================================


def build_forecast(
    df,
    date_column,
    metric_column,
    aggregation,
):
    if not date_column or not metric_column:
        return {
            "available": False,
            "reason": (
                "A usable date column and numeric metric are required."
            ),
            "date_column": date_column,
            "metric_column": metric_column,
            "historical_points": [],
            "points": [],
        }

    work = df[[date_column, metric_column]].copy()

    work["_date"] = pd.to_datetime(
        work[date_column],
        errors="coerce",
    )

    work["_value"] = pd.to_numeric(
        work[metric_column],
        errors="coerce",
    )

    work = work.dropna(
        subset=["_date", "_value"]
    )

    if len(work) < 8:
        return {
            "available": False,
            "reason": "At least 8 usable time points are required.",
            "date_column": date_column,
            "metric_column": metric_column,
            "historical_points": [],
            "points": [],
        }

    if aggregation == "mean":
        grouped = (
            work.groupby("_date")["_value"]
            .mean()
            .sort_index()
        )
    else:
        grouped = (
            work.groupby("_date")["_value"]
            .sum()
            .sort_index()
        )

    if len(grouped) < 8:
        return {
            "available": False,
            "reason": "Not enough unique time points.",
            "date_column": date_column,
            "metric_column": metric_column,
            "historical_points": [],
            "points": [],
        }

    values = grouped.to_numpy(dtype=float)

    if not np.all(np.isfinite(values)):
        return {
            "available": False,
            "reason": "Invalid numeric values were found.",
            "date_column": date_column,
            "metric_column": metric_column,
            "historical_points": [],
            "points": [],
        }

    x = np.arange(len(values), dtype=float)

    try:
        slope, intercept = np.polyfit(
            x,
            values,
            1,
        )
    except Exception:
        return {
            "available": False,
            "reason": "Forecast calculation failed.",
            "date_column": date_column,
            "metric_column": metric_column,
            "historical_points": [],
            "points": [],
        }

    differences = (
        grouped.index
        .to_series()
        .diff()
        .dropna()
    )

    if differences.empty:
        return {
            "available": False,
            "reason": "Unable to determine time interval.",
            "date_column": date_column,
            "metric_column": metric_column,
            "historical_points": [],
            "points": [],
        }

    seconds = differences.dt.total_seconds().median()

    if not np.isfinite(seconds) or seconds <= 0:
        return {
            "available": False,
            "reason": "Invalid time interval.",
            "date_column": date_column,
            "metric_column": metric_column,
            "historical_points": [],
            "points": [],
        }

    interval = timedelta(seconds=float(seconds))

    historical_points = [
        {
            "date": date.isoformat(),
            "value": safe_round(value),
        }
        for date, value in grouped.tail(30).items()
    ]

    last_date = grouped.index[-1]
    future_points = []

    for offset in range(1, 8):
        future_x = len(values) - 1 + offset

        prediction = intercept + slope * future_x

        if values.min() >= 0:
            prediction = max(0, prediction)

        future_date = last_date + interval * offset

        future_points.append(
            {
                "date": future_date.isoformat(),
                "value": safe_round(prediction),
            }
        )

    return {
        "available": True,
        "date_column": str(date_column),
        "metric_column": str(metric_column),
        "aggregation": aggregation,
        "historical_points": historical_points,
        "points": future_points,
    }


# =========================================================
# CREATE PROJECT
# =========================================================


@router.post("")
def create_project(
    name: str,
    description: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not name.strip():
        raise HTTPException(
            status_code=400,
            detail="Project name is required",
        )

    project = Project(
        user_id=current_user.id,
        name=name.strip(),
        description=description,
        status="active",
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return {
        "message": "Project created successfully",
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "created_at": project.created_at,
        },
    }


# =========================================================
# LIST PROJECTS
# =========================================================


@router.get("")
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
        .all()
    )

    return [
        {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        }
        for project in projects
    ]


# =========================================================
# GET PROJECT
# =========================================================


@router.get("/{project_id}")
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


# =========================================================
# RENAME PROJECT
# =========================================================


@router.patch("/{project_id}")
def rename_project(
    project_id: int,
    name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    new_name = name.strip()

    if not new_name:
        raise HTTPException(
            status_code=400,
            detail="Project name is required",
        )

    project.name = new_name
    db.commit()
    db.refresh(project)

    return {
        "message": "Project renamed successfully",
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        },
    }


# =========================================================
# DELETE PROJECT
# =========================================================


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    db.query(ProjectDataset).filter(
        ProjectDataset.project_id == project_id
    ).delete(synchronize_session=False)

    db.query(ProjectRun).filter(
        ProjectRun.project_id == project_id
    ).delete(synchronize_session=False)

    db.delete(project)
    db.commit()

    return {
        "message": "Project deleted successfully",
        "project_id": project_id,
    }


# =========================================================
# PROJECT OVERVIEW
# =========================================================


@router.get("/{project_id}/overview")
def get_project_overview(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    connection = (
        db.query(ProjectDataset, Dataset)
        .join(
            Dataset,
            Dataset.id == ProjectDataset.dataset_id,
        )
        .filter(
            ProjectDataset.project_id == project_id,
            Dataset.user_id == current_user.id,
        )
        .order_by(
            ProjectDataset.created_at.desc()
        )
        .first()
    )

    if not connection:
        return {
            "project_id": project_id,
            "dataset_available": False,
            "dataset": None,
            "kpis": {
                "primary_metric": None,
                "metric_label": "Primary metric",
                "total_value": None,
                "average_value": None,
                "growth_pct": None,
                "records": 0,
                "columns": 0,
                "missing_values": 0,
                "duplicate_rows": 0,
                "next_forecast": None,
            },
            "metrics": [],
            "column_types": {
                "numeric": [],
                "categorical": [],
                "date": None,
            },
            "forecast": {
                "available": False,
                "reason": "Upload a dataset to start automatic analysis.",
                "historical_points": [],
                "points": [],
            },
        }

    _, dataset = connection

    try:
        df = load_dataset(
            dataset.source_location,
            dataset.source_format,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load dataset: {str(exc)}",
        )

    records = int(len(df))
    columns = int(len(df.columns))
    missing_values = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    ranked_metrics = find_metric_columns(df)
    primary_metric = find_metric_column(df)
    date_column = find_date_column(df)

    numeric_columns = [
        str(column)
        for column in df.columns
        if pd.api.types.is_numeric_dtype(df[column])
    ]

    categorical_columns = [
        str(column)
        for column in df.columns
        if (
            not pd.api.types.is_numeric_dtype(df[column])
            and str(column) != str(date_column)
        )
    ]

    metric_details = []

    for item in ranked_metrics:
        column = item["column"]

        series = pd.to_numeric(
            df[column],
            errors="coerce",
        ).dropna()

        metric_details.append(
            {
                "column": column,
                "score": item["score"],
                "count": int(series.count()),
                "unique": int(series.nunique()),
                "average": safe_round(series.mean()),
                "minimum": safe_round(series.min()),
                "maximum": safe_round(series.max()),
            }
        )

    total_value = None
    average_value = None
    growth_pct = None
    next_forecast = None
    aggregation = None
    metric_label = "Primary metric"

    if primary_metric:
        series = pd.to_numeric(
            df[primary_metric],
            errors="coerce",
        ).dropna()

        if not series.empty:
            aggregation = get_metric_aggregation(
                primary_metric,
                series,
            )

            average_value = safe_round(series.mean())

            if aggregation == "mean":
                total_value = safe_round(series.mean())
                metric_label = f"Average {primary_metric}"
            else:
                total_value = safe_round(series.sum())
                metric_label = f"Total {primary_metric}"

            if date_column:
                growth_df = df[[date_column, primary_metric]].copy()

                growth_df["_date"] = pd.to_datetime(
                    growth_df[date_column],
                    errors="coerce",
                )

                growth_df["_value"] = pd.to_numeric(
                    growth_df[primary_metric],
                    errors="coerce",
                )

                growth_df = growth_df.dropna(
                    subset=["_date", "_value"]
                )

                if len(growth_df) >= 2:
                    if aggregation == "mean":
                        grouped = (
                            growth_df.groupby("_date")["_value"]
                            .mean()
                            .sort_index()
                        )
                    else:
                        grouped = (
                            growth_df.groupby("_date")["_value"]
                            .sum()
                            .sort_index()
                        )

                    if len(grouped) >= 2:
                        growth_pct = calculate_growth(
                            grouped.iloc[0],
                            grouped.iloc[-1],
                        )

    forecast = build_forecast(
        df,
        date_column,
        primary_metric,
        aggregation or "sum",
    )

    if forecast["available"] and forecast["points"]:
        next_forecast = forecast["points"][0]["value"]

    return {
        "project_id": project_id,
        "dataset_available": True,
        "dataset": {
            "id": dataset.id,
            "name": dataset.name,
            "format": dataset.source_format,
            "rows": records,
            "columns": columns,
        },
        "kpis": {
            "primary_metric": primary_metric,
            "metric_label": metric_label,
            "aggregation": aggregation,
            "total_value": total_value,
            "average_value": average_value,
            "growth_pct": growth_pct,
            "records": records,
            "columns": columns,
            "missing_values": missing_values,
            "duplicate_rows": duplicate_rows,
            "next_forecast": next_forecast,
        },
        "metrics": metric_details,
        "column_types": {
            "numeric": numeric_columns,
            "categorical": categorical_columns,
            "date": str(date_column) if date_column else None,
        },
        "forecast": forecast,
    }


# =========================================================
# BACKGROUND AI + PDF PROCESSING
# =========================================================


def finish_auto_analysis(
    run_id: int,
    analysis_run_id: int,
    version_id: int,
    dataset_id: int,
):
    db_generator = get_db()
    db = next(db_generator)

    try:
        run = (
            db.query(ProjectRun)
            .filter(ProjectRun.id == run_id)
            .first()
        )

        analysis_run = (
            db.query(AnalysisRun)
            .filter(AnalysisRun.id == analysis_run_id)
            .first()
        )

        dataset = (
            db.query(Dataset)
            .filter(Dataset.id == dataset_id)
            .first()
        )

        if not run or not dataset:
            return

        result = run.result or {}

        analytics = result.get("analytics", {})
        anomalies = result.get("anomalies", [])
        forecast_result = result.get("forecast", {})

        # -------------------------------------------------
        # OLLAMA
        # -------------------------------------------------

        prompt = f"""
You are the InsightOS business analytics assistant.

Use ONLY the verified information supplied below.

Dataset:
{dataset.name}

Analytics:
{analytics}

Anomalies:
{anomalies}

Forecast:
{forecast_result}

Return exactly:

EXECUTIVE SUMMARY
1. One verified finding.

KEY INSIGHTS
1. One verified insight.
2. One verified trend.
3. One verified unusual behavior.

RECOMMENDATIONS
1. One practical recommendation.
2. One practical recommendation.

STRICT RULES:
- Use only the supplied information.
- Never invent numbers.
- Never invent causes.
- Never invent business explanations.
- Never claim one region, product, or channel is better unless the data proves it.
- Do not mention promotions unless explicitly present.
- Do not mention holidays unless explicitly present.
- Do not mention seasonality unless explicitly demonstrated.
- An anomaly means statistically unusual behavior only.
- If a cause is unknown, say:
  "The available data does not establish the cause."
- Do not describe 7 daily forecast points as a monthly total.
- Keep the response concise.
- Do not use Markdown.
"""

        try:
            ai_text = generate_insight(prompt)
        except Exception:
            ai_text = None

        if not ai_text:
            ai_text = "AI insights could not be generated."

        saved_ai = AIInsight(
            dataset_version_id=version_id,
            analysis_run_id=analysis_run_id,
            insight=ai_text,
            model_name="qwen2.5-coder:7b",
        )

        db.add(saved_ai)

        if analysis_run:
            analysis_run.status = "completed"

        # -------------------------------------------------
        # PDF
        # -------------------------------------------------

        report_forecast = None

        if forecast_result.get("available"):
            report_forecast = {
                "forecast": forecast_result.get(
                    "points", []
                )
            }

        try:
            report_path = generate_report(
                dataset_id=dataset_id,
                dataset_name=dataset.name,
                analytics=analytics,
                anomalies=anomalies,
                forecast_data=report_forecast,
                ai_insight=ai_text,
            )
        except Exception as report_error:
            result["ai"] = {
                "status": "completed",
                "model": "qwen2.5-coder:7b",
                "insight": ai_text,
            }
            result["report"] = {
                "status": "failed",
                "id": None,
            }
            result["report_error"] = str(report_error)

            run.result = result
            run.status = "completed"
            run.completed_at = pd.Timestamp.utcnow()

            db.commit()
            return

        report = Report(
            dataset_version_id=version_id,
            report_type="automatic_analytics",
            file_path=report_path,
        )

        db.add(report)
        db.flush()

        # -------------------------------------------------
        # COMPLETE RESULT
        # -------------------------------------------------

        result["ai"] = {
            "status": "completed",
            "model": "qwen2.5-coder:7b",
            "insight": ai_text,
        }

        result["report"] = {
            "status": "completed",
            "id": int(report.id),
            "view_url": f"/api/reports/{report.id}",
            "download_url": f"/api/reports/{report.id}/download",
        }

        run.result = result
        run.status = "completed"
        run.completed_at = pd.Timestamp.utcnow()

        db.commit()

    except Exception as exc:
        db.rollback()

        run = (
            db.query(ProjectRun)
            .filter(ProjectRun.id == run_id)
            .first()
        )

        analysis_run = (
            db.query(AnalysisRun)
            .filter(AnalysisRun.id == analysis_run_id)
            .first()
        )

        if run:
            result = run.result or {}

            result["ai"] = {
                "status": "failed",
                "insight": None,
            }

            result["report"] = {
                "status": "failed",
                "id": None,
            }

            result["error"] = str(exc)

            run.result = result
            run.status = "failed"

        if analysis_run:
            analysis_run.status = "failed"

        db.commit()

    finally:
        db_generator.close()


# =========================================================
# AUTOMATIC ANALYSIS PIPELINE
# =========================================================


@router.post("/{project_id}/auto-analyze/{dataset_id}")
def auto_analyze_project(
    project_id: int,
    dataset_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # -----------------------------------------------------
    # VERIFY PROJECT
    # -----------------------------------------------------

    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    # -----------------------------------------------------
    # VERIFY DATASET
    # -----------------------------------------------------

    dataset = (
        db.query(Dataset)
        .join(
            ProjectDataset,
            ProjectDataset.dataset_id == Dataset.id,
        )
        .filter(
            ProjectDataset.project_id == project_id,
            Dataset.id == dataset_id,
            Dataset.user_id == current_user.id,
        )
        .first()
    )

    if not dataset:
        raise HTTPException(
            status_code=404,
            detail="Dataset is not connected to this project",
        )

    # -----------------------------------------------------
    # LOAD DATASET
    # -----------------------------------------------------

    try:
        df = load_dataset(
            dataset.source_location,
            dataset.source_format,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to load dataset: {str(exc)}",
        )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="Dataset contains no rows",
        )

    # -----------------------------------------------------
    # FAST ANALYSIS
    # -----------------------------------------------------

    try:
        analytics = analyze_dataset(df)
        anomalies = detect_anomalies(df)

        metric_column = find_metric_column(df)
        date_column = find_date_column(df)

        aggregation = "sum"

        if metric_column:
            aggregation = get_metric_aggregation(
                metric_column,
                df[metric_column],
            )

        forecast_result = build_forecast(
            df,
            date_column,
            metric_column,
            aggregation,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Fast analysis failed: {str(exc)}",
        )

    # -----------------------------------------------------
    # DATASET VERSION
    # -----------------------------------------------------

    version = (
        db.query(DatasetVersion)
        .filter(
            DatasetVersion.dataset_id == dataset_id
        )
        .order_by(
            DatasetVersion.version_number.desc()
        )
        .first()
    )

    if not version:
        raise HTTPException(
            status_code=404,
            detail="Dataset version not found",
        )

    # -----------------------------------------------------
    # ANALYSIS RUN
    # -----------------------------------------------------

    analysis_run = AnalysisRun(
        dataset_version_id=version.id,
        analysis_type="automatic_ai_insight",
        status="processing",
    )

    db.add(analysis_run)
    db.flush()

    # -----------------------------------------------------
    # PARTIAL RESULT
    # -----------------------------------------------------

    partial_result = {
        "dataset": {
            "id": int(dataset.id),
            "name": dataset.name,
            "format": dataset.source_format,
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
        },
        "analytics": analytics,
        "anomalies": anomalies,
        "forecast": forecast_result,
        "ai": {
            "status": "processing",
            "model": "qwen2.5-coder:7b",
            "insight": None,
        },
        "report": {
            "status": "processing",
            "id": None,
        },
    }

    # -----------------------------------------------------
    # PROJECT RUN
    # -----------------------------------------------------

    run = ProjectRun(
        project_id=project_id,
        dataset_id=dataset_id,
        run_type="automatic_analysis",
        status="processing",
        result=partial_result,
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    # -----------------------------------------------------
    # BACKGROUND AI + PDF
    # -----------------------------------------------------

    background_tasks.add_task(
        finish_auto_analysis,
        run.id,
        analysis_run.id,
        version.id,
        dataset_id,
    )

    # -----------------------------------------------------
    # RETURN FAST
    # -----------------------------------------------------

    return {
        "status": "processing",
        "project_id": project_id,
        "dataset_id": dataset_id,
        "run_id": run.id,
        "result": partial_result,
    }


# =========================================================
# GET ANALYSIS RUN STATUS
# =========================================================


@router.get("/{project_id}/runs/{run_id}")
def get_project_run_status(
    project_id: int,
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    run = (
        db.query(ProjectRun)
        .filter(
            ProjectRun.id == run_id,
            ProjectRun.project_id == project_id,
        )
        .first()
    )

    if not run:
        raise HTTPException(
            status_code=404,
            detail="Analysis run not found",
        )

    return {
        "run_id": run.id,
        "status": run.status,
        "result": run.result or {},
        "completed_at": run.completed_at,
    }


# =========================================================
# ADD DATASET TO PROJECT
# =========================================================


@router.post("/{project_id}/datasets/{dataset_id}")
def add_dataset_to_project(
    project_id: int,
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    dataset = (
        db.query(Dataset)
        .filter(
            Dataset.id == dataset_id,
            Dataset.user_id == current_user.id,
        )
        .first()
    )

    if not dataset:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found",
        )

    existing = (
        db.query(ProjectDataset)
        .filter(
            ProjectDataset.project_id == project_id,
            ProjectDataset.dataset_id == dataset_id,
        )
        .first()
    )

    if existing:
        return {
            "message": "Dataset already connected to project",
            "project_id": project_id,
            "dataset_id": dataset_id,
        }

    connection = ProjectDataset(
        project_id=project_id,
        dataset_id=dataset_id,
    )

    db.add(connection)
    db.commit()
    db.refresh(connection)

    return {
        "message": "Dataset added to project",
        "project_id": project_id,
        "dataset_id": dataset_id,
    }


# =========================================================
# GET PROJECT DATASETS
# =========================================================


@router.get("/{project_id}/datasets")
def get_project_datasets(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    datasets = (
        db.query(Dataset)
        .join(
            ProjectDataset,
            ProjectDataset.dataset_id == Dataset.id,
        )
        .filter(
            ProjectDataset.project_id == project_id,
            Dataset.user_id == current_user.id,
        )
        .order_by(
            ProjectDataset.created_at.desc()
        )
        .all()
    )

    return [
        {
            "id": dataset.id,
            "name": dataset.name,
            "source_type": dataset.source_type,
            "source_format": dataset.source_format,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "created_at": dataset.created_at,
        }
        for dataset in datasets
    ]
