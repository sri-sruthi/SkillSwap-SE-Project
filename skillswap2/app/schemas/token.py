# skillswap2/app/schemas/token.py
"""
Token & Rewards Pydantic Schemas
Phase 3: API request/response models
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


# ======================
# WALLET SCHEMAS
# ======================
class TokenWalletBase(BaseModel):
    """Base wallet schema"""
    pass


class TokenWalletCreate(TokenWalletBase):
    """Wallet creation schema (internal use)"""
    user_id: int
    balance: int = 20  # Initial allocation


class TokenWalletResponse(BaseModel):
    """Wallet response for API"""
    wallet_id: int = Field(..., description="Wallet identifier")
    user_id: int = Field(..., description="User identifier")
    balance: int = Field(..., description="Current token balance")
    created_at: datetime = Field(..., description="Wallet creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# ======================
# TRANSACTION SCHEMAS
# ======================
class TokenTransactionBase(BaseModel):
    """Base transaction schema"""
    pass


class TokenTransactionResponse(BaseModel):
    """Transaction response for API"""
    transaction_id: int = Field(..., description="Transaction identifier")
    type: str = Field(..., description="Transaction type (DEBIT/CREDIT/INITIAL_ALLOCATION)")
    amount: int = Field(..., description="Token amount")
    status: str = Field(..., description="Transaction status (COMPLETED/FAILED/etc)")
    description: Optional[str] = Field(None, description="Transaction description")
    session_id: Optional[int] = Field(None, description="Associated session ID")
    timestamp: Optional[datetime] = Field(None, description="Transaction timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# ======================
# ELIGIBILITY CHECK SCHEMA
# ======================
class TokenEligibilityResponse(BaseModel):
    """Session booking eligibility response"""
    can_book: bool = Field(..., description="Whether user can book a session")
    current_balance: int = Field(..., description="User's current token balance")
    required_balance: int = Field(..., description="Minimum required balance (10 tokens)")
    session_cost: int = Field(..., description="Cost per session (10 tokens)")
    deficit: int = Field(..., description="Token shortfall (0 if eligible)")


# ======================
# ADMIN TRANSFER SCHEMA (Future)
# ======================
class TokenTransferRequest(BaseModel):
    """Admin manual token transfer request"""
    target_user_id: int = Field(..., description="User receiving tokens")
    amount: int = Field(..., ge=1, description="Number of tokens to transfer")
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for transfer")
