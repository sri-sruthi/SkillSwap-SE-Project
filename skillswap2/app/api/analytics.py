# skillswap2/app/api/analytics.py
"""
Analytics & Reporting — Module 10
Provides admin-only analytics endpoints for platform insights.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from typing import Optional
from datetime import datetime, timedelta
import csv
import io

from app.database import get_db
from app.models.user import User
from app.models.session import Session as SessionModel
from app.models.token import TokenWallet, TokenTransaction
from app.models.skill import Skill, UserSkill
from app.models.review import Review, MentorRating
from app.utils.security import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def require_admin(current_user: User = Depends(get_current_user)):
    from fastapi import HTTPException
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ─────────────────────────────────────────
# GET /analytics/overview
# ─────────────────────────────────────────
@router.get("/overview")
def get_overview(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    total_users    = db.query(User).filter(User.role != "admin").count()
    total_sessions = db.query(SessionModel).count()
    completed      = db.query(SessionModel).filter(SessionModel.status == "Completed").count()
    total_reviews  = db.query(Review).count()
    avg_rating_row = db.query(func.avg(Review.rating)).scalar()
    avg_rating     = round(float(avg_rating_row), 2) if avg_rating_row else 0.0
    total_tokens   = db.query(func.sum(TokenWallet.balance)).scalar() or 0
    completion_rate = round((completed / total_sessions * 100), 1) if total_sessions else 0

    return {
        "total_users":       total_users,
        "total_sessions":    total_sessions,
        "completed_sessions": completed,
        "completion_rate_pct": completion_rate,
        "total_reviews":     total_reviews,
        "average_rating":    avg_rating,
        "tokens_in_circulation": total_tokens,
    }


# ─────────────────────────────────────────
# GET /analytics/sessions
# ─────────────────────────────────────────
@router.get("/sessions")
def get_session_analytics(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    status_counts = db.query(
        SessionModel.status, func.count(SessionModel.id)
    ).group_by(SessionModel.status).all()

    # Sessions per day (last 14 days)
    since = datetime.utcnow() - timedelta(days=14)
    daily = db.query(
        func.date(SessionModel.created_at).label("day"),
        func.count(SessionModel.id).label("count")
    ).filter(
        SessionModel.created_at >= since
    ).group_by("day").order_by("day").all()

    return {
        "by_status": {row[0]: row[1] for row in status_counts},
        "daily_last_14_days": [
            {"date": str(row.day), "count": row.count} for row in daily
        ],
    }


# ─────────────────────────────────────────
# GET /analytics/skills/popular
# ─────────────────────────────────────────
@router.get("/skills/popular")
def get_popular_skills(
    top_n: int = Query(10, ge=1, le=50),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # Most requested skills (from sessions)
    most_requested = db.query(
        Skill.title,
        func.count(SessionModel.id).label("session_count")
    ).join(SessionModel, SessionModel.skill_id == Skill.id
    ).group_by(Skill.id, Skill.title
    ).order_by(desc("session_count")
    ).limit(top_n).all()

    # Most offered skills (users who teach)
    most_offered = db.query(
        Skill.title,
        func.count(UserSkill.id).label("mentor_count")
    ).join(UserSkill, UserSkill.skill_id == Skill.id
    ).filter(UserSkill.skill_type.in_(["teach", "offer"])
    ).group_by(Skill.id, Skill.title
    ).order_by(desc("mentor_count")
    ).limit(top_n).all()

    return {
        "most_requested": [{"skill": r.title, "sessions": r.session_count} for r in most_requested],
        "most_offered":   [{"skill": r.title, "mentors": r.mentor_count}   for r in most_offered],
    }


# ─────────────────────────────────────────
# GET /analytics/tokens
# ─────────────────────────────────────────
@router.get("/tokens")
def get_token_analytics(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    total_in_wallets = db.query(func.sum(TokenWallet.balance)).scalar() or 0
    avg_balance      = db.query(func.avg(TokenWallet.balance)).scalar() or 0
    max_balance      = db.query(func.max(TokenWallet.balance)).scalar() or 0
    min_balance      = db.query(func.min(TokenWallet.balance)).scalar() or 0

    # Token distribution buckets
    wallets = db.query(TokenWallet.balance).all()
    buckets = {"0-10": 0, "11-30": 0, "31-60": 0, "61+": 0}
    for (bal,) in wallets:
        if bal <= 10:       buckets["0-10"]  += 1
        elif bal <= 30:     buckets["11-30"] += 1
        elif bal <= 60:     buckets["31-60"] += 1
        else:               buckets["61+"]   += 1

    return {
        "total_tokens_in_circulation": total_in_wallets,
        "average_balance":  round(float(avg_balance), 1),
        "max_balance":      max_balance,
        "min_balance":      min_balance,
        "wallet_distribution": buckets,
    }


# ─────────────────────────────────────────
# GET /analytics/ratings
# ─────────────────────────────────────────
@router.get("/ratings")
def get_rating_analytics(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    dist = db.query(
        Review.rating, func.count(Review.id)
    ).group_by(Review.rating).order_by(Review.rating).all()

    top_mentors = db.query(
        User.name,
        MentorRating.average_rating,
        MentorRating.total_reviews
    ).join(MentorRating, MentorRating.mentor_id == User.id
    ).filter(MentorRating.total_reviews >= 1
    ).order_by(desc(MentorRating.average_rating), desc(MentorRating.total_reviews)
    ).limit(5).all()

    return {
        "rating_distribution": {str(int(r)): c for r, c in dist},
        "top_mentors": [
            {"name": m.name, "avg_rating": round(m.average_rating, 2), "reviews": m.total_reviews}
            for m in top_mentors
        ],
    }


# ─────────────────────────────────────────
# GET /analytics/export  — CSV download
# ─────────────────────────────────────────
@router.get("/export")
def export_analytics(
    report_type: str = Query("sessions", description="sessions | users | tokens"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "sessions":
        writer.writerow(["ID", "Learner", "Mentor", "Skill", "Status", "Scheduled Time"])
        rows = db.query(SessionModel).order_by(desc(SessionModel.created_at)).limit(1000).all()
        for s in rows:
            writer.writerow([
                s.id,
                s.learner.name if s.learner else s.learner_id,
                s.mentor.name  if s.mentor  else s.mentor_id,
                s.skill.title  if s.skill   else "",
                s.status,
                s.scheduled_time.isoformat() if s.scheduled_time else "",
            ])

    elif report_type == "users":
        writer.writerow(["ID", "Name", "Email", "Role", "Active", "Token Balance", "Joined"])
        users = db.query(User).filter(User.role != "admin").order_by(desc(User.created_at)).all()
        for u in users:
            wallet = db.query(TokenWallet).filter(TokenWallet.user_id == u.id).first()
            writer.writerow([
                u.id, u.name, u.email, u.role,
                u.is_active,
                wallet.balance if wallet else 0,
                u.created_at.isoformat() if u.created_at else "",
            ])

    elif report_type == "tokens":
        writer.writerow(["Wallet ID", "User Name", "Email", "Balance"])
        wallets = db.query(TokenWallet).join(User).order_by(desc(TokenWallet.balance)).all()
        for w in wallets:
            writer.writerow([w.id, w.user.name, w.user.email, w.balance])

    output.seek(0)
    filename = f"skillswap_{report_type}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )