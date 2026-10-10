from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from database import get_db
from models.database_models import Report

router = APIRouter()


@router.get("")
def list_reports(db: Session = Depends(get_db)):
    reports = (
        db.query(Report)
        .order_by(Report.created_at.desc())
        .all()
    )

    return [
        {
            "id": report.id,
            "dataset_version_id": report.dataset_version_id,
            "report_type": report.report_type,
            "file_path": report.file_path,
            "created_at": report.created_at,
        }
        for report in reports
    ]


@router.get("/{report_id}")
def view_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    report = (
        db.query(Report)
        .filter(Report.id == report_id)
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    file_path = Path(report.file_path)

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Report file not found"
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline"
        }
    )


@router.get("/{report_id}/download")
def download_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    report = (
        db.query(Report)
        .filter(Report.id == report_id)
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    file_path = Path(report.file_path)

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Report file not found"
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=file_path.name
    )