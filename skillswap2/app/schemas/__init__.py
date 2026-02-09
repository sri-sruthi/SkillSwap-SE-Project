# app/schemas/__init__.py

# User schemas
from .user import (
    User,
    UserCreate,
    UserBase,
    UserProfileCreate,
    UserProfile,
    UserProfileUpdate,
    TokenWalletResponse
)

# Auth schemas
from .auth import Token, TokenData, LoginRequest

# Skill schemas
from .skill import (
    Skill,
    SkillCreate,
    UserSkill,
    UserSkillCreate
)

# Search result schemas (critical fix!)
from .search import (
    SkillSearchResult,
    MentorSearchResult
)

__all__ = [
    "User",
    "UserCreate",
    "UserBase",
    "UserProfileCreate",
    "UserProfile",
    "UserProfileUpdate",
    "TokenWalletResponse",
    "Token",
    "TokenData",
    "LoginRequest",
    "Skill",
    "SkillCreate",
    "UserSkill",
    "UserSkillCreate",
    "SkillSearchResult",      # ✅ Now imported
    "MentorSearchResult"      # ✅ Now imported
]