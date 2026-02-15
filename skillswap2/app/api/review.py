# skillswap2/app/api/review.py
"""
Review & Rating API Router
Phase 5: REST endpoints for review submission and rating display

Endpoints:
- POST /reviews/ - Submit a review
- GET /reviews/session/{session_id} - Get review for a session
- GET /reviews/mentor/{mentor_id} - Get all reviews for a mentor
- GET /reviews/learner/my-reviews - Get learner's submitted reviews
- GET /reviews/eligibility/{session_id} - Check review eligibility
- PATCH /reviews/{review_id} - Update a review
- DELETE /reviews/{review_id} - Delete a review
- GET /reviews/rating/{mentor_id} - Get mentor rating summary
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.user import User
from app.schemas.review import (
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    ReviewDisplay,
    ReviewSubmitResponse,
    MentorRatingResponse,
    ReviewEligibilityResponse
)
from app.services import review_service
from app.utils.security import get_current_user

router = APIRouter(prefix="/reviews", tags=["reviews"])


# ======================
# SUBMIT REVIEW
# ======================
@router.post("/", response_model=ReviewSubmitResponse, status_code=status.HTTP_201_CREATED)
def submit_review(
    review: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a review for a completed session.
    
    Requirements:
    - Session must be completed
    - User must be the learner from the session
    - Only one review per session allowed
    - Rating must be 1-5
    - Comment max 1000 characters
    
    Returns:
        Review details with updated mentor rating
    """
    try:
        result = review_service.submit_review(
            db=db,
            session_id=review.session_id,
            learner_id=current_user.id,
            rating=review.rating,
            comment=review.comment
        )
        
        return ReviewSubmitResponse(**result)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit review: {str(e)}"
        )


# ======================
# GET REVIEW BY SESSION
# ======================
@router.get("/session/{session_id}", response_model=Optional[ReviewResponse])
def get_session_review(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the review for a specific session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Review details or None if no review exists
    """
    from app.crud import review as review_crud
    
    review = review_crud.get_review_by_session(db, session_id)
    
    if not review:
        return None
    
    # Check authorization - only participants can view
    if current_user.id not in [review.learner_id, review.mentor_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this review"
        )
    
    return ReviewResponse(
        review_id=review.id,
        session_id=review.session_id,
        learner_id=review.learner_id,
        learner_name=review.learner.name if review.learner else None,
        mentor_id=review.mentor_id,
        mentor_name=review.mentor.name if review.mentor else None,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at
    )


# ======================
# GET MENTOR REVIEWS
# ======================
@router.get("/mentor/{mentor_id}", response_model=List[ReviewDisplay])
def get_mentor_reviews(
    mentor_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get all reviews for a mentor (public endpoint).
    
    Args:
        mentor_id: Mentor user ID
        limit: Maximum reviews to return (default 50)
        offset: Number of reviews to skip (default 0)
        
    Returns:
        List of reviews with learner names and ratings
    """
    try:
        reviews = review_service.get_mentor_reviews(
            db=db,
            mentor_id=mentor_id,
            limit=limit,
            offset=offset
        )
        
        return [
            ReviewDisplay(
                review_id=r["review_id"],
                learner_name=r["learner_name"],
                rating=r["rating"],
                comment=r["comment"],
                created_at=r["created_at"]
            )
            for r in reviews
        ]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve reviews: {str(e)}"
        )


# ======================
# GET LEARNER'S REVIEWS
# ======================
@router.get("/learner/my-reviews", response_model=List[ReviewResponse])
def get_my_reviews(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all reviews submitted by the current learner.
    
    Args:
        limit: Maximum reviews to return (default 50)
        offset: Number of reviews to skip (default 0)
        
    Returns:
        List of reviews submitted by current user
    """
    try:
        reviews = review_service.get_learner_reviews(
            db=db,
            learner_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        return [
            ReviewResponse(
                review_id=r["review_id"],
                session_id=r["session_id"],
                learner_id=current_user.id,
                learner_name=current_user.name,
                mentor_id=r["mentor_id"],
                mentor_name=r["mentor_name"],
                rating=r["rating"],
                comment=r["comment"],
                created_at=r["created_at"]
            )
            for r in reviews
        ]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve your reviews: {str(e)}"
        )


# ======================
# CHECK REVIEW ELIGIBILITY
# ======================
@router.get("/eligibility/{session_id}", response_model=ReviewEligibilityResponse)
def check_review_eligibility(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if current user can review a specific session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Eligibility status with reason
    """
    try:
        result = review_service.check_review_eligibility(
            db=db,
            session_id=session_id,
            learner_id=current_user.id
        )
        
        return ReviewEligibilityResponse(**result)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check eligibility: {str(e)}"
        )


# ======================
# UPDATE REVIEW
# ======================
@router.patch("/{review_id}", response_model=dict)
def update_review(
    review_id: int,
    review_update: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing review.
    
    Requirements:
    - User must be the review author
    - Rating must be 1-5 if provided
    - Comment max 1000 characters if provided
    
    Args:
        review_id: Review identifier
        review_update: Updated rating and/or comment
        
    Returns:
        Updated review details
    """
    try:
        result = review_service.update_review(
            db=db,
            review_id=review_id,
            learner_id=current_user.id,
            rating=review_update.rating,
            comment=review_update.comment
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update review: {str(e)}"
        )


# ======================
# DELETE REVIEW
# ======================
@router.delete("/{review_id}", status_code=status.HTTP_200_OK)
def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a review.
    
    Requirements:
    - User must be the review author or admin
    
    Args:
        review_id: Review identifier
        
    Returns:
        Deletion confirmation
    """
    try:
        is_admin = current_user.role == "admin"
        
        result = review_service.delete_review(
            db=db,
            review_id=review_id,
            user_id=current_user.id,
            is_admin=is_admin
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete review: {str(e)}"
        )


# ======================
# GET MENTOR RATING SUMMARY
# ======================
@router.get("/rating/{mentor_id}", response_model=MentorRatingResponse)
def get_mentor_rating(
    mentor_id: int,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive rating summary for a mentor (public endpoint).
    
    Args:
        mentor_id: Mentor user ID
        
    Returns:
        Average rating, total reviews, and rating distribution
    """
    try:
        summary = review_service.get_mentor_rating_summary(db, mentor_id)
        return MentorRatingResponse(**summary)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve rating: {str(e)}"
        )


# ======================
# ADMIN: GET ALL REVIEWS
# ======================
@router.get("/admin/all", response_model=List[ReviewResponse])
def get_all_reviews_admin(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all reviews in the system (admin only).
    
    Args:
        limit: Maximum reviews to return (default 100)
        offset: Number of reviews to skip (default 0)
        
    Returns:
        List of all reviews with full details
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        reviews = review_service.get_all_reviews(db, limit, offset)
        
        return [
            ReviewResponse(
                review_id=r["review_id"],
                session_id=r["session_id"],
                learner_id=r["learner_id"],
                learner_name=r["learner_name"],
                mentor_id=r["mentor_id"],
                mentor_name=r["mentor_name"],
                rating=r["rating"],
                comment=r["comment"],
                created_at=r["created_at"]
            )
            for r in reviews
        ]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve all reviews: {str(e)}"
        )


# ======================
# ADMIN: RECALCULATE ALL RATINGS
# ======================
@router.post("/admin/recalculate")
def recalculate_all_ratings_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Recalculate all mentor ratings (admin maintenance endpoint).
    
    Returns:
        Recalculation statistics
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        result = review_service.recalculate_all_ratings(db)
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recalculate ratings: {str(e)}"
        )


# ======================
# HEALTH CHECK
# ======================
@router.get("/health")
def review_service_health():
    """Health check endpoint for review service"""
    return {
        "service": "review_rating",
        "status": "operational",
        "features": [
            "submit_review",
            "update_review",
            "delete_review",
            "mentor_ratings",
            "eligibility_check"
        ]
    }
