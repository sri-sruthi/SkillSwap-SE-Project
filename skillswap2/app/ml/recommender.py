# skillswap2/app/ml/recommender.py
"""
Recommendation Engine
Phase 6: ML-based mentor matching using skill similarity and quality signals
"""

import numpy as np
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from app.ml.vectorizer import SkillVectorizer, aggregate_skill_vectors
from app.models.user import User
from app.models.skill import UserSkill, Skill
from app.models.review import MentorRating
from app.crud import review as review_crud


class RecommendationEngine:
    """
    ML-based recommendation engine for mentor matching.
    
    Uses skill similarity (TF-IDF + cosine similarity) combined with
    quality signals (ratings, activity) to rank mentors.
    """
    
    # Compatibility score weights
    WEIGHT_SIMILARITY = 0.5
    WEIGHT_RATING = 0.3
    WEIGHT_ACTIVITY = 0.2
    
    # Minimum rating for new mentors (no reviews yet)
    DEFAULT_RATING = 3.5

    # Support both legacy and new skill_type naming.
    # learner side: need/learn
    # mentor side: offer/teach
    SKILL_TYPE_ALIASES = {
        "need": ("need", "learn"),
        "learn": ("need", "learn"),
        "offer": ("offer", "teach"),
        "teach": ("offer", "teach"),
    }
    
    def __init__(self):
        """Initialize recommendation engine"""
        self.vectorizer = SkillVectorizer()
        self.is_ready = False

    def _resolve_skill_types(self, skill_type: str) -> Tuple[str, ...]:
        """Resolve a requested skill type into accepted DB aliases."""
        key = (skill_type or "").strip().lower()
        return self.SKILL_TYPE_ALIASES.get(key, (key,))
        
    def train(self, db: Session):
        """
        Train the vectorizer on all skills in the database.
        
        Args:
            db: Database session
        """
        # Get all skills
        skills = db.query(Skill).all()
        
        if not skills or len(skills) == 0:
            raise ValueError("No skills found in database for training")
        
        # Extract descriptions
        descriptions = []
        for skill in skills:
            desc = f"{skill.title} {skill.description or ''} {skill.category or ''}"
            descriptions.append(desc)
        
        # Fit vectorizer
        self.vectorizer.fit(descriptions)
        self.is_ready = True
        
    def get_user_skill_vector(
        self,
        db: Session,
        user_id: int,
        skill_type: str = 'offer'
    ) -> np.ndarray:
        """
        Get aggregated skill vector for a user.
        
        Args:
            db: Database session
            user_id: User ID
            skill_type: 'offer' for skills taught, 'need' for skills wanted
            
        Returns:
            Aggregated skill vector
        """
        if not self.is_ready:
            raise ValueError("Vectorizer not trained. Call train() first.")
        
        accepted_types = self._resolve_skill_types(skill_type)

        # Get user skills
        user_skills = db.query(UserSkill).filter(
            UserSkill.user_id == user_id,
            UserSkill.skill_type.in_(accepted_types)
        ).all()
        
        if not user_skills:
            return np.zeros(self.vectorizer.get_vocabulary_size())
        
        # Get skill vectors
        vectors = []
        for user_skill in user_skills:
            skill = user_skill.skill
            if skill:
                desc = f"{skill.title} {skill.description or ''} {skill.category or ''}"
                vector = self.vectorizer.transform([desc])[0]
                vectors.append(vector)
        
        if not vectors:
            return np.zeros(self.vectorizer.get_vocabulary_size())
        
        # Aggregate vectors
        return aggregate_skill_vectors(vectors, method='mean')
    
    def calculate_compatibility_score(
        self,
        similarity_score: float,
        rating: Optional[float],
        activity_score: float
    ) -> float:
        """
        Calculate weighted compatibility score.
        
        Args:
            similarity_score: Skill similarity (0-1)
            rating: Mentor rating (0-5), None for new mentors
            activity_score: Activity level (0-1)
            
        Returns:
            Compatibility score (0-1)
        """
        # Normalize rating to 0-1 scale
        if rating is None:
            normalized_rating = self.DEFAULT_RATING / 5.0
        else:
            normalized_rating = rating / 5.0
        
        # Weighted sum
        compatibility = (
            self.WEIGHT_SIMILARITY * similarity_score +
            self.WEIGHT_RATING * normalized_rating +
            self.WEIGHT_ACTIVITY * activity_score
        )
        
        return min(max(compatibility, 0.0), 1.0)
    
    def calculate_activity_score(self, db: Session, mentor_id: int) -> float:
        """
        Calculate mentor activity score based on session history.
        
        Args:
            db: Database session
            mentor_id: Mentor user ID
            
        Returns:
            Activity score (0-1)
        """
        from app.models.session import Session as SessionModel
        
        # Count completed sessions in last 90 days
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        
        recent_sessions = db.query(SessionModel).filter(
            SessionModel.mentor_id == mentor_id,
            SessionModel.status == 'Completed',
            SessionModel.created_at >= ninety_days_ago
        ).count()
        
        # Score based on session count (saturates at 10 sessions)
        activity_score = min(recent_sessions / 10.0, 1.0)
        
        return activity_score
    
    def recommend_mentors(
        self,
        db: Session,
        learner_id: int,
        top_n: int = 5,
        skill_filter: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate top-N mentor recommendations for a learner.
        
        Args:
            db: Database session
            learner_id: Learner user ID
            top_n: Number of recommendations to return (default 5)
            skill_filter: Optional skill ID to filter mentors
            
        Returns:
            List of recommendation dictionaries with mentor details
        """
        if not self.is_ready:
            raise ValueError("Vectorizer not trained. Call train() first.")
        
        # Get learner skill vector (skills they want to learn)
        learner_vector = self.get_user_skill_vector(db, learner_id, skill_type='need')
        
        if learner_vector.sum() == 0:
            # Learner has no skills specified
            return []
        
        # Get all potential mentors (users with offered skills)
        mentor_query = db.query(User).filter(
            User.id != learner_id,  # Exclude self
            User.is_active == True
        )
        
        mentor_skill_types = self._resolve_skill_types("offer")

        # Filter by skill if specified
        if skill_filter:
            mentor_query = mentor_query.join(UserSkill).filter(
                UserSkill.skill_id == skill_filter,
                UserSkill.skill_type.in_(mentor_skill_types),
            ).distinct()
        
        mentors = mentor_query.all()
        
        if not mentors:
            return []
        
        # Calculate recommendations
        recommendations = []
        
        for mentor in mentors:
            # Get mentor skill vector (skills they offer)
            mentor_vector = self.get_user_skill_vector(db, mentor.id, skill_type='offer')
            
            if mentor_vector.sum() == 0:
                continue
            
            # Calculate similarity
            similarity = self.vectorizer.compute_similarity(
                learner_vector.reshape(1, -1),
                mentor_vector.reshape(1, -1)
            )[0, 0]
            
            # Get mentor rating
            mentor_rating_obj = review_crud.get_mentor_rating(db, mentor.id)
            rating = mentor_rating_obj.average_rating if mentor_rating_obj else None
            
            # Calculate activity score
            activity = self.calculate_activity_score(db, mentor.id)
            
            # Calculate compatibility score
            compatibility = self.calculate_compatibility_score(
                similarity,
                rating,
                activity
            )
            
            recommendations.append({
                'mentor_id': mentor.id,
                'mentor_name': mentor.name,
                'mentor_email': mentor.email,
                'similarity_score': float(similarity),
                'rating': float(rating) if rating else None,
                'activity_score': float(activity),
                'compatibility_score': float(compatibility),
                'total_reviews': mentor_rating_obj.total_reviews if mentor_rating_obj else 0
            })
        
        # Sort by compatibility score (descending)
        recommendations.sort(key=lambda x: x['compatibility_score'], reverse=True)
        
        # Add rank
        for i, rec in enumerate(recommendations[:top_n], start=1):
            rec['rank'] = i
        
        return recommendations[:top_n]
    
    def save_recommendations(
        self,
        db: Session,
        learner_id: int,
        recommendations: List[Dict[str, Any]],
        skill_id: Optional[int] = None
    ):
        """
        Save recommendations to database for tracking.
        
        Args:
            db: Database session
            learner_id: Learner user ID
            recommendations: List of recommendation dictionaries
            skill_id: Optional skill ID for filtering
        """
        from app.models.recommendation import Recommendation
        
        for rec in recommendations:
            recommendation = Recommendation(
                learner_id=learner_id,
                mentor_id=rec['mentor_id'],
                skill_id=skill_id,
                similarity_score=rec['similarity_score'],
                compatibility_score=rec['compatibility_score'],
                rank=rec['rank']
            )
            db.add(recommendation)
        
        db.commit()
    
    def explain_recommendation(
        self,
        similarity: float,
        rating: Optional[float],
        activity: float,
        compatibility: float
    ) -> str:
        """
        Generate human-readable explanation for a recommendation.
        
        Args:
            similarity: Similarity score
            rating: Rating score
            activity: Activity score
            compatibility: Final compatibility score
            
        Returns:
            Explanation string
        """
        reasons = []
        
        # Similarity
        if similarity > 0.8:
            reasons.append("excellent skill match")
        elif similarity > 0.6:
            reasons.append("good skill match")
        elif similarity > 0.4:
            reasons.append("decent skill match")
        
        # Rating
        if rating and rating >= 4.5:
            reasons.append("highly rated mentor")
        elif rating and rating >= 4.0:
            reasons.append("well-rated mentor")
        
        # Activity
        if activity > 0.7:
            reasons.append("very active")
        elif activity > 0.4:
            reasons.append("active")
        
        if not reasons:
            reasons.append("potential match")
        
        return f"Recommended because: {', '.join(reasons)}"


# ======================
# UTILITY FUNCTIONS
# ======================

def get_global_engine(db: Session) -> RecommendationEngine:
    """
    Get or create global recommendation engine instance.
    
    Args:
        db: Database session
        
    Returns:
        Trained RecommendationEngine instance
    """
    # In production, this should be cached/singleton
    engine = RecommendationEngine()
    engine.train(db)
    return engine
