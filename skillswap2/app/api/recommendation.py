# skillswap2/app/api/recommendation.py
"""
Recommendation API Router
Phase 6: ML-based mentor recommendation endpoints

Endpoints:
- GET /recommend - Get personalized mentor recommendations
- GET /recommend/by-skill/{skill_id} - Get recommendations for specific skill
- POST /recommend/refresh - Refresh recommendations (retrain)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.user import User
from app.schemas.recommendation import (
    RecommendationResponse,
    RecommendationRequest,
    RecommendationExplanation,
    MentorTeachingSkill,
)
from app.ml.recommender import RecommendationEngine, get_global_engine
from app.utils.security import get_current_user

router = APIRouter(prefix="/recommend", tags=["recommendations"])
TEACH_SKILL_TYPES = ("teach", "offer")


def _get_mentor_teaching_skills(db: Session, mentor_id: int) -> list[MentorTeachingSkill]:
    """Return mentor teaching skills for booking-session dropdowns."""
    from app.models.skill import Skill, UserSkill

    # Support codebases where skill label column is `title` (current) or `name` (legacy).
    skill_label_col = getattr(Skill, "title", None) or getattr(Skill, "name")

    rows = (
        db.query(Skill.id, skill_label_col.label("label"))
        .join(UserSkill, UserSkill.skill_id == Skill.id)
        .filter(
            UserSkill.user_id == mentor_id,
            UserSkill.skill_type.in_(TEACH_SKILL_TYPES),
        )
        .order_by(skill_label_col.asc(), Skill.id.asc())
        .all()
    )

    seen: set[int] = set()
    teaching_skills: list[MentorTeachingSkill] = []
    for row in rows:
        if row.id in seen:
            continue
        seen.add(row.id)
        teaching_skills.append(MentorTeachingSkill(id=row.id, name=row.label))

    return teaching_skills


# ======================
# GET RECOMMENDATIONS
# ======================
@router.get("/", response_model=List[RecommendationResponse])
def get_recommendations(
    top_n: int = Query(5, ge=1, le=10, description="Number of recommendations (1-10)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized mentor recommendations for current user.
    
    Uses ML-based matching:
    - Skill similarity (TF-IDF + cosine similarity)
    - Mentor rating
    - Mentor activity level
    
    Query Parameters:
        top_n: Number of recommendations to return (default 5, max 10)
        
    Returns:
        List of top-N mentor recommendations ranked by compatibility
    """
    try:
        # Get recommendation engine
        engine = get_global_engine(db)
        
        # Generate recommendations
        recommendations = engine.recommend_mentors(
            db=db,
            learner_id=current_user.id,
            top_n=top_n
        )
        
        if not recommendations:
            return []
        
        # Optionally save recommendations to database
        # engine.save_recommendations(db, current_user.id, recommendations)
        
        # Format response
        return [
            RecommendationResponse(
                mentor_id=rec['mentor_id'],
                mentor_name=rec['mentor_name'],
                similarity_score=round(rec['similarity_score'], 3),
                rating=rec['rating'],
                compatibility_score=round(rec['compatibility_score'], 3),
                rank=rec['rank'],
                total_reviews=rec['total_reviews'],
                mentor_teaching_skills=_get_mentor_teaching_skills(db, rec['mentor_id']),
                explanation=engine.explain_recommendation(
                    rec['similarity_score'],
                    rec['rating'],
                    rec['activity_score'],
                    rec['compatibility_score']
                )
            )
            for rec in recommendations
        ]
    
    except ValueError as e:
        # Likely no skills specified by learner
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


# ======================
# GET RECOMMENDATIONS BY SKILL
# ======================
@router.get("/by-skill/{skill_id}", response_model=List[RecommendationResponse])
def get_recommendations_by_skill(
    skill_id: int,
    top_n: int = Query(5, ge=1, le=10, description="Number of recommendations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get mentor recommendations for a specific skill.
    
    Filters mentors who offer the specified skill, then ranks by compatibility.
    
    Path Parameters:
        skill_id: Skill identifier
        
    Query Parameters:
        top_n: Number of recommendations to return
        
    Returns:
        List of mentors who teach the specified skill, ranked by quality
    """
    try:
        # Verify skill exists
        from app.models.skill import Skill
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            raise HTTPException(
                status_code=404,
                detail=f"Skill {skill_id} not found"
            )
        
        # Get recommendation engine
        engine = get_global_engine(db)
        
        # Generate recommendations filtered by skill
        recommendations = engine.recommend_mentors(
            db=db,
            learner_id=current_user.id,
            top_n=top_n,
            skill_filter=skill_id
        )
        
        if not recommendations:
            return []
        
        # Format response
        return [
            RecommendationResponse(
                mentor_id=rec['mentor_id'],
                mentor_name=rec['mentor_name'],
                similarity_score=round(rec['similarity_score'], 3),
                rating=rec['rating'],
                compatibility_score=round(rec['compatibility_score'], 3),
                rank=rec['rank'],
                total_reviews=rec['total_reviews'],
                mentor_teaching_skills=_get_mentor_teaching_skills(db, rec['mentor_id']),
                explanation=engine.explain_recommendation(
                    rec['similarity_score'],
                    rec['rating'],
                    rec['activity_score'],
                    rec['compatibility_score']
                )
            )
            for rec in recommendations
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


# ======================
# REFRESH RECOMMENDATIONS (RETRAIN)
# ======================
@router.post("/refresh")
def refresh_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Refresh recommendation model (retrain on current data).
    
    Use this after:
    - Adding many new skills
    - Significant changes to skill descriptions
    - Database migrations
    
    Note: In production, this would be rate-limited and possibly admin-only.
    
    Returns:
        Status message with vocabulary size
    """
    try:
        engine = RecommendationEngine()
        engine.train(db)
        
        vocab_size = engine.vectorizer.get_vocabulary_size()
        
        return {
            "message": "Recommendation model refreshed successfully",
            "vocabulary_size": vocab_size,
            "status": "ready"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh recommendations: {str(e)}"
        )


# ======================
# GET RECOMMENDATION EXPLANATION
# ======================
@router.get("/explain/{mentor_id}", response_model=RecommendationExplanation)
def explain_recommendation(
    mentor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed explanation for why a mentor was recommended.
    
    Path Parameters:
        mentor_id: Mentor user ID
        
    Returns:
        Detailed breakdown of compatibility factors
    """
    try:
        from app.ml.vectorizer import SkillVectorizer
        from app.crud import review as review_crud
        
        # Verify mentor exists
        mentor = db.query(User).filter(User.id == mentor_id).first()
        if not mentor:
            raise HTTPException(
                status_code=404,
                detail="Mentor not found"
            )
        
        # Get engine
        engine = get_global_engine(db)
        
        # Calculate components
        learner_vector = engine.get_user_skill_vector(db, current_user.id, "learn")
        mentor_vector = engine.get_user_skill_vector(db, mentor_id, "teach")
        
        if learner_vector.sum() == 0:
            raise HTTPException(
                status_code=400,
                detail="Add learning skills first to get recommendations"
            )
        
        if mentor_vector.sum() == 0:
            raise HTTPException(
                status_code=400,
                detail="This mentor has not specified any teaching skills"
            )
        
        # Calculate similarity
        similarity = engine.vectorizer.compute_similarity(
            learner_vector.reshape(1, -1),
            mentor_vector.reshape(1, -1)
        )[0, 0]
        
        # Get rating
        mentor_rating = review_crud.get_mentor_rating(db, mentor_id)
        rating = mentor_rating.average_rating if mentor_rating else None
        
        # Get activity
        activity = engine.calculate_activity_score(db, mentor_id)
        
        # Calculate compatibility
        compatibility = engine.calculate_compatibility_score(similarity, rating, activity)
        
        return RecommendationExplanation(
            mentor_id=mentor_id,
            mentor_name=mentor.name,
            similarity_score=round(float(similarity), 3),
            rating_score=round(float(rating), 2) if rating else None,
            activity_score=round(float(activity), 3),
            compatibility_score=round(float(compatibility), 3),
            weight_similarity=engine.WEIGHT_SIMILARITY,
            weight_rating=engine.WEIGHT_RATING,
            weight_activity=engine.WEIGHT_ACTIVITY,
            explanation=engine.explain_recommendation(similarity, rating, activity, compatibility)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to explain recommendation: {str(e)}"
        )


# ======================
# HEALTH CHECK
# ======================
@router.get("/health")
def recommendation_health(db: Session = Depends(get_db)):
    """
    Health check for recommendation service.
    
    Returns:
        Service status and readiness
    """
    try:
        engine = RecommendationEngine()
        engine.train(db)
        
        return {
            "service": "recommendation",
            "status": "operational",
            "model_ready": engine.is_ready,
            "vocabulary_size": engine.vectorizer.get_vocabulary_size()
        }
    except Exception as e:
        return {
            "service": "recommendation",
            "status": "error",
            "error": str(e)
        }
