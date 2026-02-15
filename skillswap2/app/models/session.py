# app/models/session.py
from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.database import Base

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    learner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id"))
    scheduled_time = Column(TIMESTAMP)
    status = Column(String(20), default="Pending")
    notes = Column(String)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, onupdate=func.now())

    # Relationships
    learner = relationship("User", foreign_keys=[learner_id], back_populates="learner_sessions")
    mentor = relationship("User", foreign_keys=[mentor_id], back_populates="mentor_sessions")
    skill = relationship("Skill", back_populates="sessions")  # ✅ This now works
    # ✅ ADD THIS LINE
    review = relationship("Review", back_populates="session", uselist=False)