from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
# ---------------- USER (AUTH TABLE) ----------------
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, onupdate=func.now())

    # ✅ FIX: Explicitly specify foreign_keys for ambiguous relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    user_skills = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    learner_sessions = relationship("Session", foreign_keys="Session.learner_id", back_populates="learner")
    mentor_sessions = relationship("Session", foreign_keys="Session.mentor_id", back_populates="mentor")
    wallet = relationship("TokenWallet", back_populates="user", uselist=False)


# ---------------- PROFILE TABLE ----------------
class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name: str = Column(String(100), nullable=False)
    phone: str = Column(String(20))
    bio: str = Column(String(500))          # ← for learner's learning_goals
    studying: str = Column(String(150))      # ← for learners
    qualification: str = Column(String(150)) # ← for mentors
    age: int = Column(Integer)
    experience: str = Column(String(100))    # ← for mentors
    profile_picture: str = Column(String(255))
    created_at: datetime = Column(TIMESTAMP, server_default=func.now())
    updated_at: datetime = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )
    user = relationship("User", back_populates="profile")


# ---------------- TOKEN WALLET ----------------
class TokenWallet(Base):
    __tablename__ = "token_wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    balance = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )

    user = relationship("User", back_populates="wallet")