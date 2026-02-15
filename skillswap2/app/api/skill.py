from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.utils.security import get_current_user

router = APIRouter(prefix="/skills", tags=["Skills"])

ROLE_DEFAULT_SKILL_TYPE = {
    "student": "learn",
    "mentor": "teach",
    "learner": "learn",
}

ROLE_ALLOWED_SKILL_TYPES = {
    "student": {"teach", "learn"},
    "mentor": {"teach", "learn"},
    "learner": {"teach", "learn"},
}

VALID_SKILL_TYPES = {"teach", "learn"}
SKILL_TYPE_ALIASES = {
    "teach": "teach",
    "learn": "learn",
    "offer": "teach",
    "need": "learn",
}
CANONICAL_SKILL_TYPES = {
    "teach": ("teach", "offer"),
    "learn": ("learn", "need"),
}


def normalize_skill_type(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    return SKILL_TYPE_ALIASES.get((raw or "").strip().lower())


def accepted_skill_types(skill_type: str) -> tuple[str, ...]:
    return CANONICAL_SKILL_TYPES.get(skill_type, (skill_type,))


def choose_preferred_link(
    links: list[models.UserSkill],
    preferred_type: str,
) -> models.UserSkill:
    """
    Choose the best row when legacy alias and canonical rows both exist.
    Prefer canonical type first, then oldest row for deterministic behavior.
    """
    ordered = sorted(
        links,
        key=lambda link: (
            0 if (link.skill_type or "").strip().lower() == preferred_type else 1,
            link.id,
        ),
    )
    return ordered[0]


# ======================
# GET: All skills with mentor count
# ======================
@router.get("/")
def get_all_skills(db: Session = Depends(get_db)):
    skills = (
        db.query(
            models.Skill,
            func.count(func.distinct(models.UserSkill.user_id)).label("mentor_count"),
        )
        .outerjoin(
            models.UserSkill,
            and_(
                models.UserSkill.skill_id == models.Skill.id,
                models.UserSkill.skill_type.in_(accepted_skill_types("teach")),
            ),
        )
        .group_by(models.Skill.id)
        .all()
    )

    return [
        {
            "id": skill.id,
            "name": skill.title,
            "description": skill.description or "",
            "category": skill.category or "General",
            "level": "Beginner",
            "mentor_count": mentor_count,
        }
        for skill, mentor_count in skills
    ]


# ======================
# POST: Add new skill link (mentor teach / learner learn)
# ======================
@router.post("/")
def add_skill(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    category: str = Form("General"),
    proficiency_level: str = Form("Beginner"),
    tags: List[str] = Form([]),
    skill_type: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = (current_user.role or "").lower()
    if role not in ROLE_DEFAULT_SKILL_TYPE:
        raise HTTPException(403, "Only non-admin users can manage skills")

    requested_type = normalize_skill_type(skill_type) or ROLE_DEFAULT_SKILL_TYPE[role]
    if requested_type not in VALID_SKILL_TYPES:
        raise HTTPException(400, "skill_type must be one of: teach, learn, offer, need")
    if requested_type not in ROLE_ALLOWED_SKILL_TYPES[role]:
        raise HTTPException(403, "Not allowed to add this skill type")

    clean_title = (title or "").strip()
    if not clean_title:
        raise HTTPException(400, "title is required")

    clean_tags = []
    seen = set()
    for tag in tags or []:
        value = (tag or "").strip()
        if not value:
            continue
        lower = value.lower()
        if lower in seen:
            continue
        seen.add(lower)
        clean_tags.append(value)

    existing_skill = db.query(models.Skill).filter(models.Skill.title.ilike(clean_title)).first()
    if existing_skill:
        skill = existing_skill
    else:
        skill = models.Skill(
            title=clean_title,
            description=(description or "").strip(),
            category=(category or "General").strip() or "General",
        )
        db.add(skill)
        db.flush()

    matching_links = (
        db.query(models.UserSkill)
        .filter(
            models.UserSkill.user_id == current_user.id,
            models.UserSkill.skill_id == skill.id,
            models.UserSkill.skill_type.in_(accepted_skill_types(requested_type)),
        )
        .order_by(models.UserSkill.id.asc())
        .all()
    )

    if matching_links:
        existing_link = choose_preferred_link(matching_links, requested_type)
        duplicate_links = [link for link in matching_links if link.id != existing_link.id]

        # Canonicalize preferred row and collapse alias duplicates.
        existing_link.skill_type = requested_type
        existing_link.proficiency_level = proficiency_level
        existing_link.tags = clean_tags
        for duplicate in duplicate_links:
            db.delete(duplicate)

        db.commit()
        return {
            "message": f"Skill '{skill.title}' already exists in your {requested_type} list and was updated",
            "action": "updated",
            "skill_type": requested_type,
        }

    user_skill = models.UserSkill(
        user_id=current_user.id,
        skill_id=skill.id,
        skill_type=requested_type,
        proficiency_level=proficiency_level,
        tags=clean_tags,
    )
    db.add(user_skill)
    db.commit()

    return {
        "message": f"Skill '{skill.title}' added successfully to your {requested_type} list",
        "action": "created",
        "skill_type": requested_type,
    }

# ======================
# GET: My skills (mentor/learner)
# ======================
@router.get("/my/{skill_type}")  # ← TYPO FIX: Was '@roker' → should be '@router'
def get_my_skills(
    skill_type: str,  # "teach" or "learn"
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    normalized_type = normalize_skill_type(skill_type)
    if normalized_type not in ["teach", "learn"]:
        raise HTTPException(400, "skill_type must be one of: teach, learn, offer, need")
    
    user_skills = (
        db.query(models.UserSkill)
        .filter(
            models.UserSkill.user_id == current_user.id,
            models.UserSkill.skill_type.in_(accepted_skill_types(normalized_type)),
        )
        .order_by(models.UserSkill.id.asc())
        .all()
    )

    # Hide legacy alias duplicates in API output (teach+offer / learn+need).
    by_skill_id: dict[int, list[models.UserSkill]] = {}
    for row in user_skills:
        by_skill_id.setdefault(row.skill_id, []).append(row)

    preferred_rows = [
        choose_preferred_link(links, normalized_type)
        for _, links in sorted(by_skill_id.items(), key=lambda item: item[0])
    ]
    
    return [
        {
            "id": us.id,
            "skill_id": us.skill_id,
            "title": us.skill.title if us.skill else "N/A",
            "description": us.skill.description if us.skill else "",
            "category": us.skill.category if us.skill else "General",
            "proficiency_level": us.proficiency_level,
            "tags": us.tags or [],
        }
        for us in preferred_rows
    ]

# ======================
# DELETE: Remove user skill link
# ======================
@router.delete("/{user_skill_id}")
def remove_skill(
    user_skill_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = (current_user.role or "").lower()
    if role not in ROLE_DEFAULT_SKILL_TYPE:
        raise HTTPException(403, "Only non-admin users can manage skills")

    user_skill = db.query(models.UserSkill).filter(
        models.UserSkill.id == user_skill_id,
        models.UserSkill.user_id == current_user.id,
    ).first()

    if not user_skill:
        raise HTTPException(404, "Skill link not found in your list")

    db.delete(user_skill)
    db.commit()
    return {"message": "Skill removed successfully"}
