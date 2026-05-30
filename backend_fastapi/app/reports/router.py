"""
Report generation routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
import io

from ..database import get_db
from ..models import User, Prediction, Report
from ..schemas import ReportRequest
from ..auth.dependencies import get_current_user
from .pdf_generator import generate_prediction_report

router = APIRouter(prefix="/api/reports", tags=["Reports"])

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)


@router.post("/generate")
async def generate_report(
    request: ReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate PDF report and return it directly as a downloadable file.
    """
    prediction = db.query(Prediction)\
        .filter(
            Prediction.id == request.prediction_id,
            Prediction.user_id == current_user.id
        )\
        .first()

    if not prediction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")

    report_id = str(uuid.uuid4())
    pdf_path = REPORTS_DIR / f"report_{report_id}.pdf"

    try:
        generate_prediction_report(
            prediction=prediction,
            user=current_user,
            output_path=str(pdf_path)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )

    # Save metadata
    try:
        report = Report(
            user_id=current_user.id,
            prediction_id=prediction.id,
            pdf_path=str(pdf_path),
            file_size=pdf_path.stat().st_size
        )
        db.add(report)
        db.commit()
    except Exception:
        pass  # Don't fail if metadata save fails

    # Stream PDF directly to client
    def iter_file():
        with open(str(pdf_path), "rb") as f:
            yield from f

    return StreamingResponse(
        iter_file(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{request.prediction_id}.pdf"}
    )


@router.get("/download/{report_id}")
async def download_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download generated PDF report"""
    report = db.query(Report)\
        .filter(
            Report.id == report_id,
            Report.user_id == current_user.id
        )\
        .first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    pdf_path = Path(report.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found"
        )
    
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"prediction_report_{report.id}.pdf"
    )


@router.get("/list")
async def list_reports(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of user's generated reports"""
    reports = db.query(Report)\
        .filter(Report.user_id == current_user.id)\
        .order_by(Report.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return reports


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a generated report"""
    report = db.query(Report)\
        .filter(
            Report.id == report_id,
            Report.user_id == current_user.id
        )\
        .first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    # Delete PDF file
    pdf_path = Path(report.pdf_path)
    if pdf_path.exists():
        pdf_path.unlink()
    
    # Delete from database
    db.delete(report)
    db.commit()
    
    return None
