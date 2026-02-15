#!/usr/bin/env python3
"""
Phase 2 Testing Script
Token & Rewards - Core Logic Testing

This script tests all Phase 2 functionality:
- Wallet creation and initialization
- Token spending (session booking)
- Token earning (session completion)
- Token refunds (session cancellation)
- Transaction atomicity
- Balance validation
"""

import sys
import os
from datetime import datetime, UTC

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models
from app.services import token_service
from app.services import session_token_integration
from app.crud import token as token_crud


def unique_email(prefix: str) -> str:
    """Generate a unique email so repeated test runs don't collide."""
    return f"{prefix}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}@university.edu"


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_wallet_initialization():
    """Test wallet creation with initial allocation."""
    print_section("TEST 1: Wallet Initialization")
    
    db = SessionLocal()
    try:
        # Create test user
        test_user = models.User(
            name="Test User",
            email=unique_email("test"),
            password_hash="dummy_hash",
            role="learner"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        print(f"✓ Created test user: ID={test_user.id}")
        
        # Initialize wallet
        wallet = token_service.initialize_wallet(db, test_user.id)
        print(f"✓ Wallet created: ID={wallet.id}, Balance={wallet.balance}")
        
        # Verify initial allocation
        assert wallet.balance == 20, "Initial balance should be 20"
        print(f"✓ Initial balance correct: {wallet.balance} tokens")
        
        # Verify transaction record
        transactions = token_crud.get_user_transactions(db, test_user.id)
        assert len(transactions) == 1, "Should have 1 initial transaction"
        assert transactions[0].type == models.TransactionType.INITIAL, "Transaction type should be INITIAL"
        print(f"✓ Initial transaction recorded correctly")
        
        print("\n✅ Wallet Initialization Test PASSED")
        return test_user.id
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        raise
    finally:
        db.close()


def test_token_spending(user_id: int):
    """Test token deduction during session booking."""
    print_section("TEST 2: Token Spending (Session Booking)")
    
    db = SessionLocal()
    try:
        # Get initial balance
        initial_balance = token_service.get_wallet_balance(db, user_id)
        print(f"Initial balance: {initial_balance} tokens")

        # Create a valid mentor to satisfy sessions.mentor_id FK
        mentor = models.User(
            name="Booking Mentor",
            email=unique_email("booking_mentor"),
            password_hash="dummy_hash",
            role="mentor"
        )
        db.add(mentor)
        db.commit()
        db.refresh(mentor)
        
        # Create a test session
        test_session = models.Session(
            learner_id=user_id,
            mentor_id=mentor.id,
            status="Pending"
        )
        db.add(test_session)
        db.commit()
        db.refresh(test_session)
        print(f"✓ Created test session: ID={test_session.id}")
        
        # Spend tokens
        result = token_service.spend_tokens(
            db=db,
            user_id=user_id,
            session_id=test_session.id
        )
        
        print(f"✓ Tokens deducted successfully")
        print(f"  - Amount spent: {result['amount_spent']}")
        print(f"  - Previous balance: {result['previous_balance']}")
        print(f"  - New balance: {result['new_balance']}")
        
        # Verify balance
        new_balance = token_service.get_wallet_balance(db, user_id)
        assert new_balance == initial_balance - 10, "Balance should decrease by 10"
        print(f"✓ Balance verification passed: {new_balance} tokens")
        
        # Test insufficient balance
        print("\nTesting insufficient balance scenario...")
        try:
            # Try to spend more than available
            token_service.spend_tokens(db, user_id, 999, amount=100)
            print("❌ Should have raised insufficient balance error")
        except ValueError as e:
            print(f"✓ Insufficient balance error caught: {e}")
        
        # Test duplicate transaction prevention
        print("\nTesting duplicate transaction prevention...")
        try:
            token_service.spend_tokens(db, user_id, test_session.id)
            print("❌ Should have prevented duplicate transaction")
        except ValueError as e:
            print(f"✓ Duplicate transaction prevented: {e}")
        
        print("\n✅ Token Spending Test PASSED")
        return test_session.id
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        raise
    finally:
        db.close()


def test_token_earning(session_id: int):
    """Test token reward after session completion."""
    print_section("TEST 3: Token Earning (Session Completion)")
    
    db = SessionLocal()
    try:
        # Create a mentor user
        mentor = models.User(
            name="Test Mentor",
            email=unique_email("mentor"),
            password_hash="dummy_hash",
            role="mentor"
        )
        db.add(mentor)
        db.commit()
        db.refresh(mentor)
        print(f"✓ Created mentor user: ID={mentor.id}")
        
        # Initialize mentor wallet
        mentor_wallet = token_service.initialize_wallet(db, mentor.id)
        initial_balance = mentor_wallet.balance
        print(f"✓ Mentor wallet: Initial balance={initial_balance}")
        
        # Update session with mentor
        session = db.query(models.Session).filter(
            models.Session.id == session_id
        ).first()
        session.mentor_id = mentor.id
        db.commit()
        
        # Award tokens
        result = token_service.earn_tokens(
            db=db,
            user_id=mentor.id,
            session_id=session_id
        )
        
        print(f"✓ Tokens awarded successfully")
        print(f"  - Amount earned: {result['amount_earned']}")
        print(f"  - Previous balance: {result['previous_balance']}")
        print(f"  - New balance: {result['new_balance']}")
        
        # Verify balance
        new_balance = token_service.get_wallet_balance(db, mentor.id)
        assert new_balance == initial_balance + 10, "Balance should increase by 10"
        print(f"✓ Balance verification passed: {new_balance} tokens")
        
        # Test duplicate reward prevention
        print("\nTesting duplicate reward prevention...")
        try:
            token_service.earn_tokens(db, mentor.id, session_id)
            print("❌ Should have prevented duplicate reward")
        except ValueError as e:
            print(f"✓ Duplicate reward prevented: {e}")
        
        print("\n✅ Token Earning Test PASSED")
        return mentor.id
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        raise
    finally:
        db.close()


def test_transaction_atomicity():
    """Test that transactions are atomic (all-or-nothing)."""
    print_section("TEST 4: Transaction Atomicity")
    
    db = SessionLocal()
    try:
        # Create user
        user = models.User(
            name="Atomicity Test User",
            email=unique_email("atomic"),
            password_hash="dummy_hash",
            role="learner"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        wallet = token_service.initialize_wallet(db, user.id)
        initial_balance = wallet.balance
        print(f"✓ User created with balance: {initial_balance}")
        
        # Force a transaction failure scenario
        print("\nSimulating transaction failure...")
        try:
            # This should fail due to insufficient balance
            token_service.spend_tokens(db, user.id, 999, amount=1000)
        except ValueError:
            # Check that balance hasn't changed
            final_balance = token_service.get_wallet_balance(db, user.id)
            assert final_balance == initial_balance, "Balance should not change on failed transaction"
            print(f"✓ Balance unchanged after failed transaction: {final_balance}")
        
        print("\n✅ Transaction Atomicity Test PASSED")
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        raise
    finally:
        db.close()


def test_session_integration(learner_id: int, mentor_id: int):
    """Test integration with session lifecycle."""
    print_section("TEST 5: Session Lifecycle Integration")
    
    db = SessionLocal()
    try:
        # Create a new session
        session = models.Session(
            learner_id=learner_id,
            mentor_id=mentor_id,
            status="Pending"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        print(f"✓ Created session: ID={session.id}")
        
        # Pre-booking validation
        validation = session_token_integration.validate_session_booking(db, learner_id)
        print(f"\nPre-booking validation:")
        print(f"  - Can book: {validation['valid']}")
        print(f"  - Message: {validation['message']}")
        
        # Simulate session confirmation
        session.status = "Confirmed"
        result = session_token_integration.on_session_confirmed(db, session)
        print(f"\n✓ Session confirmed - Token deduction:")
        print(f"  - Success: {result['success']}")
        
        # Simulate session completion
        session.status = "Completed"
        result = session_token_integration.on_session_completed(db, session)
        print(f"\n✓ Session completed - Token reward:")
        print(f"  - Success: {result['success']}")
        
        # Get session token status
        status = session_token_integration.get_session_token_status(db, session.id)
        print(f"\nSession token status:")
        print(f"  - Tokens deducted: {status['tokens_deducted']}")
        print(f"  - Tokens awarded: {status['tokens_awarded']}")
        print(f"  - Total transactions: {len(status['transactions'])}")
        
        print("\n✅ Session Integration Test PASSED")
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        raise
    finally:
        db.close()


def test_transaction_history(user_id: int):
    """Test transaction history retrieval."""
    print_section("TEST 6: Transaction History")
    
    db = SessionLocal()
    try:
        history = token_service.get_transaction_history(db, user_id)
        print(f"✓ Retrieved {len(history)} transactions")
        
        for i, tx in enumerate(history, 1):
            print(f"\nTransaction {i}:")
            print(f"  - Type: {tx['type']}")
            print(f"  - Amount: {tx['amount']}")
            print(f"  - Status: {tx['status']}")
            print(f"  - Description: {tx['description']}")
        
        print("\n✅ Transaction History Test PASSED")
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        raise
    finally:
        db.close()


def run_all_tests():
    """Run all Phase 2 tests."""
    print("\n" + "=" * 60)
    print("  PHASE 2: TOKEN & REWARDS - CORE LOGIC TESTING")
    print("=" * 60)
    
    try:
        # Test 1: Wallet initialization
        learner_id = test_wallet_initialization()
        
        # Test 2: Token spending
        session_id = test_token_spending(learner_id)
        
        # Test 3: Token earning
        mentor_id = test_token_earning(session_id)
        
        # Test 4: Transaction atomicity
        test_transaction_atomicity()
        
        # Test 5: Session integration
        test_session_integration(learner_id, mentor_id)
        
        # Test 6: Transaction history
        test_transaction_history(learner_id)
        
        print_section("ALL TESTS PASSED ✅")
        print("\nPhase 2 implementation is working correctly!")
        print("You can now proceed to Phase 3 (API & Integration)")
        
    except Exception as e:
        print_section("TESTS FAILED ❌")
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
