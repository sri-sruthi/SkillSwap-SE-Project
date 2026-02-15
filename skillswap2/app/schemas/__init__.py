"""Central schema exports."""

# Token schemas
from .token import (
    TokenWalletCreate,
    TokenWalletResponse,
    TokenTransactionResponse,
    TokenEligibilityResponse,
    TokenTransferRequest,
)

# Review schemas
from .review import (
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    ReviewDisplay,
    ReviewSubmitResponse,
    MentorRatingResponse,
    ReviewEligibilityResponse,
    ReviewModerationRequest,
    RatingRecalculationResponse,
)

# Backward-compatible aliases used by older imports.
Review = ReviewResponse
MentorRating = MentorRatingResponse

# Recommendation schemas
from .recommendation import (
    RecommendationResponse,
    RecommendationRequest,
    RecommendationExplanation,
    RecommendationRefreshResponse,
)

# User schemas
from .user import (
    User,
    UserCreate,
    UserBase,
    UserProfileCreate,
    UserProfile,
    UserProfileUpdate,
)

# Auth schemas
from .auth import Token, TokenData, LoginRequest

# Skill schemas
from .skill import Skill, SkillCreate, UserSkill, UserSkillCreate

# Search schemas
from .search import SkillSearchResult, MentorSearchResult

__all__ = [
    "TokenWalletCreate",
    "TokenWalletResponse",
    "TokenTransactionResponse",
    "TokenEligibilityResponse",
    "TokenTransferRequest",
    "Review",
    "ReviewCreate",
    "ReviewUpdate",
    "ReviewResponse",
    "ReviewDisplay",
    "ReviewSubmitResponse",
    "MentorRating",
    "MentorRatingResponse",
    "ReviewEligibilityResponse",
    "ReviewModerationRequest",
    "RatingRecalculationResponse",
    "RecommendationResponse",
    "RecommendationRequest",
    "RecommendationExplanation",
    "RecommendationRefreshResponse",
    "User",
    "UserCreate",
    "UserBase",
    "UserProfileCreate",
    "UserProfile",
    "UserProfileUpdate",
    "Token",
    "TokenData",
    "LoginRequest",
    "Skill",
    "SkillCreate",
    "UserSkill",
    "UserSkillCreate",
    "SkillSearchResult",
    "MentorSearchResult",
]
