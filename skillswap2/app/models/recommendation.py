# app/models/recommendation.py
from sqlalchemy import Column, Integer, ForeignKey, Float, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.database import Base

class Recommendation(Base):
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    learner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mentor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=True)
    similarity_score = Column(Float, nullable=False)
    compatibility_score = Column(Float, nullable=False)
    rank = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    learner = relationship("User", foreign_keys=[learner_id])
    mentor = relationship("User", foreign_keys=[mentor_id])
    skill = relationship("Skill", foreign_keys=[skill_id])