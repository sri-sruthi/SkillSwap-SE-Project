from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import schemas, models
from app.crud import skill as crud
from app.utils.security import get_current_user

router = APIRouter(prefix="/skills", tags=["Skills"])


# =============================
# MENTOR → CREATE NEW SKILL
# =============================

@router.post("/", response_model=schemas.Skill)
def create_skill(
    skill: schemas.SkillCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if current_user.role != "mentor":
        raise HTTPException(403, "Only mentors can create skills")

    existing = crud.get_skill_by_name(db, skill.name)
    if existing:
        return existing

    return crud.create_skill(db, skill)


# =============================
# LEARNER → ADD SKILL
# =============================

@router.post("/learn", response_model=schemas.UserSkill)
def add_learn_skill(
    data: schemas.UserSkillCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if current_user.role != "learner":
        raise HTTPException(403, "Only learners allowed")

    data.skill_type = "learn"

    return crud.create_user_skill(db, data, current_user.id)


# =============================
# MY SKILLS
# =============================

@router.get("/my/learn", response_model=List[schemas.UserSkill])
def my_learn_skills(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_user_skills(db, current_user.id, "learn")


@router.get("/my/teach", response_model=List[schemas.UserSkill])
def my_teach_skills(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_user_skills(db, current_user.id, "teach")
