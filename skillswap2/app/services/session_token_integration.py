# app/services/session_token_integration.py
"""
Session-Token Integration Module
Phase 2: Integration with Session Completion

This module connects session lifecycle events with token operations.
"""

from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from app import models
from app.services import token_service
from app.models.token import TransactionType, TransactionStatus


# =====================================
# SESSION LIFECYCLE HANDLERS
# =====================================

def on_session_confirmed(
    db: Session,
    session: models.Session
) -> Dict[str, Any]:
    """
    Handle token deduction when a session is confirmed.
    
    This is called by the Session Management module when a mentor
    accepts a session request.
    
    Args:
        db: Database session
        session: Session object
        
    Returns:
        Dictionary with token operation result
        
    Raises:
        ValueError: If insufficient balance or validation fails
    """
    try:
        result = token_service.spend_tokens(
            db=db,
            user_id=session.learner_id,
            session_id=session.id
        )
        
        return {
            "success": True,
            "message": "Tokens deducted successfully",
            "transaction_details": result
        }
        
    except ValueError as e:
        # Insufficient balance or validation error
        return {
            "success": False,
            "error": str(e),
            "error_type": "validation_error"
        }
    except Exception as e:
        # System error
        return {
            "success": False,
            "error": f"Token deduction failed: {str(e)}",
            "error_type": "system_error"
        }


def on_session_completed(
    db: Session,
    session: models.Session
) -> Dict[str, Any]:
    """
    Handle token reward when a session is completed.
    
    This is called by the Session Management module when a session
    is marked as completed.
    
    Args:
        db: Database session
        session: Session object
        
    Returns:
        Dictionary with token operation result
    """
    try:
        result = token_service.earn_tokens(
            db=db,
            user_id=session.mentor_id,
            session_id=session.id
        )
        
        return {
            "success": True,
            "message": "Tokens awarded to mentor",
            "transaction_details": result
        }
        
    except ValueError as e:
        # Duplicate transaction or validation error
        return {
            "success": False,
            "error": str(e),
            "error_type": "validation_error"
        }
    except Exception as e:
        # System error
        return {
            "success": False,
            "error": f"Token reward failed: {str(e)}",
            "error_type": "system_error"
        }


def on_session_cancelled(
    db: Session,
    session: models.Session,
    cancelled_by: int
) -> Dict[str, Any]:
    """
    Handle token refund when a session is cancelled.
    
    Refund is issued if tokens were already deducted.
    
    Args:
        db: Database session
        session: Session object
        cancelled_by: User ID who cancelled the session
        
    Returns:
        Dictionary with refund result
    """
    # Only refund if session was confirmed (tokens were deducted)
    if session.status not in ["Confirmed", "Pending"]:
        return {
            "success": True,
            "message": "No refund needed - session not confirmed",
            "refund_issued": False
        }
    
    try:
        result = token_service.refund_tokens(
            db=db,
            session_id=session.id,
            reason=f"Session cancelled by user {cancelled_by}"
        )
        
        return {
            "success": True,
            "message": "Tokens refunded to learner",
            "refund_issued": True,
            "refund_details": result
        }
        
    except ValueError as e:
        # No transaction to refund (session wasn't paid for)
        return {
            "success": True,
            "message": "No refund needed - no payment found",
            "refund_issued": False
        }
    except Exception as e:
        # System error during refund
        return {
            "success": False,
            "error": f"Refund failed: {str(e)}",
            "error_type": "system_error"
        }


# =====================================
# PRE-SESSION VALIDATION
# =====================================

def validate_session_booking(
    db: Session,
    learner_id: int
) -> Dict[str, Any]:
    """
    Validate if a learner can book a session based on token balance.
    
    This should be called BEFORE creating a session request to provide
    early feedback to the user.
    
    Args:
        db: Database session
        learner_id: Learner's user ID
        
    Returns:
        Dictionary with validation result
    """
    result = token_service.can_book_session(db, learner_id)
    
    if result.get("can_book"):
        return {
            "valid": True,
            "message": "Sufficient tokens available",
            "details": result
        }
    else:
        deficit = result.get("deficit", 0)
        return {
            "valid": False,
            "message": f"Insufficient tokens. You need {deficit} more tokens to book a session.",
            "details": result
        }


# =====================================
# TRANSACTION QUERY HELPERS
# =====================================

def get_session_token_status(
    db: Session,
    session_id: int
) -> Dict[str, Any]:
    """
    Get token transaction status for a specific session.
    
    Args:
        db: Database session
        session_id: Session ID
        
    Returns:
        Dictionary with transaction status
    """
    from app.crud import token as token_crud
    
    transactions = token_crud.get_session_transactions(db, session_id)
    
    spend_tx = next(
        (t for t in transactions if t.type == TransactionType.SPEND), None
    )
    earn_tx = next(
        (t for t in transactions if t.type == TransactionType.EARN), None
    )
    refund_tx = next(
        (t for t in transactions if t.type == TransactionType.REFUND), None
    )
    
    return {
        "session_id": session_id,
        "tokens_deducted": spend_tx is not None and spend_tx.status == TransactionStatus.COMPLETED,
        "tokens_awarded": earn_tx is not None and earn_tx.status == TransactionStatus.COMPLETED,
        "tokens_refunded": refund_tx is not None and refund_tx.status == TransactionStatus.COMPLETED,
        "transactions": [
            {
                "type": t.type.value,
                "amount": t.amount,
                "status": t.status.value,
                "timestamp": t.timestamp.isoformat() if t.timestamp else None
            }
            for t in transactions
        ]
    }


# =====================================
# BULK OPERATIONS (ADMIN)
# =====================================

def get_platform_token_summary(db: Session) -> Dict[str, Any]:
    """
    Get overall platform token statistics.
    Used for admin dashboard and analytics.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with platform-wide token statistics
    """
    from app.crud import token as token_crud
    
    total_in_circulation = token_crud.get_total_tokens_in_circulation(db)
    
    # Count wallets
    total_wallets = db.query(models.TokenWallet).count()
    
    # Calculate average balance
    avg_balance = total_in_circulation / total_wallets if total_wallets > 0 else 0
    
    # Count completed transactions
    total_transactions = db.query(models.TokenTransaction).filter(
        models.TokenTransaction.status == TransactionStatus.COMPLETED
    ).count()
    
    return {
        "total_tokens_in_circulation": total_in_circulation,
        "total_wallets": total_wallets,
        "average_balance_per_wallet": round(avg_balance, 2),
        "total_completed_transactions": total_transactions
    }
