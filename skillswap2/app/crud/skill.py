from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas


# ======================
# SKILL CRUD OPERATIONS
# ======================

def create_skill(db: Session, title: str, description: str = "", category: str = "General"):
    """Create a new skill in the global catalog"""
    db_skill = models.Skill(
        title=title,
        description=description,
        category=category
    )
    db.add(db_skill)
    db.commit()
    db.refresh(db_skill)
    return db_skill


def get_skill(db: Session, skill_id: int):
    """Get skill by ID"""
    return db.query(models.Skill).filter(models.Skill.id == skill_id).first()


def get_skill_by_name(db: Session, title: str):
    """Get skill by name (case-insensitive)"""
    return db.query(models.Skill).filter(
        models.Skill.title.ilike(title)
    ).first()


def get_skills(db: Session, skip: int = 0, limit: int = 100):
    """Get all skills with mentor count"""
    return db.query(
        models.Skill,
        func.count(models.UserSkill.id).label("mentor_count")
    ).outerjoin(
        models.UserSkill,
        (models.Skill.id == models.UserSkill.skill_id) &
        (models.UserSkill.skill_type == "teach")
    ).group_by(models.Skill.id).offset(skip).limit(limit).all()


# ======================
# USER_SKILL CRUD OPERATIONS
# ======================

def create_user_skill(
    db: Session, 
    user_id: int, 
    skill_id: int, 
    skill_type: str,  # "teach" or "learn"
    proficiency_level: str = None,
    tags: str = None
):
    """Link a user to a skill (mentor teaches or learner wants to learn)"""
    if skill_type not in ["teach", "learn"]:
        raise ValueError("skill_type must be 'teach' or 'learn'")
    
    db_user_skill = models.UserSkill(
        user_id=user_id,
        skill_id=skill_id,
        skill_type=skill_type,
        proficiency_level=proficiency_level,
        tags=tags
    )
    db.add(db_user_skill)
    db.commit()
    db.refresh(db_user_skill)
    return db_user_skill


def get_user_skills(
    db: Session, 
    user_id: int, 
    skill_type: str = None
):
    """Get all skills for a user (optionally filtered by type)"""
    query = db.query(models.UserSkill).filter(models.UserSkill.user_id == user_id)
    if skill_type:
        if skill_type not in ["teach", "learn"]:
            raise ValueError("skill_type must be 'teach' or 'learn'")
        query = query.filter(models.UserSkill.skill_type == skill_type)
    return query.all()


def delete_user_skill(db: Session, user_skill_id: int):
    """Remove a user-skill link"""
    db_user_skill = db.query(models.UserSkill).filter(
        models.UserSkill.id == user_skill_id
    ).first()
    if db_user_skill:
        db.delete(db_user_skill)
        db.commit()
        return True
    return False


def get_mentors_for_skill(db: Session, skill_id: int):
    """Get all mentors who teach a specific skill"""
    return db.query(models.UserSkill).filter(
        models.UserSkill.skill_id == skill_id,
        models.UserSkill.skill_type == "teach"
    ).all()


def get_learners_for_skill(db: Session, skill_id: int):
    """Get all learners who want to learn a specific skill"""
    return db.query(models.UserSkill).filter(
        models.UserSkill.skill_id == skill_id,
        models.UserSkill.skill_type == "learn"
    ).all()