from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.utils.security import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


class ReportCreateRequest(BaseModel):
    reported_user_id: int
    reason: str


@router.post("/")
def create_user_report(
    payload: ReportCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reported_user_id = int(payload.reported_user_id)
    reason = (payload.reason or "").strip()

    if reported_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot report yourself")
    if len(reason) < 5:
        raise HTTPException(status_code=400, detail="Reason must be at least 5 characters")
    if len(reason) > 2000:
        raise HTTPException(status_code=400, detail="Reason must be 2000 characters or less")

    reported_user = db.query(models.User).filter(models.User.id == reported_user_id).first()
    if not reported_user:
        raise HTTPException(status_code=404, detail="User not found")

    report = models.Report(
        reporter_id=current_user.id,
        reported_user_id=reported_user_id,
        reason=reason,
        status="Open",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "message": "Report submitted successfully",
        "report_id": report.id,
        "status": report.status,
    }
