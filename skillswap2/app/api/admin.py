# skillswap2/app/api/admin.py
"""
Admin Module — Module 9
Provides admin-only endpoints for user management, session oversight,
abuse reports, and audit logging.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List
from datetime import datetime, UTC

from app.database import get_db
from app.models.user import User, UserProfile
from app.models.session import Session as SessionModel
from app.models.token import TokenWallet
from app.models.notification import Notification
from app.models.report import Report
from app.utils.security import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])


# ─────────────────────────────────────────
# HELPER: Enforce admin access
# ─────────────────────────────────────────
def require_admin(current_user: User = Depends(get_current_user)):
    if (current_user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ─────────────────────────────────────────
# GET /admin/stats  — Dashboard overview
# ─────────────────────────────────────────
@router.get("/stats")
def get_dashboard_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    total_users    = db.query(User).count()
    active_users   = db.query(User).filter(User.is_active == True).count()
    blocked_users  = db.query(User).filter(User.is_active == False).count()
    total_sessions = db.query(SessionModel).count()
    pending_sessions   = db.query(SessionModel).filter(SessionModel.status == "Pending").count()
    confirmed_sessions = db.query(SessionModel).filter(SessionModel.status == "Confirmed").count()
    completed_sessions = db.query(SessionModel).filter(SessionModel.status == "Completed").count()
    cancelled_sessions = db.query(SessionModel).filter(SessionModel.status == "Cancelled").count()

    total_tokens_in_wallets = db.query(func.sum(TokenWallet.balance)).scalar() or 0
    total_reports = db.query(Report).count()
    open_reports = db.query(Report).filter(func.lower(Report.status) == "open").count()

    return {
        "users": {
            "total":   total_users,
            "active":  active_users,
            "blocked": blocked_users,
        },
        "sessions": {
            "total":     total_sessions,
            "pending":   pending_sessions,
            "confirmed": confirmed_sessions,
            "completed": completed_sessions,
            "cancelled": cancelled_sessions,
        },
        "tokens": {
            "total_in_circulation": total_tokens_in_wallets,
        },
        "reports": {
            "total": total_reports,
            "open": open_reports,
        }
    }


# ─────────────────────────────────────────
# GET /admin/users  — List all users
# ─────────────────────────────────────────
@router.get("/users")
def get_all_users(
    search: Optional[str] = Query(None, description="Search by name or email"),
    is_active: Optional[bool] = Query(None, description="Filter by active/blocked"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(User).filter(User.role != "admin")

    if search:
        like = f"%{search}%"
        query = query.filter(
            (User.name.ilike(like)) | (User.email.ilike(like))
        )
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    users = query.order_by(desc(User.created_at)).offset(skip).limit(limit).all()

    result = []
    for u in users:
        wallet = db.query(TokenWallet).filter(TokenWallet.user_id == u.id).first()
        result.append({
            "id":         u.id,
            "name":       u.name,
            "email":      u.email,
            "role":       u.role,
            "is_active":  u.is_active,
            "token_balance": wallet.balance if wallet else 0,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })
    return result


# ─────────────────────────────────────────
# GET /admin/users/{user_id}  — User detail
# ─────────────────────────────────────────
@router.get("/users/{user_id}")
def get_user_detail(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    wallet = db.query(TokenWallet).filter(TokenWallet.user_id == user_id).first()

    sessions_as_learner = db.query(SessionModel).filter(
        SessionModel.learner_id == user_id
    ).order_by(desc(SessionModel.created_at)).limit(10).all()

    sessions_as_mentor = db.query(SessionModel).filter(
        SessionModel.mentor_id == user_id
    ).order_by(desc(SessionModel.created_at)).limit(10).all()

    def fmt_session(s):
        return {
            "id": s.id,
            "status": s.status,
            "scheduled_time": s.scheduled_time.isoformat() if s.scheduled_time else None,
        }

    return {
        "id":          user.id,
        "name":        user.name,
        "email":       user.email,
        "role":        user.role,
        "is_active":   user.is_active,
        "created_at":  user.created_at.isoformat() if user.created_at else None,
        "token_balance": wallet.balance if wallet else 0,
        "sessions_as_learner": [fmt_session(s) for s in sessions_as_learner],
        "sessions_as_mentor":  [fmt_session(s) for s in sessions_as_mentor],
    }


# ─────────────────────────────────────────
# PATCH /admin/users/{user_id}/block
# ─────────────────────────────────────────
@router.patch("/users/{user_id}/block")
def block_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot block another admin")
    if not user.is_active:
        return {"message": "User is already blocked", "user_id": user_id}

    user.is_active = False
    db.commit()

    # Notify the blocked user
    notif = Notification(
        recipient_id=user_id,
        actor_id=admin.id,
        event_type="account_blocked",
        message="Your account has been suspended by an administrator."
    )
    db.add(notif)
    db.commit()

    return {"message": f"User {user.name} has been blocked", "user_id": user_id}


# ─────────────────────────────────────────
# PATCH /admin/users/{user_id}/unblock
# ─────────────────────────────────────────
@router.patch("/users/{user_id}/unblock")
def unblock_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_active:
        return {"message": "User is already active", "user_id": user_id}

    user.is_active = True
    db.commit()

    notif = Notification(
        recipient_id=user_id,
        actor_id=admin.id,
        event_type="account_unblocked",
        message="Your account has been reinstated by an administrator."
    )
    db.add(notif)
    db.commit()

    return {"message": f"User {user.name} has been unblocked", "user_id": user_id}


# ─────────────────────────────────────────
# GET /admin/sessions  — All sessions
# ─────────────────────────────────────────
@router.get("/sessions")
def get_all_sessions(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(SessionModel)
    if status:
        query = query.filter(SessionModel.status == status)

    sessions = query.order_by(desc(SessionModel.created_at)).offset(skip).limit(limit).all()

    return [
        {
            "id":             s.id,
            "status":         s.status,
            "learner_id":     s.learner_id,
            "learner_name":   s.learner.name if s.learner else None,
            "mentor_id":      s.mentor_id,
            "mentor_name":    s.mentor.name if s.mentor else None,
            "skill_name":     s.skill.title if s.skill else None,
            "scheduled_time": s.scheduled_time.isoformat() if s.scheduled_time else None,
            "created_at":     s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]


# ─────────────────────────────────────────
# GET /admin/reports  — User reports queue
# ─────────────────────────────────────────
@router.get("/reports")
def get_reports(
    status: Optional[str] = Query(None, description="open | resolved | dismissed | blocked"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Report)

    if status:
        normalized = status.strip().lower()
        allowed_statuses = {"open", "resolved", "dismissed", "blocked"}
        if normalized not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="status must be one of: open, resolved, dismissed, blocked",
            )
        query = query.filter(func.lower(Report.status) == normalized)

    reports = query.order_by(desc(Report.created_at)).offset(skip).limit(limit).all()
    return [
        {
            "id": r.id,
            "reporter_id": r.reporter_id,
            "reporter_name": r.reporter.name if r.reporter else None,
            "reporter_email": r.reporter.email if r.reporter else None,
            "reported_user_id": r.reported_user_id,
            "reported_user_name": r.reported_user.name if r.reported_user else None,
            "reported_user_email": r.reported_user.email if r.reported_user else None,
            "reason": r.reason,
            "status": r.status,
            "resolution_note": r.resolution_note,
            "resolved_by": r.resolved_by,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        }
        for r in reports
    ]


# ─────────────────────────────────────────
# PATCH /admin/reports/{report_id}/resolve
# ─────────────────────────────────────────
@router.patch("/reports/{report_id}/resolve")
def resolve_report(
    report_id: int,
    resolution_note: Optional[str] = Query(None),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if (report.status or "").strip().lower() != "open":
        return {
            "message": f"Report already actioned as {report.status}",
            "report_id": report.id,
            "status": report.status,
        }

    report.status = "Resolved"
    report.resolved_by = admin.id
    report.resolved_at = datetime.now(UTC)
    if resolution_note is not None:
        note = resolution_note.strip()
        report.resolution_note = note if note else None
    db.commit()

    return {"message": "Report resolved", "report_id": report.id, "status": report.status}


# ─────────────────────────────────────────
# PATCH /admin/reports/{report_id}/dismiss
# ─────────────────────────────────────────
@router.patch("/reports/{report_id}/dismiss")
def dismiss_report(
    report_id: int,
    resolution_note: Optional[str] = Query(None),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if (report.status or "").strip().lower() != "open":
        return {
            "message": f"Report already actioned as {report.status}",
            "report_id": report.id,
            "status": report.status,
        }

    report.status = "Dismissed"
    report.resolved_by = admin.id
    report.resolved_at = datetime.now(UTC)
    if resolution_note is not None:
        note = resolution_note.strip()
        report.resolution_note = note if note else None
    db.commit()

    return {"message": "Report dismissed", "report_id": report.id, "status": report.status}


# ─────────────────────────────────────────
# PATCH /admin/reports/{report_id}/block-reported-user
# ─────────────────────────────────────────
@router.patch("/reports/{report_id}/block-reported-user")
def block_reported_user(
    report_id: int,
    resolution_note: Optional[str] = Query(None),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if (report.status or "").strip().lower() != "open":
        return {
            "message": f"Report already actioned as {report.status}",
            "report_id": report.id,
            "status": report.status,
        }

    reported_user = db.query(User).filter(User.id == report.reported_user_id).first()
    if not reported_user:
        raise HTTPException(status_code=404, detail="Reported user not found")
    if (reported_user.role or "").lower() == "admin":
        raise HTTPException(status_code=400, detail="Cannot block an admin account")

    was_already_blocked = not bool(reported_user.is_active)
    if not was_already_blocked:
        reported_user.is_active = False
        db.add(
            Notification(
                recipient_id=reported_user.id,
                actor_id=admin.id,
                event_type="account_blocked",
                message="Your account has been suspended by an administrator.",
            )
        )

    report.status = "Blocked"
    report.resolved_by = admin.id
    report.resolved_at = datetime.now(UTC)
    note_parts = []
    note = (resolution_note or "").strip()
    if note:
        note_parts.append(note)
    note_parts.append(
        "User was already blocked before this report action."
        if was_already_blocked
        else "User blocked by admin from report action."
    )
    report.resolution_note = " ".join(note_parts)
    db.commit()

    return {
        "message": "Reported user blocked and report actioned",
        "report_id": report.id,
        "reported_user_id": reported_user.id,
        "status": report.status,
    }
