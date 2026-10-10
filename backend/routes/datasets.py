from pathlib import Path
import uuid
import json

import pandas as pd

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
)

from sqlalchemy.orm import Session

from database import get_db

from models.database_models import (
    Dataset,
    DatasetVersion,
    DatasetColumn,
    AnalysisRun,
    AIInsight,
    Report,
    Project,
    ProjectDataset,
    User,
)

from services.auth_dependency import get_current_user

from services.data_cleaning import (
    load_dataset,
    clean_dataset,
)

from services.analytics import analyze_dataset

from services.visualization import (
    generate_chart_data,
    auto_generate_visualizations,
)

from services.ollama_service import (
    generate_insight,
    generate_chat_response,
)

from services.anomaly_detection import detect_anomalies
from services.column_profiler import profile_columns
from services.forecasting import forecast
from services.report_generator import generate_report


router = APIRouter()


# =========================================================
# UPLOAD DATASET
# =========================================================

@router.post("/upload")
async def upload_dataset(
    project_id: int,
    file: UploadFile = File(...),
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

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File is required",
        )

    allowed_formats = {
        ".csv": "CSV",
        ".xlsx": "XLSX",
        ".xls": "XLS",
        ".json": "JSON",
    }

    extension = Path(file.filename).suffix.lower()

    if extension not in allowed_formats:
        raise HTTPException(
            status_code=400,
            detail="Unsupported dataset format",
        )

    file_format = allowed_formats[extension]

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty",
        )

    upload_dir = Path("data/uploads")
    upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_filename = (
        f"{uuid.uuid4().hex}{extension}"
    )

    file_path = upload_dir / stored_filename
    file_path.write_bytes(content)

    try:

        df = load_dataset(
            str(file_path),
            file_format,
        )

        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="Dataset contains no rows",
            )

        dataset = Dataset(
            user_id=current_user.id,
            name=Path(file.filename).name,
            source_type="upload",
            source_format=file_format,
            source_location=str(file_path),
            row_count=len(df),
            column_count=len(df.columns),
            size_bytes=len(content),
        )

        db.add(dataset)
        db.flush()

        version = DatasetVersion(
            dataset_id=dataset.id,
            version_number=1,
            row_count=len(df),
            column_count=len(df.columns),
            size_bytes=len(content),
        )

        db.add(version)
        db.flush()

        columns = profile_columns(df)

        for column in columns:

            dataset_column = DatasetColumn(
                dataset_version_id=version.id,
                column_name=str(column["column"]),
                data_type=column["detected_type"],
                nullable=column["missing_count"] > 0,
                missing_count=column["missing_count"],
                unique_count=column["unique_count"],
            )

            db.add(dataset_column)

        project_dataset = ProjectDataset(
            project_id=project.id,
            dataset_id=dataset.id,
        )

        db.add(project_dataset)

        db.commit()

        return {
            "message": (
                "Dataset uploaded and "
                "connected successfully"
            ),
            "dataset": {
                "id": dataset.id,
                "name": dataset.name,
                "format": file_format,
                "rows": len(df),
                "columns": len(df.columns),
                "project_id": project.id,
            },
        }

    except HTTPException:
        db.rollback()
        file_path.unlink(missing_ok=True)
        raise

    except Exception as e:
        db.rollback()
        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=400,
            detail=f"Dataset upload failed: {str(e)}",
        )


# =========================================================
# DATASET PREVIEW
# =========================================================

@router.get("/{dataset_id}/preview")
def dataset_preview(
    dataset_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    limit = max(1, min(limit, 100))

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

    try:

        df = load_dataset(
            dataset.source_location,
            dataset.source_format,
        )

        preview = df.head(limit).copy()

        # Convert missing values to real JSON null.
        preview = (
            preview
            .astype(object)
            .where(pd.notna(preview), None)
        )

        raw_rows = preview.to_dict(
            orient="records"
        )

        rows = json.loads(
            json.dumps(
                raw_rows,
                default=str,
                allow_nan=False,
            )
        )

        return {
            "dataset_id": dataset.id,
            "columns": [
                str(column)
                for column in df.columns
            ],
            "rows": rows,
            "limit": limit,
            "total_rows": len(df),
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=(
                "Dataset preview failed: "
                f"{str(e)}"
            ),
        )


# =========================================================
# DATASET PROFILE
# =========================================================

@router.get("/{dataset_id}/profile")
def dataset_profile(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

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

    try:

        df = load_dataset(
            dataset.source_location,
            dataset.source_format,
        )

        return {
            "dataset_id": dataset.id,
            "name": dataset.name,
            "rows": len(df),
            "columns": len(df.columns),
            "size_bytes": dataset.size_bytes,
            "columns_profile": profile_columns(df),
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=f"Profile failed: {str(e)}",
        )


# =========================================================
# CLEAN DATASET
# =========================================================

@router.post("/{dataset_id}/clean")
def clean_dataset_route(
    dataset_id: int,
    remove_duplicates: bool = True,
    fill_missing: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

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

    try:

        df = load_dataset(
            dataset.source_location,
            dataset.source_format,
        )

        _, cleaning_result = clean_dataset(
            df,
            remove_duplicates=remove_duplicates,
            fill_missing=fill_missing,
        )

        return {
            "dataset_id": dataset_id,
            "cleaning": cleaning_result,
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=f"Cleaning failed: {str(e)}",
        )


# =========================================================
# ANALYTICS
# =========================================================

@router.get("/{dataset_id}/analytics")
def dataset_analytics(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

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

    try:

        df = load_dataset(
            dataset.source_location,
            dataset.source_format,
        )

        return analyze_dataset(df)

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=f"Analytics failed: {str(e)}",
        )


# =========================================================
# VISUALIZATION
# =========================================================

@router.get("/{dataset_id}/visualization")
def dataset_visualization(
    dataset_id: int,
    chart_type: str,
    x: str = None,
    y: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

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

    try:

        df = load_dataset(
            dataset.source_location,
            dataset.source_format,
        )

        return generate_chart_data(
            df,
            chart_type,
            x,
            y,
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=f"Visualization failed: {str(e)}",
        )


# =========================================================
# AUTOMATIC VISUALIZATIONS
# =========================================================

@router.get("/{dataset_id}/visualizations/auto")
def automatic_visualizations(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

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

    try:

        df = load_dataset(
            dataset.source_location,
            dataset.source_format,
        )

        result = auto_generate_visualizations(df)

        return {
            "dataset_id": dataset_id,
            **result,
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=(
                "Automatic visualization failed: "
                f"{str(e)}"
            ),
        )


# =========================================================
# AI INSIGHT
# =========================================================

@router.post("/{dataset_id}/ai-insight")
def dataset_ai_insight(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

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

    try:

        df = load_dataset(
            dataset.source_location,
            dataset.source_format,
        )

        analytics = analyze_dataset(df)
        anomalies = detect_anomalies(df)

        forecast_data = None

        datetime_columns = analytics.get(
            "datetime_columns",
            []
        )

        numeric_columns = analytics.get(
            "numeric_columns",
            []
        )

        if datetime_columns and numeric_columns:

            try:

                forecast_data = forecast(
                    df,
                    datetime_columns[0],
                    numeric_columns[0],
                    periods=7,
                )

            except Exception:

                forecast_data = None

        prompt = f"""
You are the AI analysis engine for InsightOS.

Explain ONLY VERIFIED statistical results.

DATASET:
{dataset.name}

VERIFIED ANALYTICS:
{json.dumps(
    analytics,
    indent=2,
    default=str
)}

VERIFIED ANOMALIES:
{json.dumps(
    anomalies,
    indent=2,
    default=str
)}

VERIFIED FORECAST:
{json.dumps(
    forecast_data,
    indent=2,
    default=str
)}

Return exactly:

INSIGHTS

1. Most important verified finding.
2. Most important verified trend.
3. Most important verified unusual behavior.

RECOMMENDATIONS

1. One practical recommendation supported by the data.
2. A second practical recommendation supported by the data.

STRICT RULES:

1. Use only supplied information.
2. Never invent numbers.
3. Never invent causes.
4. Never assume promotions.
5. Never assume marketing campaigns.
6. Never assume holidays.
7. Never assume customer behavior.
8. Never assume operational problems.
9. Never assume seasonality.
10. Never assume market conditions.
11. Never invent the cause of an anomaly.
12. If the cause is unknown, say:
"The available data does not establish the cause."
13. Anomaly means statistically unusual behavior only.
14. Keep the response concise.
15. Do not use Markdown.
16. Do not use #.
17. Do not use **.

Return only the requested sections.
"""

        insight = generate_insight(prompt)

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

        analysis_run = AnalysisRun(
            dataset_version_id=version.id,
            analysis_type="ai_insight",
            result=json.dumps(
                {
                    "analytics": analytics,
                    "anomalies": anomalies,
                    "forecast": forecast_data,
                },
                default=str,
            ),
            status="completed",
        )

        db.add(analysis_run)
        db.flush()

        ai_record = AIInsight(
            dataset_version_id=version.id,
            analysis_run_id=analysis_run.id,
            insight=insight,
            model_name="qwen2.5-coder:7b",
        )

        db.add(ai_record)
        db.commit()

        return {
            "dataset_id": dataset_id,
            "insight": insight,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=f"AI insight failed: {str(e)}",
        )


# =========================================================
# AI CHAT
# =========================================================

@router.post("/{dataset_id}/chat")
def dataset_chat(
    dataset_id: int,
    question: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

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

    try:

        df = load_dataset(
            dataset.source_location,
            dataset.source_format,
        )

        analytics = analyze_dataset(df)
        anomalies = detect_anomalies(df)

        forecast_data = None

        datetime_columns = analytics.get(
            "datetime_columns",
            []
        )

        numeric_columns = analytics.get(
            "numeric_columns",
            []
        )

        if datetime_columns and numeric_columns:

            try:

                forecast_data = forecast(
                    df,
                    datetime_columns[0],
                    numeric_columns[0],
                    periods=7,
                )

            except Exception:

                forecast_data = None

        # =================================================
        # VERIFIED ANOMALY ANSWER
        # =================================================

        question_lower = question.lower().strip()

        if "anomal" in question_lower:

            if isinstance(anomalies, list):

                anomaly_records = anomalies

            elif isinstance(anomalies, dict):

                anomaly_records = anomalies.get(
                    "anomalies",
                    anomalies.get(
                        "records",
                        []
                    )
                )

            else:

                anomaly_records = []

            if not isinstance(
                anomaly_records,
                list
            ):
                anomaly_records = []

            anomaly_count = len(
                anomaly_records
            )

            example_dates = []

            for item in anomaly_records[:5]:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                record = item.get(
                    "record",
                    {}
                )

                if isinstance(
                    record,
                    dict
                ):

                    date_value = record.get(
                        "Date"
                    )

                    if date_value:
                        example_dates.append(
                            str(date_value)
                        )

            answer = (
                f"There are {anomaly_count} "
                "anomalies in the dataset."
            )

            if example_dates:

                answer += (
                    " Example anomaly dates: "
                    + ", ".join(example_dates)
                    + "."
                )

            return {
                "dataset_id": dataset_id,
                "question": question,
                "answer": answer,
            }

        # =================================================
        # OLLAMA FOR OTHER QUESTIONS
        # =================================================

        prompt = f"""
You are InsightOS AI.

Answer ONLY from the verified dataset information.

DATASET:
{dataset.name}

ANALYTICS:
{json.dumps(
    analytics,
    indent=2,
    default=str
)}

ANOMALIES:
{json.dumps(
    anomalies,
    indent=2,
    default=str
)}

FORECAST:
{json.dumps(
    forecast_data,
    indent=2,
    default=str
)}

USER QUESTION:
{question}

STRICT RULES:

1. Never invent numbers.
2. Never invent causes.
3. Use supplied analytics directly.
4. Use supplied forecast directly.
5. Use supplied anomaly information directly.
6. If the answer cannot be determined, say so clearly.
7. Keep the answer concise.
8. Do not use Markdown.

Return only the answer.
"""

        response = generate_chat_response(
            prompt
        )

        return {
            "dataset_id": dataset_id,
            "question": question,
            "answer": response,
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=f"AI chat failed: {str(e)}",
        )


# =========================================================
# LATEST AI INSIGHT
# =========================================================

@router.get("/{dataset_id}/ai-insight/latest")
def latest_ai_insight(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

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

        return {
            "dataset_id": dataset_id,
            "available": False,
            "insight": None,
        }

    insight = (
        db.query(AIInsight)
        .filter(
            AIInsight.dataset_version_id == version.id
        )
        .order_by(
            AIInsight.created_at.desc()
        )
        .first()
    )

    if not insight:

        return {
            "dataset_id": dataset_id,
            "available": False,
            "insight": None,
        }

    return {
        "dataset_id": dataset_id,
        "available": True,
        "model": insight.model_name,
        "insight": insight.insight,
        "created_at": insight.created_at,
    }


# =========================================================
# LATEST REPORT
# =========================================================

@router.get("/{dataset_id}/latest-report")
def latest_report(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

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

    report = (
        db.query(Report)
        .join(
            DatasetVersion,
            Report.dataset_version_id
            == DatasetVersion.id,
        )
        .filter(
            DatasetVersion.dataset_id == dataset_id
        )
        .order_by(
            Report.created_at.desc()
        )
        .first()
    )

    if not report:

        return {
            "dataset_id": dataset_id,
            "available": False,
            "report_id": None,
        }

    return {
        "dataset_id": dataset_id,
        "available": True,
        "report_id": report.id,
        "report_type": report.report_type,
        "created_at": report.created_at,
        "download_url": (
            f"/api/reports/{report.id}/download"
        ),
    }


# =========================================================
# ANOMALIES
# =========================================================

@router.get("/{dataset_id}/anomalies")
def dataset_anomalies(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

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

    try:

        df = load_dataset(
            dataset.source_location,
            dataset.source_format,
        )

        return detect_anomalies(df)

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=(
                "Anomaly detection failed: "
                f"{str(e)}"
            ),
        )


# =========================================================
# COLUMN PROFILING
# =========================================================

@router.get("/{dataset_id}/columns")
def dataset_columns(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

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

    try:

        df = load_dataset(
            dataset.source_location,
            dataset.source_format,
        )

        return profile_columns(df)

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=(
                "Column profiling failed: "
                f"{str(e)}"
            ),
        )


# =========================================================
# FORECAST
# =========================================================

@router.post("/{dataset_id}/forecast")
def dataset_forecast(
    dataset_id: int,
    date_column: str,
    value_column: str,
    periods: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    if periods < 1:
        raise HTTPException(
            status_code=400,
            detail="Periods must be at least 1",
        )

    periods = min(periods, 30)

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

    try:

        df = load_dataset(
            dataset.source_location,
            dataset.source_format,
        )

        return forecast(
            df,
            date_column,
            value_column,
            periods,
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=f"Forecast failed: {str(e)}",
        )


# =========================================================
# CREATE REPORT
# =========================================================

@router.post("/{dataset_id}/report")
def create_report(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

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

    try:

        df = load_dataset(
            dataset.source_location,
            dataset.source_format,
        )

        analytics = analyze_dataset(df)
        anomalies = detect_anomalies(df)

        forecast_data = None

        datetime_columns = analytics.get(
            "datetime_columns",
            []
        )

        numeric_columns = analytics.get(
            "numeric_columns",
            []
        )

        if datetime_columns and numeric_columns:

            try:

                forecast_data = forecast(
                    df,
                    datetime_columns[0],
                    numeric_columns[0],
                    periods=7,
                )

            except Exception:

                forecast_data = None

        ai_insight = None

        try:

            prompt = f"""
You are the AI business analyst inside InsightOS.

Analyze ONLY the verified information below.

DATASET:
{dataset.name}

ANALYTICS:
{json.dumps(
    analytics,
    indent=2,
    default=str
)}

ANOMALIES:
{json.dumps(
    anomalies,
    indent=2,
    default=str
)}

FORECAST:
{json.dumps(
    forecast_data,
    indent=2,
    default=str
)}

Return exactly these sections:

INSIGHTS

1. Most important verified finding.
2. Most important verified trend.
3. Most important verified unusual behavior.

RECOMMENDATIONS

1. First practical recommendation.
2. Second practical recommendation.

Rules:

- Use only supplied data.
- Never invent numbers.
- Never invent business causes.
- Do not assume promotions.
- Do not assume holidays.
- Do not assume customers.
- Do not assume seasonality.
- Do not assume operational problems.
- Do not mention quarters unless supplied.
- Do not call period growth an average growth rate.
- Anomaly means statistically unusual behavior only.
- If the cause is unknown, say:
"The available data does not establish the cause."
- Keep it concise.
- Do not use Markdown.

Return only the requested sections.
"""

            ai_insight = generate_insight(
                prompt
            )

        except Exception:

            ai_insight = None

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

        file_path = generate_report(
            dataset_id=dataset_id,
            dataset_name=dataset.name,
            analytics=analytics,
            anomalies=anomalies,
            forecast_data=forecast_data,
            ai_insight=ai_insight,
        )

        report = Report(
            dataset_version_id=version.id,
            report_type="analytics",
            file_path=file_path,
        )

        db.add(report)
        db.commit()
        db.refresh(report)

        return {
            "message": (
                "Report generated successfully"
            ),
            "report_id": report.id,
            "dataset_id": dataset_id,
            "file_path": report.file_path,
            "view_url": (
                f"/api/reports/{report.id}"
            ),
            "download_url": (
                f"/api/reports/"
                f"{report.id}/download"
            ),
        }

    except HTTPException:
        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=(
                "Report generation failed: "
                f"{str(e)}"
            ),
        )