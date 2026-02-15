from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, ARRAY, JSON, func
from sqlalchemy.orm import relationship
from app.database import Base

# app/models/skill.py
class Skill(Base):
    __tablename__ = "skills"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), unique=True, nullable=False, index=True)  # ← CHANGED FROM 'name' TO 'title'
    description = Column(Text)
    category = Column(String(50), default="General")
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    user_skills = relationship("UserSkill", back_populates="skill", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="skill")  # ← ADD THIS

class UserSkill(Base):
    __tablename__ = "user_skills"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        index=True,
        nullable=False
    )
    skill_id = Column(
        Integer, 
        ForeignKey("skills.id", ondelete="CASCADE"), 
        index=True,
        nullable=False
    )
    skill_type = Column(String(20), nullable=False)  # 'teach' or 'learn'
    proficiency_level = Column(String(20))
    # SQLite (used by tests) does not support ARRAY; store as JSON there.
    tags = Column(ARRAY(String).with_variant(JSON, "sqlite"), default=list)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    skill = relationship("Skill", back_populates="user_skills")
    user = relationship("User", back_populates="user_skills")
