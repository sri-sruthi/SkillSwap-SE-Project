from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Skill(Base):
    __tablename__ = "skills"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    category = Column(String(50))
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationship
    user_skills = relationship("UserSkill", back_populates="skill", cascade="all, delete-orphan")

class UserSkill(Base):
    __tablename__ = "user_skills"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    skill_type = Column(String(20), nullable=False)  # 'teach' or 'learn'
    proficiency_level = Column(String(20))
    tags = Column(ARRAY(String), default=[])
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    skill = relationship("Skill", back_populates="user_skills")