from pydantic import BaseModel
from typing import Optional, List

# ======================
# SKILL SCHEMAS
# ======================

# app/schemas/skill.py
class SkillBase(BaseModel):
    title: str  # ← CHANGED FROM 'name' TO 'title'
    description: Optional[str] = None
    category: Optional[str] = "General"

class SkillCreate(SkillBase):
    pass

class Skill(SkillBase):
    id: int
    
    class Config:
        from_attributes = True  # For SQLAlchemy ORM mode

# ======================
# USER_SKILL SCHEMAS
# ======================

class UserSkillBase(BaseModel):
    skill_id: int
    skill_type: str  # "teach" or "learn"
    proficiency_level: Optional[str] = None
    tags: Optional[List[str]] = []

class UserSkillCreate(UserSkillBase):
    pass

class UserSkill(UserSkillBase):
    id: int
    user_id: int
    
    class Config:
        from_attributes = True

# ======================
# RESPONSE MODELS
# ======================

class SkillWithMentorCount(Skill):
    mentor_count: int

class MentorSkillResponse(BaseModel):
    id: int
    skill_id: int
    title: str  # ← matches Skill.title
    description: Optional[str] = None
    category: Optional[str] = None

# app/schemas/skill.py

from pydantic import BaseModel
from typing import Optional, List

class SkillSearchResult(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = "General"
    level: Optional[str] = "Beginner"
    mentor_count: int

class MentorSearchResult(BaseModel):
    id: int
    user_id: int
    mentor_name: str
    qualification: Optional[str] = None
    experience: Optional[str] = None
    rating: Optional[float] = None
    session_count: Optional[int] = 0