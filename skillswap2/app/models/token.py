# app/models/token.py
from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Enum, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class TransactionType(str, enum.Enum):
    EARN = "earn"
    SPEND = "spend"
    INITIAL = "initial"
    REFUND = "refund"

class TransactionStatus(str, enum.Enum):
    INITIATED = "initiated"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class TokenWallet(Base):
    __tablename__ = "token_wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    balance = Column(Integer, default=20, nullable=False)  # Initial allocation = 20 tokens
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="wallet")
    transactions = relationship("TokenTransaction", back_populates="wallet", cascade="all, delete-orphan")

class TokenTransaction(Base):
    __tablename__ = "token_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("token_wallets.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Integer, nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.INITIATED, nullable=False)
    description = Column(String(255))
    timestamp = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    wallet = relationship("TokenWallet", back_populates="transactions")
    session = relationship("Session", foreign_keys=[session_id])