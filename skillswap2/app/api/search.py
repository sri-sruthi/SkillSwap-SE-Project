from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app import models
from app.schemas import SkillSearchResult, MentorSearchResult

router = APIRouter(prefix="/search", tags=["Search"])
TEACH_SKILL_TYPES = ("teach", "offer")
PROFICIENCY_LEVELS = ("Beginner", "Intermediate", "Advanced", "Expert")
PROFICIENCY_LEVELS_BY_KEY = {level.lower(): level for level in PROFICIENCY_LEVELS}


def _normalize_requested_level(level: Optional[str]) -> Optional[str]:
    if level is None:
        return None
    normalized = str(level).strip().lower()
    if not normalized:
        return None
    if normalized not in PROFICIENCY_LEVELS_BY_KEY:
        raise HTTPException(
            status_code=400,
            detail="Invalid level. Use one of: Beginner, Intermediate, Advanced, Expert",
        )
    return PROFICIENCY_LEVELS_BY_KEY[normalized]


def _normalized_proficiency_expr():
    # Legacy rows may have NULL/blank level; treat them as beginner.
    return func.coalesce(func.nullif(func.lower(func.trim(models.UserSkill.proficiency_level)), ""), "beginner")


def _canonicalize_level_value(value: Optional[str]) -> str:
    normalized = str(value or "").strip().lower()
    return PROFICIENCY_LEVELS_BY_KEY.get(normalized, "Beginner")

@router.get("/skills", response_model=List[SkillSearchResult])
def get_all_skills(
    db: Session = Depends(get_db),
    query: Optional[str] = None,
    category: Optional[str] = None,
    level: Optional[str] = None,
    sort_by: str = "popularity"
):
    normalized_level = _normalize_requested_level(level)
    normalized_level_key = normalized_level.lower() if normalized_level else None

    # Subquery to count mentors per skill
    mentor_count_query = (
        db.query(
            models.UserSkill.skill_id,
            func.count(func.distinct(models.UserSkill.user_id)).label("mentor_count")
        )
        .filter(func.lower(models.UserSkill.skill_type).in_(TEACH_SKILL_TYPES))
    )
    if normalized_level_key:
        mentor_count_query = mentor_count_query.filter(_normalized_proficiency_expr() == normalized_level_key)
    mentor_count_subq = mentor_count_query.group_by(models.UserSkill.skill_id).subquery()

    # Main query: Skills LEFT JOIN mentor counts
    base_query = db.query(
        models.Skill,
        func.coalesce(mentor_count_subq.c.mentor_count, 0).label("mentor_count")
    ).outerjoin(
        mentor_count_subq,
        models.Skill.id == mentor_count_subq.c.skill_id
    )

    # Apply filters
    if query:
        base_query = base_query.filter(
            models.Skill.title.ilike(f"%{query}%")
        )
    if category:
        base_query = base_query.filter(
            models.Skill.category.ilike(category)
        )
    if normalized_level_key:
        base_query = base_query.filter(func.coalesce(mentor_count_subq.c.mentor_count, 0) > 0)

    # Sorting
    if sort_by == "popularity":
        base_query = base_query.order_by(func.coalesce(mentor_count_subq.c.mentor_count, 0).desc())
    elif sort_by == "newest":
        base_query = base_query.order_by(models.Skill.created_at.desc())
    elif sort_by == "alphabetical":
        base_query = base_query.order_by(models.Skill.title.asc())

    results = base_query.all()

    return [
        {
            "id": skill.id,
            "name": skill.title,
            "description": skill.description or "",
            "category": skill.category or "General",
            "level": normalized_level,
            "mentor_count": count
        }
        for skill, count in results
    ]

@router.get("/skills/trending", response_model=List[SkillSearchResult])
def get_trending_skills(
    db: Session = Depends(get_db),
    days: int = 30,
    limit: int = 50,
):
    """
    Backend-driven trending skills analytics.

    Trending score is based on:
    1) Session demand in recent window (non-cancelled)
    2) Mentor availability for the skill
    """
    days = max(1, min(days, 180))
    limit = max(1, min(limit, 200))
    since = datetime.utcnow() - timedelta(days=days)

    recent_session_subq = (
        db.query(
            models.Session.skill_id.label("skill_id"),
            func.count(models.Session.id).label("recent_session_count"),
        )
        .filter(
            models.Session.skill_id.isnot(None),
            models.Session.created_at >= since,
            models.Session.status != "Cancelled",
        )
        .group_by(models.Session.skill_id)
        .subquery()
    )

    mentor_count_subq = (
        db.query(
            models.UserSkill.skill_id.label("skill_id"),
            func.count(func.distinct(models.UserSkill.user_id)).label("mentor_count"),
        )
        .filter(func.lower(models.UserSkill.skill_type).in_(TEACH_SKILL_TYPES))
        .group_by(models.UserSkill.skill_id)
        .subquery()
    )

    rows = (
        db.query(
            models.Skill,
            func.coalesce(recent_session_subq.c.recent_session_count, 0).label("recent_session_count"),
            func.coalesce(mentor_count_subq.c.mentor_count, 0).label("mentor_count"),
        )
        .outerjoin(recent_session_subq, recent_session_subq.c.skill_id == models.Skill.id)
        .outerjoin(mentor_count_subq, mentor_count_subq.c.skill_id == models.Skill.id)
        .order_by(
            func.coalesce(recent_session_subq.c.recent_session_count, 0).desc(),
            func.coalesce(mentor_count_subq.c.mentor_count, 0).desc(),
            models.Skill.created_at.desc(),
        )
        .limit(limit)
        .all()
    )

    return [
        {
            "id": skill.id,
            "name": skill.title,
            "description": skill.description or "",
            "category": skill.category or "General",
            "level": None,
            "mentor_count": mentor_count,
        }
        for skill, _, mentor_count in rows
    ]


@router.get("/skills/recent", response_model=List[SkillSearchResult])
def get_recent_skills(
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """
    Backend-driven recent skills feed.
    """
    limit = max(1, min(limit, 200))

    mentor_count_subq = (
        db.query(
            models.UserSkill.skill_id.label("skill_id"),
            func.count(func.distinct(models.UserSkill.user_id)).label("mentor_count"),
        )
        .filter(func.lower(models.UserSkill.skill_type).in_(TEACH_SKILL_TYPES))
        .group_by(models.UserSkill.skill_id)
        .subquery()
    )

    rows = (
        db.query(
            models.Skill,
            func.coalesce(mentor_count_subq.c.mentor_count, 0).label("mentor_count"),
        )
        .outerjoin(mentor_count_subq, mentor_count_subq.c.skill_id == models.Skill.id)
        .order_by(models.Skill.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": skill.id,
            "name": skill.title,
            "description": skill.description or "",
            "category": skill.category or "General",
            "level": None,
            "mentor_count": mentor_count,
        }
        for skill, mentor_count in rows
    ]


@router.get("/mentors/{skill_id}", response_model=List[MentorSearchResult])
def get_mentors_for_skill(
    skill_id: int,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get all mentors who teach a specific skill (public endpoint - no auth required).
    """
    normalized_level = _normalize_requested_level(level)
    normalized_level_key = normalized_level.lower() if normalized_level else None

    mentor_link_query = (
        db.query(
            models.UserSkill.user_id.label("user_id"),
            func.min(models.UserSkill.id).label("user_skill_id"),
        )
        .filter(
            models.UserSkill.skill_id == skill_id,
            func.lower(models.UserSkill.skill_type).in_(TEACH_SKILL_TYPES),
        )
    )
    if normalized_level_key:
        mentor_link_query = mentor_link_query.filter(_normalized_proficiency_expr() == normalized_level_key)
    mentor_link_subq = mentor_link_query.group_by(models.UserSkill.user_id).subquery()

    mentor_session_count_subq = (
        db.query(
            models.Session.mentor_id.label("mentor_id"),
            func.count(models.Session.id).label("session_count"),
        )
        .filter(models.Session.status == "Completed")
        .group_by(models.Session.mentor_id)
        .subquery()
    )

    rows = (
        db.query(
            models.UserSkill,
            models.MentorRating.average_rating.label("average_rating"),
            func.coalesce(mentor_session_count_subq.c.session_count, 0).label("session_count"),
        )
        .join(mentor_link_subq, mentor_link_subq.c.user_skill_id == models.UserSkill.id)
        .join(models.User, models.User.id == models.UserSkill.user_id)
        .outerjoin(models.MentorRating, models.MentorRating.mentor_id == models.UserSkill.user_id)
        .outerjoin(mentor_session_count_subq, mentor_session_count_subq.c.mentor_id == models.UserSkill.user_id)
        .filter(
            models.User.is_active == True,
        )
        .order_by(
            models.MentorRating.average_rating.desc().nullslast(),
            func.coalesce(mentor_session_count_subq.c.session_count, 0).desc(),
            models.User.name.asc(),
        )
        .all()
    )

    return [
        {
            "id": us.id,
            "user_id": us.user_id,
            "mentor_name": us.user.name,
            "qualification": getattr(us.user.profile, "qualification", "N/A") if us.user.profile else "N/A",
            "experience": getattr(us.user.profile, "experience", "N/A") if us.user.profile else "N/A",
            "proficiency_level": _canonicalize_level_value(us.proficiency_level),
            "rating": round(float(average_rating), 2) if average_rating is not None else None,
            "session_count": int(session_count or 0),
        }
        for us, average_rating, session_count in rows
    ]
