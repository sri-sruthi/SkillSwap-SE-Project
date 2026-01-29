from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ---------- SKILL ----------

class SkillBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None


class SkillCreate(SkillBase):
    pass


class Skill(SkillBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- USER SKILL ----------

class UserSkillBase(BaseModel):
    skill_type: str
    proficiency_level: Optional[str] = None
    tags: Optional[List[str]] = []


class UserSkillCreate(UserSkillBase):
    skill_id: int


class UserSkill(UserSkillBase):
    id: int
    user_id: int
    skill_id: int
    skill: Optional[Skill] = None
    created_at: datetime

    class Config:
        from_attributes = True
