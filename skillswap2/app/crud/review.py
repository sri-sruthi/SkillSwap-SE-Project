# skillswap2/app/crud/review.py
"""
Review CRUD Operations
Phase 4: Core database operations for ratings and reviews
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime, UTC

from app.models.review import Review, MentorRating
from app.models.session import Session as SessionModel
from app.models.user import User


# ======================
# REVIEW CRUD
# ======================

def create_review(
    db: Session,
    session_id: int,
    learner_id: int,
    mentor_id: int,
    rating: int,
    comment: Optional[str] = None
) -> Review:
    """
    Create a new review for a completed session.
    
    Args:
        db: Database session
        session_id: Session identifier
        learner_id: Learner user ID
        mentor_id: Mentor user ID
        rating: Rating value (1-5)
        comment: Optional text comment
        
    Returns:
        Created Review object
        
    Raises:
        ValueError: If rating is out of range
    """
    if not (1 <= rating <= 5):
        raise ValueError("Rating must be between 1 and 5")
    
    review = Review(
        session_id=session_id,
        learner_id=learner_id,
        mentor_id=mentor_id,
        rating=rating,
        comment=comment
    )
    
    db.add(review)
    db.flush()
    return review


def get_review_by_id(db: Session, review_id: int) -> Optional[Review]:
    """
    Get a review by its ID.
    
    Args:
        db: Database session
        review_id: Review identifier
        
    Returns:
        Review object or None if not found
    """
    return db.query(Review).filter(Review.id == review_id).first()


def get_review_by_session(db: Session, session_id: int) -> Optional[Review]:
    """
    Get review for a specific session.
    
    Args:
        db: Database session
        session_id: Session identifier
        
    Returns:
        Review object or None if no review exists for this session
    """
    return db.query(Review).filter(Review.session_id == session_id).first()


def get_reviews_by_mentor(
    db: Session,
    mentor_id: int,
    limit: int = 50,
    offset: int = 0
) -> List[Review]:
    """
    Get all reviews for a mentor.
    
    Args:
        db: Database session
        mentor_id: Mentor user ID
        limit: Maximum reviews to return
        offset: Number of reviews to skip
        
    Returns:
        List of Review objects
    """
    return (
        db.query(Review)
        .filter(Review.mentor_id == mentor_id)
        .order_by(Review.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def get_reviews_by_learner(
    db: Session,
    learner_id: int,
    limit: int = 50,
    offset: int = 0
) -> List[Review]:
    """
    Get all reviews given by a learner.
    
    Args:
        db: Database session
        learner_id: Learner user ID
        limit: Maximum reviews to return
        offset: Number of reviews to skip
        
    Returns:
        List of Review objects
    """
    return (
        db.query(Review)
        .filter(Review.learner_id == learner_id)
        .order_by(Review.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def update_review(
    db: Session,
    review_id: int,
    rating: Optional[int] = None,
    comment: Optional[str] = None
) -> Optional[Review]:
    """
    Update an existing review.
    
    Args:
        db: Database session
        review_id: Review identifier
        rating: New rating value (1-5)
        comment: New comment text
        
    Returns:
        Updated Review object or None if not found
        
    Raises:
        ValueError: If rating is out of range
    """
    review = get_review_by_id(db, review_id)
    if not review:
        return None
    
    if rating is not None:
        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5")
        review.rating = rating
    
    if comment is not None:
        review.comment = comment
    
    db.flush()
    return review


def delete_review(db: Session, review_id: int) -> bool:
    """
    Delete a review.
    
    Args:
        db: Database session
        review_id: Review identifier
        
    Returns:
        True if deleted, False if not found
    """
    review = get_review_by_id(db, review_id)
    if not review:
        return False
    
    db.delete(review)
    db.flush()
    return True


# ======================
# MENTOR RATING CRUD
# ======================

def get_or_create_mentor_rating(db: Session, mentor_id: int) -> MentorRating:
    """
    Get or create mentor rating record.
    
    Args:
        db: Database session
        mentor_id: Mentor user ID
        
    Returns:
        MentorRating object
    """
    rating = db.query(MentorRating).filter(
        MentorRating.mentor_id == mentor_id
    ).first()
    
    if not rating:
        rating = MentorRating(
            mentor_id=mentor_id,
            average_rating=0.0,
            total_reviews=0
        )
        db.add(rating)
        db.flush()
    
    return rating


def calculate_mentor_rating(db: Session, mentor_id: int) -> tuple[float, int]:
    """
    Calculate average rating and total reviews for a mentor.
    
    Args:
        db: Database session
        mentor_id: Mentor user ID
        
    Returns:
        Tuple of (average_rating, total_reviews)
    """
    result = db.query(
        func.avg(Review.rating).label('avg_rating'),
        func.count(Review.id).label('total')
    ).filter(
        Review.mentor_id == mentor_id
    ).first()
    
    avg_rating = float(result.avg_rating) if result.avg_rating else 0.0
    total = int(result.total) if result.total else 0
    
    return (avg_rating, total)


def update_mentor_rating(db: Session, mentor_id: int) -> MentorRating:
    """
    Recalculate and update mentor's average rating.
    
    Args:
        db: Database session
        mentor_id: Mentor user ID
        
    Returns:
        Updated MentorRating object
    """
    mentor_rating = get_or_create_mentor_rating(db, mentor_id)
    avg_rating, total = calculate_mentor_rating(db, mentor_id)
    
    mentor_rating.average_rating = avg_rating
    mentor_rating.total_reviews = total
    mentor_rating.updated_at = datetime.now(UTC)
    
    db.flush()
    return mentor_rating


def get_mentor_rating(db: Session, mentor_id: int) -> Optional[MentorRating]:
    """
    Get mentor rating record.
    
    Args:
        db: Database session
        mentor_id: Mentor user ID
        
    Returns:
        MentorRating object or None if not found
    """
    return db.query(MentorRating).filter(
        MentorRating.mentor_id == mentor_id
    ).first()


def get_rating_distribution(db: Session, mentor_id: int) -> dict:
    """
    Get distribution of ratings for a mentor.
    
    Args:
        db: Database session
        mentor_id: Mentor user ID
        
    Returns:
        Dictionary with rating counts: {1: count, 2: count, ...}
    """
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    
    results = db.query(
        Review.rating,
        func.count(Review.id).label('count')
    ).filter(
        Review.mentor_id == mentor_id
    ).group_by(
        Review.rating
    ).all()
    
    for rating, count in results:
        distribution[rating] = count
    
    return distribution


# ======================
# VALIDATION HELPERS
# ======================

def can_review_session(
    db: Session,
    session_id: int,
    user_id: int
) -> tuple[bool, str]:
    """
    Check if a user can review a session.
    
    Args:
        db: Database session
        session_id: Session identifier
        user_id: User attempting to review
        
    Returns:
        Tuple of (can_review: bool, reason: str)
    """
    # Get session
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id
    ).first()
    
    if not session:
        return (False, "Session not found")
    
    # Must be the learner participant for this session
    if session.learner_id != user_id:
        return (False, "Only the learner in this session can submit a review")
    
    # Session must be completed
    if session.status != "Completed":
        return (False, "Only completed sessions can be reviewed")
    
    # Check if review already exists
    existing_review = get_review_by_session(db, session_id)
    if existing_review:
        return (False, "Review already submitted for this session")
    
    return (True, "Can review")


def is_review_owner(db: Session, review_id: int, user_id: int) -> bool:
    """
    Check if user is the owner of a review.
    
    Args:
        db: Database session
        review_id: Review identifier
        user_id: User ID to check
        
    Returns:
        True if user is the learner who created the review
    """
    review = get_review_by_id(db, review_id)
    if not review:
        return False
    
    return review.learner_id == user_id
