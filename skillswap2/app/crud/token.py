# app/crud/token.py
"""
Token & Rewards Module - CRUD Operations
Phase 2: Core Logic Implementation

This module implements the database operations for token wallets and transactions.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime

from app import models
from app.models.token import TransactionType, TransactionStatus


# =====================================
# WALLET CRUD OPERATIONS
# =====================================

def get_wallet_by_user_id(db: Session, user_id: int) -> Optional[models.TokenWallet]:
    """
    Retrieve a user's token wallet.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        TokenWallet object or None if not found
    """
    return db.query(models.TokenWallet).filter(
        models.TokenWallet.user_id == user_id
    ).first()


def create_wallet(db: Session, user_id: int, initial_balance: int = 20) -> models.TokenWallet:
    """
    Create a new token wallet for a user with initial allocation.
    
    Args:
        db: Database session
        user_id: User ID
        initial_balance: Initial token allocation (default: 20)
        
    Returns:
        Created TokenWallet object
    """
    wallet = models.TokenWallet(
        user_id=user_id,
        balance=initial_balance
    )
    db.add(wallet)
    db.flush()  # Get wallet ID without committing
    
    # Record initial allocation transaction
    initial_transaction = models.TokenTransaction(
        wallet_id=wallet.id,
        amount=initial_balance,
        type=TransactionType.INITIAL,
        status=TransactionStatus.COMPLETED,
        description="Initial token allocation"
    )
    db.add(initial_transaction)
    
    return wallet


def update_wallet_balance(
    db: Session,
    wallet_id: int,
    new_balance: int
) -> models.TokenWallet:
    """
    Update wallet balance (used internally by transaction operations).
    
    Args:
        db: Database session
        wallet_id: Wallet ID
        new_balance: New balance value
        
    Returns:
        Updated TokenWallet object
    """
    wallet = db.query(models.TokenWallet).filter(
        models.TokenWallet.id == wallet_id
    ).first()
    
    if not wallet:
        raise ValueError(f"Wallet with ID {wallet_id} not found")
    
    wallet.balance = new_balance
    return wallet


# =====================================
# TRANSACTION CRUD OPERATIONS
# =====================================

def create_transaction(
    db: Session,
    wallet_id: int,
    amount: int,
    transaction_type: TransactionType,
    session_id: Optional[int] = None,
    description: Optional[str] = None
) -> models.TokenTransaction:
    """
    Create a new token transaction record.
    
    Args:
        db: Database session
        wallet_id: Wallet ID
        amount: Token amount (positive for credit, negative for debit)
        transaction_type: Type of transaction (EARN, SPEND, INITIAL, REFUND)
        session_id: Optional session ID
        description: Optional transaction description
        
    Returns:
        Created TokenTransaction object
    """
    transaction = models.TokenTransaction(
        wallet_id=wallet_id,
        session_id=session_id,
        amount=amount,
        type=transaction_type,
        status=TransactionStatus.INITIATED,
        description=description
    )
    db.add(transaction)
    db.flush()  # Get transaction ID
    return transaction


def update_transaction_status(
    db: Session,
    transaction_id: int,
    status: TransactionStatus
) -> models.TokenTransaction:
    """
    Update transaction status (INITIATED -> COMPLETED/FAILED/ROLLED_BACK).
    
    Args:
        db: Database session
        transaction_id: Transaction ID
        status: New status
        
    Returns:
        Updated TokenTransaction object
    """
    transaction = db.query(models.TokenTransaction).filter(
        models.TokenTransaction.id == transaction_id
    ).first()
    
    if not transaction:
        raise ValueError(f"Transaction with ID {transaction_id} not found")
    
    transaction.status = status
    return transaction


def get_transaction_by_id(
    db: Session,
    transaction_id: int
) -> Optional[models.TokenTransaction]:
    """
    Retrieve a transaction by ID.
    
    Args:
        db: Database session
        transaction_id: Transaction ID
        
    Returns:
        TokenTransaction object or None
    """
    return db.query(models.TokenTransaction).filter(
        models.TokenTransaction.id == transaction_id
    ).first()


def get_user_transactions(
    db: Session,
    user_id: int,
    limit: int = 50,
    offset: int = 0
) -> List[models.TokenTransaction]:
    """
    Retrieve transaction history for a user.
    
    Args:
        db: Database session
        user_id: User ID
        limit: Maximum number of transactions to return
        offset: Number of transactions to skip
        
    Returns:
        List of TokenTransaction objects
    """
    # Join TokenTransaction with TokenWallet to filter by user_id
    return db.query(models.TokenTransaction).join(
        models.TokenWallet,
        models.TokenTransaction.wallet_id == models.TokenWallet.id
    ).filter(
        models.TokenWallet.user_id == user_id
    ).order_by(
        models.TokenTransaction.timestamp.desc()
    ).limit(limit).offset(offset).all()


def get_session_transactions(
    db: Session,
    session_id: int
) -> List[models.TokenTransaction]:
    """
    Retrieve all transactions associated with a specific session.
    
    Args:
        db: Database session
        session_id: Session ID
        
    Returns:
        List of TokenTransaction objects
    """
    return db.query(models.TokenTransaction).filter(
        models.TokenTransaction.session_id == session_id
    ).all()


# =====================================
# TRANSACTION VALIDATION
# =====================================

def check_duplicate_transaction(
    db: Session,
    session_id: int,
    transaction_type: TransactionType
) -> bool:
    """
    Check if a transaction already exists for a session.
    Prevents duplicate token deductions or rewards.
    
    Args:
        db: Database session
        session_id: Session ID
        transaction_type: Transaction type to check
        
    Returns:
        True if duplicate exists, False otherwise
    """
    existing = db.query(models.TokenTransaction).filter(
        models.TokenTransaction.session_id == session_id,
        models.TokenTransaction.type == transaction_type,
        models.TokenTransaction.status == TransactionStatus.COMPLETED
    ).first()
    
    return existing is not None


# =====================================
# ANALYTICS & REPORTING
# =====================================

def get_total_tokens_in_circulation(db: Session) -> int:
    """
    Calculate total tokens currently in all wallets.
    
    Args:
        db: Database session
        
    Returns:
        Total token count
    """
    result = db.query(func.sum(models.TokenWallet.balance)).scalar()
    return result or 0


def get_user_token_statistics(db: Session, user_id: int) -> dict:
    """
    Get token statistics for a user.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Dictionary with statistics (total_earned, total_spent, current_balance)
    """
    wallet = get_wallet_by_user_id(db, user_id)
    if not wallet:
        return {
            "total_earned": 0,
            "total_spent": 0,
            "current_balance": 0
        }
    
    # Calculate total earned (EARN + INITIAL)
    earned = db.query(func.sum(models.TokenTransaction.amount)).filter(
        models.TokenTransaction.wallet_id == wallet.id,
        models.TokenTransaction.type.in_([TransactionType.EARN, TransactionType.INITIAL]),
        models.TokenTransaction.status == TransactionStatus.COMPLETED
    ).scalar() or 0
    
    # Calculate total spent (SPEND transactions are negative)
    spent = db.query(func.sum(models.TokenTransaction.amount)).filter(
        models.TokenTransaction.wallet_id == wallet.id,
        models.TokenTransaction.type == TransactionType.SPEND,
        models.TokenTransaction.status == TransactionStatus.COMPLETED
    ).scalar() or 0
    
    return {
        "total_earned": earned,
        "total_spent": abs(spent),  # Make positive for display
        "current_balance": wallet.balance
    }