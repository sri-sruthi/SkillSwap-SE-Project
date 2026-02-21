from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.utils.security import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])
TEACH_SKILL_TYPES = ("teach", "offer")
LEARN_SKILL_TYPES = ("learn", "need")


def _teaching_skill_sort_key(user_skill: models.UserSkill) -> tuple[int, int]:
    raw_type = (user_skill.skill_type or "").strip().lower()
    return (0 if raw_type == "teach" else 1, user_skill.id)


# ======================
# GET: Public mentor profile basics
# ======================
@router.get("/public/{mentor_id}")
def get_public_mentor_profile(
    mentor_id: int,
    db: Session = Depends(get_db)
):
    mentor = db.query(models.User).filter(
        models.User.id == mentor_id,
        models.User.is_active == True
    ).first()

    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")

    teaches_any_skill = db.query(models.UserSkill.id).filter(
        models.UserSkill.user_id == mentor_id,
        func.lower(models.UserSkill.skill_type).in_(TEACH_SKILL_TYPES),
    ).first()
    if not teaches_any_skill:
        raise HTTPException(status_code=404, detail="Mentor not found")

    teach_rows = (
        db.query(models.UserSkill)
        .filter(
            models.UserSkill.user_id == mentor_id,
            func.lower(models.UserSkill.skill_type).in_(TEACH_SKILL_TYPES),
        )
        .order_by(models.UserSkill.id.asc())
        .all()
    )

    # Collapse legacy alias duplicates (teach + offer for same skill).
    by_skill_id = {}
    for row in teach_rows:
        by_skill_id.setdefault(row.skill_id, []).append(row)
    preferred_rows = [
        sorted(rows, key=_teaching_skill_sort_key)[0]
        for _, rows in sorted(by_skill_id.items(), key=lambda item: item[0])
    ]

    profile = mentor.profile
    full_name = profile.full_name if profile and profile.full_name else mentor.name
    qualification = profile.qualification if profile else None
    experience = profile.experience if profile else None

    return {
        "id": mentor.id,
        "name": mentor.name,
        "full_name": full_name,
        "display_name": full_name or mentor.name,
        "qualification": qualification,
        "experience": experience,
        "role": mentor.role,
        "teaching_skills": [
            {
                "skill_id": row.skill_id,
                "title": row.skill.title if row.skill else "N/A",
                "category": row.skill.category if row.skill else "General",
                "proficiency_level": row.proficiency_level or "Not specified",
            }
            for row in preferred_rows
        ],
    }


# ======================
# GET: Current user profile
# ======================
@router.get("/me")
def get_current_user_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    can_teach = db.query(models.UserSkill.id).filter(
        models.UserSkill.user_id == current_user.id,
        func.lower(models.UserSkill.skill_type).in_(TEACH_SKILL_TYPES),
    ).first() is not None
    can_learn = db.query(models.UserSkill.id).filter(
        models.UserSkill.user_id == current_user.id,
        func.lower(models.UserSkill.skill_type).in_(LEARN_SKILL_TYPES),
    ).first() is not None

    base_info = {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "name": current_user.name,  # From User model
        "can_teach": can_teach,
        "can_learn": can_learn,
        "profile": {
            "full_name": profile.full_name,
            "phone": profile.phone,
            "age": profile.age,
            "qualification": profile.qualification,
            "experience": profile.experience,
            "college": profile.studying,
            "what_to_learn": profile.bio,
        }
    }

    return base_info


# ======================
# PUT: Update profile (both roles)
# ======================
@router.put("/profile")
def update_profile(
    full_name: str = Form(None),
    phone: str = Form(None),
    age: int = Form(None),
    # Mentor-specific
    qualification: str = Form(None),
    experience: str = Form(None),
    # Learner-specific
    studying: str = Form(None),
    bio: str = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Update common fields
    if full_name is not None:
        profile.full_name = full_name
    if phone is not None:
        profile.phone = phone
    if age is not None:
        profile.age = age

    # Capability-based profile fields (dual-role friendly)
    if qualification is not None:
        profile.qualification = qualification
    if experience is not None:
        profile.experience = experience
    if studying is not None:
        profile.studying = studying
    if bio is not None:
        profile.bio = bio

    db.commit()
    return {"message": "Profile updated successfully"}


# ======================
# PUT: Update password
# ======================
@router.put("/password")
def update_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.utils.security import verify_password, get_password_hash
    
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    current_user.password_hash = get_password_hash(new_password)
    db.commit()
    return {"message": "Password updated successfully"}
