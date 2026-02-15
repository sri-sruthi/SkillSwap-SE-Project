# skillswap2/tests/test_phase4_reviews.py
"""
Phase 4: Ratings & Review Core Logic Tests
Complete end-to-end testing of review CRUD and service layer
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, UTC

from app.database import Base
from app.models.user import User
from app.models.session import Session
from app.models.review import Review, MentorRating
from app.crud import review as review_crud
from app.services import review_service


# ======================
# TEST DATABASE SETUP
# ======================

@pytest.fixture
def db_session():
    """Create test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def setup_users(db_session):
    """Create test users"""
    learner = User(
        id=1,
        name="Test Learner",
        email="learner@test.com",
        password_hash="hash",
        role="student"
    )
    
    mentor = User(
        id=2,
        name="Test Mentor",
        email="mentor@test.com",
        password_hash="hash",
        role="student"
    )
    
    db_session.add(learner)
    db_session.add(mentor)
    db_session.commit()
    
    return {"learner": learner, "mentor": mentor}


@pytest.fixture
def setup_completed_session(db_session, setup_users):
    """Create a completed session"""
    session = Session(
        id=1,
        learner_id=1,
        mentor_id=2,
        skill_id=1,
        scheduled_time=datetime.now(UTC),
        status="Completed"
    )
    
    db_session.add(session)
    db_session.commit()
    
    return session


# ======================
# TEST 1: REVIEW CREATION
# ======================

def test_create_review_success(db_session, setup_completed_session):
    """Test successful review creation"""
    
    review = review_crud.create_review(
        db=db_session,
        session_id=1,
        learner_id=1,
        mentor_id=2,
        rating=5,
        comment="Excellent mentor!"
    )
    
    assert review.id is not None
    assert review.session_id == 1
    assert review.rating == 5
    assert review.comment == "Excellent mentor!"
    assert review.learner_id == 1
    assert review.mentor_id == 2


def test_create_review_invalid_rating(db_session, setup_completed_session):
    """Test review creation with invalid rating"""
    
    with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
        review_crud.create_review(
            db=db_session,
            session_id=1,
            learner_id=1,
            mentor_id=2,
            rating=6,  # Invalid
            comment="Test"
        )


def test_create_review_no_comment(db_session, setup_completed_session):
    """Test review creation without comment"""
    
    review = review_crud.create_review(
        db=db_session,
        session_id=1,
        learner_id=1,
        mentor_id=2,
        rating=4
    )
    
    assert review.comment is None


# ======================
# TEST 2: DUPLICATE REVIEW PREVENTION
# ======================

def test_duplicate_review_prevented(db_session, setup_completed_session):
    """Test that duplicate reviews for same session are prevented"""
    
    # Create first review
    review_crud.create_review(
        db=db_session,
        session_id=1,
        learner_id=1,
        mentor_id=2,
        rating=5
    )
    db_session.commit()
    
    # Try to create second review (should be prevented by DB unique constraint)
    from sqlalchemy.exc import IntegrityError
    
    with pytest.raises(IntegrityError):
        review_crud.create_review(
            db=db_session,
            session_id=1,
            learner_id=1,
            mentor_id=2,
            rating=4
        )
        db_session.commit()


# ======================
# TEST 3: REVIEW ELIGIBILITY
# ======================

def test_can_review_completed_session(db_session, setup_completed_session):
    """Test eligibility check for completed session"""
    
    can_review, reason = review_crud.can_review_session(
        db=db_session,
        session_id=1,
        user_id=1  # Learner
    )
    
    assert can_review is True
    assert reason == "Can review"


def test_cannot_review_non_completed(db_session, setup_users):
    """Test that pending sessions cannot be reviewed"""
    
    # Create pending session
    session = Session(
        id=2,
        learner_id=1,
        mentor_id=2,
        skill_id=1,
        scheduled_time=datetime.now(UTC),
        status="Pending"
    )
    db_session.add(session)
    db_session.commit()
    
    can_review, reason = review_crud.can_review_session(
        db=db_session,
        session_id=2,
        user_id=1
    )
    
    assert can_review is False
    assert "completed" in reason.lower()


def test_mentor_cannot_review(db_session, setup_completed_session):
    """Test that mentors cannot review their own sessions"""
    
    can_review, reason = review_crud.can_review_session(
        db=db_session,
        session_id=1,
        user_id=2  # Mentor trying to review
    )
    
    assert can_review is False
    assert "learner" in reason.lower()


# ======================
# TEST 4: RATING CALCULATION
# ======================

def test_mentor_rating_calculation(db_session, setup_completed_session, setup_users):
    """Test average rating calculation"""
    
    # Create multiple completed sessions
    for i in range(2, 6):
        session = Session(
            id=i,
            learner_id=1,
            mentor_id=2,
            skill_id=1,
            scheduled_time=datetime.now(UTC),
            status="Completed"
        )
        db_session.add(session)
    db_session.commit()
    
    # Create reviews with different ratings
    ratings = [5, 4, 5, 3, 4]  # Average should be 4.2
    
    for i, rating in enumerate(ratings, start=1):
        review_crud.create_review(
            db=db_session,
            session_id=i,
            learner_id=1,
            mentor_id=2,
            rating=rating
        )
    db_session.commit()
    
    # Calculate rating
    avg_rating, total = review_crud.calculate_mentor_rating(db_session, mentor_id=2)
    
    assert total == 5
    assert round(avg_rating, 1) == 4.2


def test_mentor_rating_update(db_session, setup_completed_session):
    """Test automatic mentor rating update"""
    
    # Create review
    review_crud.create_review(
        db=db_session,
        session_id=1,
        learner_id=1,
        mentor_id=2,
        rating=5
    )
    
    # Update mentor rating
    mentor_rating = review_crud.update_mentor_rating(db_session, mentor_id=2)
    
    assert mentor_rating.average_rating == 5.0
    assert mentor_rating.total_reviews == 1


# ======================
# TEST 5: RATING DISTRIBUTION
# ======================

def test_rating_distribution(db_session, setup_users):
    """Test rating distribution calculation"""
    
    # Create sessions and reviews with varied ratings
    ratings = [5, 5, 4, 4, 4, 3, 3, 2, 1]
    
    for i, rating in enumerate(ratings, start=1):
        session = Session(
            id=i,
            learner_id=1,
            mentor_id=2,
            skill_id=1,
            scheduled_time=datetime.now(UTC),
            status="Completed"
        )
        db_session.add(session)
        db_session.flush()
        
        review_crud.create_review(
            db=db_session,
            session_id=i,
            learner_id=1,
            mentor_id=2,
            rating=rating
        )
    
    db_session.commit()
    
    # Get distribution
    distribution = review_crud.get_rating_distribution(db_session, mentor_id=2)
    
    assert distribution[5] == 2
    assert distribution[4] == 3
    assert distribution[3] == 2
    assert distribution[2] == 1
    assert distribution[1] == 1


# ======================
# TEST 6: SERVICE LAYER
# ======================

def test_submit_review_service(db_session, setup_completed_session):
    """Test review submission through service layer"""
    
    result = review_service.submit_review(
        db=db_session,
        session_id=1,
        learner_id=1,
        rating=5,
        comment="Great session!"
    )
    
    assert result["review_id"] is not None
    assert result["rating"] == 5
    assert result["mentor_new_average"] == 5.0
    assert result["mentor_total_reviews"] == 1
    assert "successfully" in result["message"].lower()


def test_submit_review_ineligible(db_session, setup_users):
    """Test review submission for ineligible session"""
    
    # Create non-completed session
    session = Session(
        id=2,
        learner_id=1,
        mentor_id=2,
        skill_id=1,
        scheduled_time=datetime.now(UTC),
        status="Confirmed"  # Not completed
    )
    db_session.add(session)
    db_session.commit()
    
    with pytest.raises(ValueError, match="completed"):
        review_service.submit_review(
            db=db_session,
            session_id=2,
            learner_id=1,
            rating=5
        )


def test_get_mentor_rating_summary(db_session, setup_users):
    """Test mentor rating summary retrieval"""
    
    # Create sessions and reviews
    for i in range(1, 4):
        session = Session(
            id=i,
            learner_id=1,
            mentor_id=2,
            skill_id=1,
            scheduled_time=datetime.now(UTC),
            status="Completed"
        )
        db_session.add(session)
        db_session.flush()
        
        review_crud.create_review(
            db=db_session,
            session_id=i,
            learner_id=1,
            mentor_id=2,
            rating=5 - i + 1  # Ratings: 5, 4, 3
        )
    
    db_session.commit()
    review_crud.update_mentor_rating(db_session, mentor_id=2)
    
    # Get summary
    summary = review_service.get_mentor_rating_summary(db_session, mentor_id=2)
    
    assert summary["total_reviews"] == 3
    assert summary["average_rating"] == 4.0  # (5+4+3)/3
    assert summary["rating_distribution"][5] == 1
    assert summary["rating_distribution"][4] == 1
    assert summary["rating_distribution"][3] == 1


# ======================
# TEST 7: REVIEW UPDATE
# ======================

def test_update_review(db_session, setup_completed_session):
    """Test review update"""
    
    # Create review
    review = review_crud.create_review(
        db=db_session,
        session_id=1,
        learner_id=1,
        mentor_id=2,
        rating=3,
        comment="OK"
    )
    db_session.commit()
    
    # Update review
    result = review_service.update_review(
        db=db_session,
        review_id=review.id,
        learner_id=1,
        rating=5,
        comment="Actually excellent!"
    )
    
    assert result["rating"] == 5
    assert "successfully" in result["message"].lower()


def test_update_review_unauthorized(db_session, setup_completed_session, setup_users):
    """Test unauthorized review update"""
    
    # Create review
    review = review_crud.create_review(
        db=db_session,
        session_id=1,
        learner_id=1,
        mentor_id=2,
        rating=5
    )
    db_session.commit()
    
    # Try to update as different user
    with pytest.raises(ValueError, match="own reviews"):
        review_service.update_review(
            db=db_session,
            review_id=review.id,
            learner_id=999,  # Different user
            rating=3
        )


# ======================
# TEST 8: REVIEW DELETION
# ======================

def test_delete_review(db_session, setup_completed_session):
    """Test review deletion"""
    
    # Create review
    review = review_crud.create_review(
        db=db_session,
        session_id=1,
        learner_id=1,
        mentor_id=2,
        rating=5
    )
    db_session.commit()
    
    # Delete review
    result = review_service.delete_review(
        db=db_session,
        review_id=review.id,
        user_id=1
    )
    
    assert "successfully" in result["message"].lower()
    
    # Verify deletion
    deleted_review = review_crud.get_review_by_id(db_session, review.id)
    assert deleted_review is None


# ======================
# TEST 9: COMMENT VALIDATION
# ======================

def test_long_comment_rejected(db_session, setup_completed_session):
    """Test that overly long comments are rejected"""
    
    long_comment = "x" * 1001  # Over 1000 character limit
    
    with pytest.raises(ValueError, match="1000 characters"):
        review_service.submit_review(
            db=db_session,
            session_id=1,
            learner_id=1,
            rating=5,
            comment=long_comment
        )


# ======================
# TEST 10: MENTOR WITH NO REVIEWS
# ======================

def test_mentor_no_reviews(db_session, setup_users):
    """Test rating summary for mentor with no reviews"""
    
    summary = review_service.get_mentor_rating_summary(db_session, mentor_id=2)
    
    assert summary["total_reviews"] == 0
    assert summary["average_rating"] == 0.0
    assert all(count == 0 for count in summary["rating_distribution"].values())


# ======================
# RUN TESTS
# ======================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
