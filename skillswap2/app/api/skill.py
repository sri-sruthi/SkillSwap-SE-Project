from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from typing import List  # ← ADDED: Required for tags: List[str]
from app.database import get_db
from app import models
from app.utils.security import get_current_user

router = APIRouter(prefix="/skills", tags=["Skills"])

# ======================
# GET: All skills with mentor count
# ======================
@router.get("/")
def get_all_skills(db: Session = Depends(get_db)):
    skills = db.query(
        models.Skill,
        db.query(models.UserSkill)
          .filter(models.UserSkill.skill_id == models.Skill.id)
          .filter(models.UserSkill.skill_type == "teach")
          .count()
          .label("mentor_count")
    ).all()
    
    return [
        {
            "id": skill.id,
            "name": skill.title,  # Maps DB 'title' → API field 'name'
            "description": skill.description or "",
            "category": skill.category or "General",
            "level": "Beginner",  # Placeholder (add 'level' column to Skill model later)
            "mentor_count": mentor_count
        }
        for skill, mentor_count in skills
    ]

# ======================
# POST: Add new skill (for mentors)
# ======================
@router.post("/")
def add_skill(
    title: str = Form(...),
    description: str = Form(None),
    category: str = Form("General"),  # ← FIXED: Added type annotation
    proficiency_level: str = Form("Beginner"),
    tags: List[str] = Form([]),  # ← Requires 'from typing import List'
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "mentor":
        raise HTTPException(403, "Only mentors can add skills")

    # Check if skill already exists (case-insensitive)
    existing = db.query(models.Skill).filter(
        models.Skill.title.ilike(title)
    ).first()

    if existing:
        skill_id = existing.id
    else:
        new_skill = models.Skill(
            title=title,
            description=description or "",
            category=category
        )
        db.add(new_skill)
        db.commit()
        db.refresh(new_skill)
        skill_id = new_skill.id

    # Link to mentor
    user_skill = models.UserSkill(
        user_id=current_user.id,
        skill_id=skill_id,
        skill_type="teach",
        proficiency_level=proficiency_level,
        tags=tags
    )
    db.add(user_skill)
    db.commit()
    db.refresh(user_skill)  # ← GOOD PRACTICE: Refresh after commit

    return {"message": f"Skill '{title}' added successfully"}

# ======================
# GET: My skills (mentor/learner)
# ======================
@router.get("/my/{skill_type}")  # ← TYPO FIX: Was '@roker' → should be '@router'
def get_my_skills(
    skill_type: str,  # "teach" or "learn"
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if skill_type not in ["teach", "learn"]:
        raise HTTPException(400, "skill_type must be 'teach' or 'learn'")
    
    user_skills = db.query(models.UserSkill).filter(
        models.UserSkill.user_id == current_user.id,
        models.UserSkill.skill_type == skill_type
    ).all()
    
    return [
        {
            "id": us.id,
            "skill_id": us.skill_id,
            "title": us.skill.title if us.skill else "N/A",
            "description": us.skill.description if us.skill else "",
            "category": us.skill.category if us.skill else "General",
            "proficiency_level": us.proficiency_level,  # ← ADDED: Include level
            "tags": us.tags or []  # ← ADDED: Include tags
        }
        for us in user_skills
    ]

# ======================
# DELETE: Remove skill (mentor only)
# ======================
# ======================
# DELETE: Remove skill (mentor only)
# ======================
@router.delete("/{user_skill_id}")
def remove_skill(
    user_skill_id: int,  # ← Rename to clarify: this is UserSkill.id
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "mentor":
        raise HTTPException(403, "Only mentors can remove skills")
    
    # Find the UserSkill record by its own ID (not skill_id!)
    user_skill = db.query(models.UserSkill).filter(
        models.UserSkill.id == user_skill_id,          # ✅ Correct: UserSkill.id
        models.UserSkill.user_id == current_user.id,
        models.UserSkill.skill_type == "teach"
    ).first()
    
    if not user_skill:
        raise HTTPException(404, "Skill link not found in your teachable list")
    
    db.delete(user_skill)
    db.commit()
    return {"message": "Skill removed successfully"}