# skillswap2/app/schemas/recommendation.py
"""
Recommendation Pydantic Schemas
Phase 6: Request/response models for ML recommendations
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class MentorTeachingSkill(BaseModel):
    """Skill a mentor can teach"""
    id: int = Field(..., description="Skill ID")
    name: str = Field(..., description="Skill name")


# ======================
# RECOMMENDATION RESPONSE
# ======================

class RecommendationResponse(BaseModel):
    """Mentor recommendation response"""
    mentor_id: int = Field(..., description="Mentor user ID")
    mentor_name: str = Field(..., description="Mentor name")
    similarity_score: float = Field(..., ge=0, le=1, description="Skill similarity score (0-1)")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Average mentor rating (0-5)")
    compatibility_score: float = Field(..., ge=0, le=1, description="Overall compatibility score (0-1)")
    rank: int = Field(..., ge=1, description="Recommendation rank (1 = best match)")
    total_reviews: int = Field(0, ge=0, description="Total number of reviews")
    explanation: str = Field(..., description="Human-readable explanation")
    mentor_teaching_skills: List[MentorTeachingSkill] = Field(
        default_factory=list,
        description="Mentor skills available for session booking",
    )


# ======================
# RECOMMENDATION REQUEST
# ======================

class RecommendationRequest(BaseModel):
    """Request for mentor recommendations"""
    skill_id: Optional[int] = Field(None, description="Optional skill filter")
    top_n: int = Field(5, ge=1, le=10, description="Number of recommendations (1-10)")


# ======================
# RECOMMENDATION EXPLANATION
# ======================

class RecommendationExplanation(BaseModel):
    """Detailed recommendation explanation"""
    mentor_id: int = Field(..., description="Mentor user ID")
    mentor_name: str = Field(..., description="Mentor name")
    
    # Score components
    similarity_score: float = Field(..., description="Skill similarity (0-1)")
    rating_score: Optional[float] = Field(None, description="Mentor rating (0-5)")
    activity_score: float = Field(..., description="Activity level (0-1)")
    compatibility_score: float = Field(..., description="Final compatibility (0-1)")
    
    # Weights
    weight_similarity: float = Field(..., description="Weight for similarity component")
    weight_rating: float = Field(..., description="Weight for rating component")
    weight_activity: float = Field(..., description="Weight for activity component")
    
    # Explanation
    explanation: str = Field(..., description="Human-readable explanation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "mentor_id": 2,
                "mentor_name": "John Doe",
                "similarity_score": 0.85,
                "rating_score": 4.5,
                "activity_score": 0.7,
                "compatibility_score": 0.78,
                "weight_similarity": 0.5,
                "weight_rating": 0.3,
                "weight_activity": 0.2,
                "explanation": "Recommended because: excellent skill match, highly rated mentor, very active"
            }
        }


# ======================
# RECOMMENDATION REFRESH STATUS
# ======================

class RecommendationRefreshResponse(BaseModel):
    """Response after refreshing recommendation model"""
    message: str
    vocabulary_size: int = Field(..., description="Size of learned vocabulary")
    status: str = Field(..., description="Model status")
