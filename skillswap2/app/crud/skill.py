from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas


# ============================
# SKILL TABLE
# ============================

def create_skill(db: Session, skill: schemas.SkillCreate):
    new_skill = models.Skill(
        name=skill.name,
        description=skill.description,
        category=skill.category
    )
    db.add(new_skill)
    db.commit()
    db.refresh(new_skill)
    return new_skill


def get_skill(db: Session, skill_id: int):
    return db.query(models.Skill).filter(models.Skill.id == skill_id).first()


def get_skill_by_name(db: Session, name: str):
    return db.query(models.Skill).filter(
        func.lower(models.Skill.name) == func.lower(name)
    ).first()


def get_skills(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Skill).offset(skip).limit(limit).all()


# ============================
# USER SKILLS (TEACH / LEARN)
# ============================

def create_user_skill(db: Session, user_id: int, skill_id: int, skill_type: str,
                      proficiency_level=None, tags=None):

    skill = get_skill(db, skill_id)
    if not skill:
        raise ValueError("Skill not found")

    existing = db.query(models.UserSkill).filter(
        models.UserSkill.user_id == user_id,
        models.UserSkill.skill_id == skill_id,
        models.UserSkill.skill_type == skill_type
    ).first()

    if existing:
        return existing

    user_skill = models.UserSkill(
        user_id=user_id,
        skill_id=skill_id,
        skill_type=skill_type,
        proficiency_level=proficiency_level,
        tags=tags or []
    )

    db.add(user_skill)
    db.commit()
    db.refresh(user_skill)
    return user_skill


def get_user_skills(db: Session, user_id: int, skill_type: str):
    return db.query(models.UserSkill).filter(
        models.UserSkill.user_id == user_id,
        models.UserSkill.skill_type == skill_type
    ).all()


def delete_user_skill(db: Session, user_skill_id: int, user_id: int):
    user_skill = db.query(models.UserSkill).filter(
        models.UserSkill.id == user_skill_id,
        models.UserSkill.user_id == user_id
    ).first()

    if not user_skill:
        return False

    db.delete(user_skill)
    db.commit()
    return True


# ============================
# EXTRA (OPTIONAL ANALYTICS)
# ============================

def get_skills_with_mentor_count(db: Session):
    result = db.query(
        models.Skill,
        func.count(models.UserSkill.id).label("mentor_count")
    ).outerjoin(
        models.UserSkill,
        (models.Skill.id == models.UserSkill.skill_id) &
        (models.UserSkill.skill_type == "teach")
    ).group_by(models.Skill.id).all()

    return [
        {"skill": skill, "mentor_count": count}
        for skill, count in result
    ]
