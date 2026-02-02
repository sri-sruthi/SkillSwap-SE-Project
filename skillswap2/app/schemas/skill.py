from pydantic import BaseModel
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

class UserSkillCreate(BaseModel):
    skill_id: int
    proficiency_level: Optional[str] = None
    tags: Optional[List[str]] = []


class UserSkill(BaseModel):
    id: int
    user_id: int
    skill_id: int
    skill_type: str
    proficiency_level: Optional[str]
    tags: Optional[List[str]]
    created_at: datetime

    class Config:
        from_attributes = True
