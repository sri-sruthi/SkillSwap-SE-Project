# app/models/__init__.py
# Import models in dependency order
from .user import User, UserProfile, TokenWallet
from .skill import Skill, UserSkill
from .session import Session  # Import Session LAST

__all__ = ["User", "UserProfile", "TokenWallet", "Skill", "UserSkill", "Session"]