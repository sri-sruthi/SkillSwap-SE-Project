# skillswap2/app/api/token.py
"""
Token & Rewards API Router
Phase 3: REST endpoints for token wallet operations

Endpoints:
- GET /tokens/wallet - Get current user's wallet balance
- GET /tokens/transactions - Get transaction history
- GET /tokens/eligibility - Check session booking eligibility
- POST /tokens/transfer - Admin endpoint for manual token adjustment (future)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, UTC

from app.database import get_db
from app.models.user import User
from app.models.token import TokenWallet, TokenTransaction, TransactionType, TransactionStatus
from app.schemas.token import (
    TokenWalletResponse,
    TokenTransactionResponse, 
    TokenEligibilityResponse,
    TokenTransferRequest
)
from app.services.token_service import (
    get_wallet_balance,
    get_transaction_history,
    can_book_session
)
from app.utils.security import get_current_user

router = APIRouter(prefix="/tokens", tags=["tokens"])


# ======================
# WALLET BALANCE
# ======================
@router.get("/wallet", response_model=TokenWalletResponse)
def get_my_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's token wallet balance.
    
    Returns:
        - wallet_id: Wallet identifier
        - user_id: User identifier  
        - balance: Current token balance
        - created_at: Wallet creation timestamp
        - updated_at: Last update timestamp
    """
    try:
        # Get wallet using service function
        balance = get_wallet_balance(db, current_user.id)
        
        # Get full wallet object for complete response
        wallet = db.query(TokenWallet).filter(
            TokenWallet.user_id == current_user.id
        ).first()
        
        if not wallet:
            raise HTTPException(
                status_code=404,
                detail="Wallet not found. Please contact support."
            )
        
        return TokenWalletResponse(
            wallet_id=wallet.id,
            user_id=wallet.user_id,
            balance=wallet.balance,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve wallet: {str(e)}"
        )


# ======================
# TRANSACTION HISTORY
# ======================
@router.get("/transactions", response_model=List[TokenTransactionResponse])
def get_my_transactions(
    limit: int = Query(50, ge=1, le=100, description="Number of transactions to return"),
    offset: int = Query(0, ge=0, description="Number of transactions to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's token transaction history.
    
    Query Parameters:
        - limit: Maximum transactions to return (1-100, default 50)
        - offset: Number of transactions to skip (for pagination)
    
    Returns:
        List of transactions with:
        - transaction_id: Transaction identifier
        - type: DEBIT/CREDIT/INITIAL_ALLOCATION
        - amount: Token amount
        - status: INITIATED/COMPLETED/FAILED/ROLLED_BACK
        - description: Transaction description
        - session_id: Associated session (if applicable)
        - timestamp: Transaction timestamp
    """
    try:
        # Get formatted transaction history
        transactions = get_transaction_history(db, current_user.id, limit, offset)
        
        return [
            TokenTransactionResponse(
                transaction_id=t["transaction_id"],
                type=t["type"],
                amount=t["amount"],
                status=t["status"],
                description=t["description"],
                session_id=t["session_id"],
                timestamp=datetime.fromisoformat(t["timestamp"]) if t["timestamp"] else None
            )
            for t in transactions
        ]
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve transactions: {str(e)}"
        )


# ======================
# SESSION BOOKING ELIGIBILITY
# ======================
@router.get("/eligibility", response_model=TokenEligibilityResponse)
def check_booking_eligibility(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if current user can book a session based on token balance.
    
    Returns:
        - can_book: Boolean eligibility status
        - current_balance: User's current token balance
        - required_balance: Minimum required balance (10 tokens)
        - session_cost: Cost per session (10 tokens)
        - deficit: How many tokens short (0 if eligible)
    """
    try:
        eligibility = can_book_session(db, current_user.id)
        
        if "error" in eligibility:
            raise HTTPException(status_code=404, detail=eligibility["error"])
        
        return TokenEligibilityResponse(
            can_book=eligibility["can_book"],
            current_balance=eligibility["current_balance"],
            required_balance=eligibility["required_balance"],
            session_cost=eligibility["session_cost"],
            deficit=eligibility["deficit"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check eligibility: {str(e)}"
        )


# ======================
# ADMIN: MANUAL TOKEN ADJUSTMENT (Future Enhancement)
# ======================
@router.post("/admin/transfer")
def manual_token_transfer(
    transfer: TokenTransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin-only endpoint for manual token adjustments.
    
    ⚠️ FUTURE ENHANCEMENT - Currently returns 501 Not Implemented
    
    Use cases:
    - Compensate users for platform errors
    - Award tokens for community contributions
    - Manual corrections
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can perform manual token transfers"
        )
    
    raise HTTPException(
        status_code=501,
        detail="Manual token transfers not yet implemented. Coming in Phase 7 (Admin Module)."
    )


# ======================
# HEALTH CHECK
# ======================
@router.get("/health")
def token_service_health():
    """
    Health check endpoint for token service.
    """
    return {
        "service": "token_rewards",
        "status": "operational",
        "timestamp": datetime.now(UTC).isoformat()
    }
