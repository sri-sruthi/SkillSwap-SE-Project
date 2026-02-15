# app/api/auth.py - COMPLETE CORRECTED VERSION

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.utils.security import get_password_hash, verify_password, create_access_token
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import timedelta

# The prefix "/auth" ensures this router handles "POST /auth/register"
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ===== REQUEST/RESPONSE MODELS =====

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    # Bcrypt has a 72-byte limit. Setting max_length=72 prevents server crashes.
    password: str = Field(..., min_length=6, max_length=72)
    role: str
    qualification: Optional[str] = None
    studying: Optional[str] = None
    learning_goals: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str


# ===== REGISTER ENDPOINT =====

@router.post("/register")
async def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register new user with role-specific profile logic"""
    
    # 1. Validate role
    if user_data.role not in ["mentor", "learner"]:
        raise HTTPException(
            status_code=400,
            detail="Role must be 'mentor' or 'learner'"
        )
    
    # 2. Check if email already exists
    existing = db.query(models.User).filter(
        models.User.email == user_data.email
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    try:
        # 3. Handle Bcrypt's 72-byte limit manually as a safety net
        # This ensures get_password_hash never receives > 72 characters.
        safe_password = user_data.password[:72]
        password_hash = get_password_hash(safe_password)
        
        # 4. Create User record
        new_user = models.User(
            name=user_data.name,
            email=user_data.email,
            password_hash=password_hash,
            role=user_data.role,
            is_active=True
        )
        db.add(new_user)
        db.flush() # Get user ID before creating profile
        
        # 5. Create Profile record based on role
        profile = models.UserProfile(
            user_id=new_user.id,
            full_name=user_data.name,
            qualification=user_data.qualification if user_data.role == "mentor" else None,
            studying=user_data.studying if user_data.role == "learner" else None,
            bio=user_data.learning_goals if user_data.role == "learner" else None
        )
        db.add(profile)
        
        # 6. Initialize Wallet (20 tokens)
        wallet = models.TokenWallet(user_id=new_user.id, balance=20)
        db.add(wallet)
        
        db.commit()
        db.refresh(new_user)
        
        return {
            "message": "Registration successful",
            "user_id": new_user.id,
            "email": new_user.email,
            "role": new_user.role
        }

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        # Log the error for debugging but send a clean 500 to user
        print(f"Registration error: {repr(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ===== LOGIN ENDPOINT =====

@router.post("/login", response_model=Token)
async def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    """Verify credentials and return access token"""
    
    user = db.query(models.User).filter(
        models.User.email == credentials.email
    ).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }
