# skillswap2/app/schemas/review.py
"""
Review & Rating Pydantic Schemas
Phase 4: Request/response models with validation
"""

from pydantic import BaseModel, ConfigDict, Field, validator
from typing import Optional
from datetime import datetime


# ======================
# REVIEW SCHEMAS
# ======================

class ReviewBase(BaseModel):
    """Base review schema"""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    comment: Optional[str] = Field(None, max_length=1000, description="Review comment (max 1000 chars)")
    
    @validator('comment')
    def validate_comment(cls, v):
        """Validate comment is not just whitespace"""
        if v is not None and v.strip() == "":
            raise ValueError("Comment cannot be empty or just whitespace")
        return v.strip() if v else None


class ReviewCreate(ReviewBase):
    """Schema for creating a review"""
    session_id: int = Field(..., description="Session identifier")


class ReviewUpdate(BaseModel):
    """Schema for updating a review"""
    rating: Optional[int] = Field(None, ge=1, le=5, description="New rating (1-5)")
    comment: Optional[str] = Field(None, max_length=1000, description="New comment")
    
    @validator('comment')
    def validate_comment(cls, v):
        """Validate comment is not just whitespace"""
        if v is not None and v.strip() == "":
            raise ValueError("Comment cannot be empty or just whitespace")
        return v.strip() if v else None


class ReviewResponse(BaseModel):
    """Review response for API"""
    review_id: int = Field(..., description="Review identifier")
    session_id: int = Field(..., description="Session identifier")
    learner_id: int = Field(..., description="Learner user ID")
    learner_name: Optional[str] = Field(None, description="Learner name")
    mentor_id: int = Field(..., description="Mentor user ID")
    mentor_name: Optional[str] = Field(None, description="Mentor name")
    rating: int = Field(..., description="Rating (1-5)")
    comment: Optional[str] = Field(None, description="Review comment")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class ReviewDisplay(BaseModel):
    """Simplified review display (for public mentor profiles)"""
    review_id: int
    learner_name: str = Field(..., description="Learner name (anonymized if needed)")
    rating: int
    comment: Optional[str] = None
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ReviewSubmitResponse(BaseModel):
    """Response after submitting a review"""
    review_id: int
    session_id: int
    rating: int
    comment: Optional[str] = None
    created_at: Optional[str] = None
    mentor_new_average: float = Field(..., description="Mentor's updated average rating")
    mentor_total_reviews: int = Field(..., description="Mentor's total review count")
    message: str


# ======================
# MENTOR RATING SCHEMAS
# ======================

class MentorRatingResponse(BaseModel):
    """Mentor rating summary response"""
    mentor_id: int = Field(..., description="Mentor user ID")
    average_rating: float = Field(..., description="Average rating (0-5)")
    total_reviews: int = Field(..., description="Total number of reviews")
    rating_distribution: dict = Field(..., description="Count of each rating (1-5)")
    rating_distribution_percentage: dict = Field(..., description="Percentage of each rating")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class RatingDistribution(BaseModel):
    """Rating distribution detail"""
    five_stars: int = Field(0, description="Number of 5-star reviews")
    four_stars: int = Field(0, description="Number of 4-star reviews")
    three_stars: int = Field(0, description="Number of 3-star reviews")
    two_stars: int = Field(0, description="Number of 2-star reviews")
    one_star: int = Field(0, description="Number of 1-star reviews")


# ======================
# ELIGIBILITY CHECK SCHEMA
# ======================

class ReviewEligibilityResponse(BaseModel):
    """Review eligibility check response"""
    can_review: bool = Field(..., description="Whether learner can review this session")
    reason: str = Field(..., description="Reason (error message or 'Can review')")
    session_id: int = Field(..., description="Session identifier")


# ======================
# ADMIN SCHEMAS
# ======================

class ReviewModerationRequest(BaseModel):
    """Admin review moderation request"""
    action: str = Field(..., description="Action: 'delete' or 'flag'")
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for moderation")


class RatingRecalculationResponse(BaseModel):
    """Response after recalculating all ratings"""
    total_mentors: int = Field(..., description="Total mentors processed")
    updated_count: int = Field(..., description="Successfully updated count")
    errors: list = Field(default_factory=list, description="Any errors encountered")
    message: str
