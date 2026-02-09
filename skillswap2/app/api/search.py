from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app import models
from app.schemas import SkillSearchResult, MentorSearchResult

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("/skills", response_model=List[SkillSearchResult])
def get_all_skills(
    db: Session = Depends(get_db),
    query: Optional[str] = None,
    category: Optional[str] = None,
    level: Optional[str] = None,
    sort_by: str = "popularity"
):
    # Subquery to count mentors per skill
    mentor_count_subq = (
        db.query(
            models.UserSkill.skill_id,
            func.count(models.UserSkill.id).label("mentor_count")
        )
        .filter(models.UserSkill.skill_type == "teach")
        .group_by(models.UserSkill.skill_id)
        .subquery()
    )

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
            "level": "Beginner",
            "mentor_count": count
        }
        for skill, count in results
    ]

@router.get("/mentors/{skill_id}", response_model=List[MentorSearchResult])
def get_mentors_for_skill(skill_id: int, db: Session = Depends(get_db)):
    """
    Get all mentors who teach a specific skill (public endpoint - no auth required).
    """
    mentors = (
        db.query(models.UserSkill)
        .join(models.User)
        .filter(
            models.UserSkill.skill_id == skill_id,
            models.UserSkill.skill_type == "teach"
        )
        .all()
    )

    # Return empty list instead of 404 (better UX)
    return [
        {
            "id": us.id,
            "user_id": us.user_id,
            "mentor_name": us.user.name,
            "qualification": getattr(us.user.profile, "qualification", "N/A") if us.user.profile else "N/A",
            "experience": getattr(us.user.profile, "experience", "N/A") if us.user.profile else "N/A",
            "rating": 4.8,          # Placeholder - replace with real rating later
            "session_count": 12     # Placeholder - replace with real count later
        }
        for us in mentors
    ]