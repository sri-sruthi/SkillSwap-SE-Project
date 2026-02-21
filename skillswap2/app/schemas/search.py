from pydantic import BaseModel
from typing import Optional, List

# ======================
# SEARCH REQUEST MODELS
# ======================

class SearchQuery(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    level: Optional[str] = None
    sort_by: Optional[str] = "popularity"  # popularity, newest, rating

# ======================
# SKILL SEARCH RESULTS
# ======================

class SkillSearchResult(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = "General"
    level: Optional[str] = "Beginner"
    mentor_count: int

# ======================
# MENTOR SEARCH RESULTS
# ======================

class MentorSearchResult(BaseModel):
    id: int
    user_id: int
    mentor_name: str
    qualification: Optional[str] = None
    experience: Optional[str] = None
    proficiency_level: Optional[str] = "Beginner"
    rating: Optional[float] = None
    session_count: Optional[int] = 0

# ======================
# CATEGORY MODEL
# ======================

class Category(BaseModel):
    name: str
    skill_count: int

# ======================
# POPULAR SKILLS RESPONSE
# ======================

class PopularSkillsResponse(BaseModel):
    skills: List[SkillSearchResult]

# ======================
# MENTOR DETAILS FOR SESSION REQUEST
# ======================

class MentorDetail(BaseModel):
    id: int
    user_id: int
    name: str
    qualification: Optional[str] = None
    bio: Optional[str] = None
    available_slots: Optional[int] = None
