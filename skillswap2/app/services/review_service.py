# skillswap2/app/services/review_service.py
"""
Review Service Layer
Phase 4: Business logic for review submission and rating management
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime, UTC

from app.crud import review as review_crud
from app.models.review import Review, MentorRating


# ======================
# REVIEW SUBMISSION
# ======================

def submit_review(
    db: Session,
    session_id: int,
    learner_id: int,
    rating: int,
    comment: Optional[str] = None
) -> Dict[str, Any]:
    """
    Submit a review for a completed session.
    
    Validates eligibility, creates review, and updates mentor rating.
    
    Args:
        db: Database session
        session_id: Session identifier
        learner_id: Learner user ID
        rating: Rating value (1-5)
        comment: Optional text comment
        
    Returns:
        Dictionary with review details and status
        
    Raises:
        ValueError: If validation fails or rating is invalid
    """
    # Validate eligibility
    can_review, reason = review_crud.can_review_session(db, session_id, learner_id)
    if not can_review:
        raise ValueError(reason)
    
    # Validate rating range
    if not (1 <= rating <= 5):
        raise ValueError("Rating must be between 1 and 5")
    
    # Validate comment length if provided
    if comment and len(comment) > 1000:
        raise ValueError("Comment must be 1000 characters or less")
    
    # Get session to extract mentor_id
    from app.models.session import Session as SessionModel
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id
    ).first()
    
    if not session:
        raise ValueError("Session not found")
    
    try:
        # Create review
        review = review_crud.create_review(
            db=db,
            session_id=session_id,
            learner_id=learner_id,
            mentor_id=session.mentor_id,
            rating=rating,
            comment=comment
        )
        
        # Update mentor's average rating
        updated_rating = review_crud.update_mentor_rating(db, session.mentor_id)
        
        # Commit transaction
        db.commit()
        
        return {
            "review_id": review.id,
            "session_id": review.session_id,
            "rating": review.rating,
            "comment": review.comment,
            "created_at": review.created_at.isoformat() if review.created_at else None,
            "mentor_new_average": round(updated_rating.average_rating, 2),
            "mentor_total_reviews": updated_rating.total_reviews,
            "message": "Review submitted successfully"
        }
    
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to submit review: {str(e)}")


def update_review(
    db: Session,
    review_id: int,
    learner_id: int,
    rating: Optional[int] = None,
    comment: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing review.
    
    Args:
        db: Database session
        review_id: Review identifier
        learner_id: Learner user ID (for ownership validation)
        rating: New rating value (1-5)
        comment: New comment text
        
    Returns:
        Dictionary with updated review details
        
    Raises:
        ValueError: If validation fails
    """
    # Check ownership
    if not review_crud.is_review_owner(db, review_id, learner_id):
        raise ValueError("You can only update your own reviews")
    
    # Get existing review
    review = review_crud.get_review_by_id(db, review_id)
    if not review:
        raise ValueError("Review not found")
    
    # Validate rating if provided
    if rating is not None and not (1 <= rating <= 5):
        raise ValueError("Rating must be between 1 and 5")
    
    # Validate comment length if provided
    if comment is not None and len(comment) > 1000:
        raise ValueError("Comment must be 1000 characters or less")
    
    try:
        # Store old rating to check if it changed
        old_rating = review.rating
        
        # Update review
        updated_review = review_crud.update_review(
            db=db,
            review_id=review_id,
            rating=rating,
            comment=comment
        )
        
        # If rating changed, update mentor's average
        if rating is not None and rating != old_rating:
            review_crud.update_mentor_rating(db, review.mentor_id)
        
        db.commit()
        
        return {
            "review_id": updated_review.id,
            "rating": updated_review.rating,
            "comment": updated_review.comment,
            "updated_at": datetime.now(UTC).isoformat(),
            "message": "Review updated successfully"
        }
    
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to update review: {str(e)}")


def delete_review(
    db: Session,
    review_id: int,
    user_id: int,
    is_admin: bool = False
) -> Dict[str, Any]:
    """
    Delete a review.
    
    Args:
        db: Database session
        review_id: Review identifier
        user_id: User attempting deletion
        is_admin: Whether user is administrator
        
    Returns:
        Dictionary with deletion status
        
    Raises:
        ValueError: If validation fails
    """
    # Get review
    review = review_crud.get_review_by_id(db, review_id)
    if not review:
        raise ValueError("Review not found")
    
    # Check permission
    if not is_admin and review.learner_id != user_id:
        raise ValueError("You can only delete your own reviews")
    
    try:
        mentor_id = review.mentor_id
        
        # Delete review
        review_crud.delete_review(db, review_id)
        
        # Update mentor's average rating
        review_crud.update_mentor_rating(db, mentor_id)
        
        db.commit()
        
        return {
            "review_id": review_id,
            "message": "Review deleted successfully"
        }
    
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to delete review: {str(e)}")


# ======================
# REVIEW RETRIEVAL
# ======================

def get_mentor_reviews(
    db: Session,
    mentor_id: int,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get all reviews for a mentor with formatted output.
    
    Args:
        db: Database session
        mentor_id: Mentor user ID
        limit: Maximum reviews to return
        offset: Number of reviews to skip
        
    Returns:
        List of formatted review dictionaries
    """
    reviews = review_crud.get_reviews_by_mentor(db, mentor_id, limit, offset)
    
    return [
        {
            "review_id": r.id,
            "session_id": r.session_id,
            "learner_id": r.learner_id,
            "learner_name": r.learner.name if r.learner else "Unknown",
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in reviews
    ]


def get_mentor_rating_summary(db: Session, mentor_id: int) -> Dict[str, Any]:
    """
    Get comprehensive rating summary for a mentor.
    
    Args:
        db: Database session
        mentor_id: Mentor user ID
        
    Returns:
        Dictionary with rating statistics
    """
    # Get or create rating record
    mentor_rating = review_crud.get_or_create_mentor_rating(db, mentor_id)
    
    # Get rating distribution
    distribution = review_crud.get_rating_distribution(db, mentor_id)
    
    # Calculate percentages
    total = mentor_rating.total_reviews
    distribution_pct = {
        rating: (count / total * 100) if total > 0 else 0
        for rating, count in distribution.items()
    }
    
    return {
        "mentor_id": mentor_id,
        "average_rating": round(mentor_rating.average_rating, 2),
        "total_reviews": mentor_rating.total_reviews,
        "rating_distribution": distribution,
        "rating_distribution_percentage": {
            k: round(v, 1) for k, v in distribution_pct.items()
        },
        "updated_at": mentor_rating.updated_at.isoformat() if mentor_rating.updated_at else None
    }


def get_learner_reviews(
    db: Session,
    learner_id: int,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get all reviews given by a learner.
    
    Args:
        db: Database session
        learner_id: Learner user ID
        limit: Maximum reviews to return
        offset: Number of reviews to skip
        
    Returns:
        List of formatted review dictionaries
    """
    reviews = review_crud.get_reviews_by_learner(db, learner_id, limit, offset)
    
    return [
        {
            "review_id": r.id,
            "session_id": r.session_id,
            "mentor_id": r.mentor_id,
            "mentor_name": r.mentor.name if r.mentor else "Unknown",
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in reviews
    ]


def check_review_eligibility(
    db: Session,
    session_id: int,
    learner_id: int
) -> Dict[str, Any]:
    """
    Check if a learner can review a specific session.
    
    Args:
        db: Database session
        session_id: Session identifier
        learner_id: Learner user ID
        
    Returns:
        Dictionary with eligibility status and reason
    """
    can_review, reason = review_crud.can_review_session(db, session_id, learner_id)
    
    return {
        "can_review": can_review,
        "reason": reason,
        "session_id": session_id
    }


# ======================
# ADMIN OPERATIONS
# ======================

def get_all_reviews(
    db: Session,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get all reviews in the system (admin only).
    
    Args:
        db: Database session
        limit: Maximum reviews to return
        offset: Number of reviews to skip
        
    Returns:
        List of all reviews with full details
    """
    reviews = db.query(Review).order_by(
        Review.created_at.desc()
    ).limit(limit).offset(offset).all()
    
    return [
        {
            "review_id": r.id,
            "session_id": r.session_id,
            "learner_id": r.learner_id,
            "learner_name": r.learner.name if r.learner else "Unknown",
            "mentor_id": r.mentor_id,
            "mentor_name": r.mentor.name if r.mentor else "Unknown",
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in reviews
    ]


def recalculate_all_ratings(db: Session) -> Dict[str, Any]:
    """
    Recalculate all mentor ratings (admin maintenance).
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with recalculation statistics
    """
    # Get all mentors who have received reviews
    mentors_with_reviews = db.query(Review.mentor_id).distinct().all()
    mentor_ids = [m[0] for m in mentors_with_reviews]
    
    updated_count = 0
    errors = []
    
    for mentor_id in mentor_ids:
        try:
            review_crud.update_mentor_rating(db, mentor_id)
            updated_count += 1
        except Exception as e:
            errors.append(f"Mentor {mentor_id}: {str(e)}")
    
    db.commit()
    
    return {
        "total_mentors": len(mentor_ids),
        "updated_count": updated_count,
        "errors": errors,
        "message": "Rating recalculation complete"
    }
