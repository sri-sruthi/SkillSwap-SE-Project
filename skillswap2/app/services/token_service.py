# app/services/token_service.py
"""
Token & Rewards Module - Business Logic Service
Phase 2: Core Logic Implementation

This module implements the business logic for token operations including
earning, spending, and transaction management with atomic guarantees.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, Dict, Any
from datetime import datetime

from app import models
from app.crud import token as token_crud
from app.models.token import TransactionType, TransactionStatus


# =====================================
# CONFIGURATION CONSTANTS
# =====================================

class TokenPolicy:
    """Token economy policy configuration."""
    INITIAL_ALLOCATION = 20  # Tokens given to new users
    SESSION_COST = 10        # Tokens required to book a session
    SESSION_REWARD = 10      # Tokens earned by mentor on completion
    MINIMUM_BALANCE = 10     # Minimum balance required to book


# =====================================
# WALLET OPERATIONS
# =====================================

def initialize_wallet(db: Session, user_id: int) -> models.TokenWallet:
    """
    Create a new wallet with initial token allocation.
    Called during user registration.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Created TokenWallet object
        
    Raises:
        ValueError: If wallet already exists
    """
    # Check if wallet already exists
    existing_wallet = token_crud.get_wallet_by_user_id(db, user_id)
    if existing_wallet:
        raise ValueError(f"Wallet already exists for user {user_id}")
    
    try:
        wallet = token_crud.create_wallet(
            db=db,
            user_id=user_id,
            initial_balance=TokenPolicy.INITIAL_ALLOCATION
        )
        db.commit()
        db.refresh(wallet)
        return wallet
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"Failed to initialize wallet: {str(e)}")


def get_wallet_balance(db: Session, user_id: int) -> int:
    """
    Get current token balance for a user.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Current balance
        
    Raises:
        ValueError: If wallet not found
    """
    wallet = token_crud.get_wallet_by_user_id(db, user_id)
    if not wallet:
        raise ValueError(f"Wallet not found for user {user_id}")
    return wallet.balance


def validate_sufficient_balance(db: Session, user_id: int, required_amount: int) -> bool:
    """
    Check if user has sufficient tokens.
    
    Args:
        db: Database session
        user_id: User ID
        required_amount: Amount required
        
    Returns:
        True if sufficient balance exists
    """
    try:
        balance = get_wallet_balance(db, user_id)
        return balance >= required_amount
    except ValueError:
        return False


# =====================================
# TOKEN SPENDING (Session Booking)
# =====================================

def spend_tokens(
    db: Session,
    user_id: int,
    session_id: int,
    amount: Optional[int] = None
) -> Dict[str, Any]:
    """
    Deduct tokens from learner's wallet when session is confirmed.
    
    This operation is ATOMIC - either completes fully or rolls back entirely.
    
    Args:
        db: Database session
        user_id: Learner's user ID
        session_id: Session ID
        amount: Token amount (defaults to SESSION_COST)
        
    Returns:
        Dictionary with transaction details
        
    Raises:
        ValueError: If insufficient balance or wallet not found
        Exception: If transaction fails
    """
    if amount is None:
        amount = TokenPolicy.SESSION_COST
    
    # Validation checks
    wallet = token_crud.get_wallet_by_user_id(db, user_id)
    if not wallet:
        raise ValueError(f"Wallet not found for user {user_id}")
    
    if wallet.balance < amount:
        raise ValueError(
            f"Insufficient balance. Required: {amount}, Available: {wallet.balance}"
        )
    
    # Check for duplicate transaction
    if token_crud.check_duplicate_transaction(db, session_id, TransactionType.SPEND):
        raise ValueError(f"Tokens already deducted for session {session_id}")
    
    # Begin atomic transaction
    try:
        # Create transaction record
        transaction = token_crud.create_transaction(
            db=db,
            wallet_id=wallet.id,
            amount=-amount,  # Negative for debit
            transaction_type=TransactionType.SPEND,
            session_id=session_id,
            description=f"Session booking - Session ID: {session_id}"
        )
        
        # Update wallet balance
        new_balance = wallet.balance - amount
        token_crud.update_wallet_balance(db, wallet.id, new_balance)
        
        # Mark transaction as completed
        token_crud.update_transaction_status(
            db, transaction.id, TransactionStatus.COMPLETED
        )
        
        # Commit atomic transaction
        db.commit()
        db.refresh(transaction)
        db.refresh(wallet)
        
        return {
            "success": True,
            "transaction_id": transaction.id,
            "amount_spent": amount,
            "previous_balance": wallet.balance + amount,
            "new_balance": wallet.balance,
            "session_id": session_id,
            "timestamp": transaction.timestamp
        }
        
    except SQLAlchemyError as e:
        # Rollback on any database error
        db.rollback()
        
        # Mark transaction as failed if it was created
        if 'transaction' in locals():
            try:
                token_crud.update_transaction_status(
                    db, transaction.id, TransactionStatus.FAILED
                )
                db.commit()
            except:
                pass
        
        raise Exception(f"Token spending failed: {str(e)}")


# =====================================
# TOKEN EARNING (Session Completion)
# =====================================

def earn_tokens(
    db: Session,
    user_id: int,
    session_id: int,
    amount: Optional[int] = None
) -> Dict[str, Any]:
    """
    Credit tokens to mentor's wallet after session completion.
    
    This operation is ATOMIC - either completes fully or rolls back entirely.
    
    Args:
        db: Database session
        user_id: Mentor's user ID
        session_id: Session ID
        amount: Token amount (defaults to SESSION_REWARD)
        
    Returns:
        Dictionary with transaction details
        
    Raises:
        ValueError: If wallet not found or duplicate transaction
        Exception: If transaction fails
    """
    if amount is None:
        amount = TokenPolicy.SESSION_REWARD
    
    # Validation checks
    wallet = token_crud.get_wallet_by_user_id(db, user_id)
    if not wallet:
        raise ValueError(f"Wallet not found for user {user_id}")
    
    # Check for duplicate transaction
    if token_crud.check_duplicate_transaction(db, session_id, TransactionType.EARN):
        raise ValueError(f"Tokens already awarded for session {session_id}")
    
    # Begin atomic transaction
    try:
        # Create transaction record
        transaction = token_crud.create_transaction(
            db=db,
            wallet_id=wallet.id,
            amount=amount,  # Positive for credit
            transaction_type=TransactionType.EARN,
            session_id=session_id,
            description=f"Session completion reward - Session ID: {session_id}"
        )
        
        # Update wallet balance
        new_balance = wallet.balance + amount
        token_crud.update_wallet_balance(db, wallet.id, new_balance)
        
        # Mark transaction as completed
        token_crud.update_transaction_status(
            db, transaction.id, TransactionStatus.COMPLETED
        )
        
        # Commit atomic transaction
        db.commit()
        db.refresh(transaction)
        db.refresh(wallet)
        
        return {
            "success": True,
            "transaction_id": transaction.id,
            "amount_earned": amount,
            "previous_balance": wallet.balance - amount,
            "new_balance": wallet.balance,
            "session_id": session_id,
            "timestamp": transaction.timestamp
        }
        
    except SQLAlchemyError as e:
        # Rollback on any database error
        db.rollback()
        
        # Mark transaction as failed if it was created
        if 'transaction' in locals():
            try:
                token_crud.update_transaction_status(
                    db, transaction.id, TransactionStatus.FAILED
                )
                db.commit()
            except:
                pass
        
        raise Exception(f"Token earning failed: {str(e)}")


# =====================================
# REFUND OPERATIONS
# =====================================

def refund_tokens(
    db: Session,
    session_id: int,
    reason: str = "Session cancelled"
) -> Dict[str, Any]:
    """
    Refund tokens to learner if session is cancelled.
    
    Args:
        db: Database session
        session_id: Session ID
        reason: Refund reason
        
    Returns:
        Dictionary with refund details
        
    Raises:
        ValueError: If no spend transaction found
        Exception: If refund fails
    """
    # Find original spend transaction
    transactions = token_crud.get_session_transactions(db, session_id)
    spend_transaction = next(
        (t for t in transactions 
         if t.type == TransactionType.SPEND and t.status == TransactionStatus.COMPLETED),
        None
    )
    
    if not spend_transaction:
        raise ValueError(f"No completed spend transaction found for session {session_id}")
    
    # Get wallet
    wallet = db.query(models.TokenWallet).filter(
        models.TokenWallet.id == spend_transaction.wallet_id
    ).first()
    
    if not wallet:
        raise ValueError("Wallet not found for refund")
    
    refund_amount = abs(spend_transaction.amount)
    
    try:
        # Create refund transaction
        refund_transaction = token_crud.create_transaction(
            db=db,
            wallet_id=wallet.id,
            amount=refund_amount,
            transaction_type=TransactionType.REFUND,
            session_id=session_id,
            description=f"Refund: {reason}"
        )
        
        # Update balance
        new_balance = wallet.balance + refund_amount
        token_crud.update_wallet_balance(db, wallet.id, new_balance)
        
        # Mark refund as completed
        token_crud.update_transaction_status(
            db, refund_transaction.id, TransactionStatus.COMPLETED
        )
        
        # Commit
        db.commit()
        db.refresh(refund_transaction)
        db.refresh(wallet)
        
        return {
            "success": True,
            "refund_transaction_id": refund_transaction.id,
            "amount_refunded": refund_amount,
            "new_balance": wallet.balance,
            "reason": reason
        }
        
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"Refund failed: {str(e)}")


# =====================================
# TRANSACTION HISTORY
# =====================================

def get_transaction_history(
    db: Session,
    user_id: int,
    limit: int = 50,
    offset: int = 0
) -> list:
    """
    Retrieve formatted transaction history for a user.
    
    Args:
        db: Database session
        user_id: User ID
        limit: Maximum transactions to return
        offset: Number of transactions to skip
        
    Returns:
        List of formatted transaction dictionaries
    """
    transactions = token_crud.get_user_transactions(db, user_id, limit, offset)
    
    type_map = {
        "earn": "CREDIT",
        "refund": "CREDIT",
        "spend": "DEBIT",
        "initial": "INITIAL_ALLOCATION",
    }

    return [
        {
            "transaction_id": t.id,
            # Keep API contract stable for frontend: CREDIT/DEBIT/INITIAL_ALLOCATION
            "type": type_map.get(t.type.value, t.type.value.upper()),
            # Frontend decides sign by type; expose absolute amount for display consistency.
            "amount": abs(t.amount),
            "status": t.status.value.upper(),
            "description": t.description,
            "session_id": t.session_id,
            "timestamp": t.timestamp.isoformat() if t.timestamp else None
        }
        for t in transactions
    ]


# =====================================
# VALIDATION & POLICY ENFORCEMENT
# =====================================

def can_book_session(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Check if user can book a session based on token balance.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Dictionary with eligibility status and details
    """
    try:
        balance = get_wallet_balance(db, user_id)
        can_book = balance >= TokenPolicy.MINIMUM_BALANCE
        
        return {
            "can_book": can_book,
            "current_balance": balance,
            "required_balance": TokenPolicy.MINIMUM_BALANCE,
            "session_cost": TokenPolicy.SESSION_COST,
            "deficit": max(0, TokenPolicy.MINIMUM_BALANCE - balance)
        }
    except ValueError as e:
        return {
            "can_book": False,
            "error": str(e)
        }


# =====================================
# PHASE 3 COMPATIBILITY HELPERS
# =====================================

def spend_tokens_for_session(
    db: Session,
    user_id: int,
    session_id: int
) -> Dict[str, Any]:
    """
    Backward-compatible wrapper used by Session API integration.
    Deduct fixed session cost from learner wallet on confirmation.
    """
    return spend_tokens(
        db=db,
        user_id=user_id,
        session_id=session_id,
        amount=TokenPolicy.SESSION_COST
    )


def reward_tokens_for_session(
    db: Session,
    user_id: int,
    session_id: int
) -> Dict[str, Any]:
    """
    Backward-compatible wrapper used by Session API integration.
    Credit fixed session reward to mentor wallet on completion.
    """
    return earn_tokens(
        db=db,
        user_id=user_id,
        session_id=session_id,
        amount=TokenPolicy.SESSION_REWARD
    )


def refund_tokens_for_session(
    db: Session,
    user_id: int,
    session_id: int,
    reason: str = "Session cancelled"
) -> Dict[str, Any]:
    """
    Backward-compatible wrapper used by Session API integration.
    Ensures the refund applies to the learner who originally paid.
    """
    wallet = token_crud.get_wallet_by_user_id(db, user_id)
    if not wallet:
        raise ValueError(f"Wallet not found for user {user_id}")

    transactions = token_crud.get_session_transactions(db, session_id)
    spend_tx = next(
        (
            t for t in transactions
            if t.type == TransactionType.SPEND and t.status == TransactionStatus.COMPLETED
        ),
        None
    )
    if not spend_tx:
        raise ValueError(f"No completed spend transaction found for session {session_id}")

    if spend_tx.wallet_id != wallet.id:
        raise ValueError(
            f"Spend transaction for session {session_id} does not belong to user {user_id}"
        )

    return refund_tokens(
        db=db,
        session_id=session_id,
        reason=reason
    )
