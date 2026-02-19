from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.utils.security import get_password_hash, verify_password, create_access_token
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import re

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ===== REQUEST/RESPONSE MODELS =====

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    # Bcrypt limit is 72 bytes; max_length=72 prevents the "password too long" crash
    password: str = Field(..., min_length=6, max_length=72)
    role: Optional[str] = "student"
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


def is_allowed_signup_email(email: str) -> bool:
    normalized = email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalized):
        return False
    domain = normalized.split("@", 1)[1]
    return domain.endswith(".edu") or domain == "gmail.com"

# ===== REGISTER ENDPOINT =====

@router.post("/register")
async def register(user_data: RegisterRequest, db: Session = Depends(get_db)):
    """Register new user and create associated profile"""
    requested_role = (user_data.role or "student").strip().lower()
    if requested_role not in {"student", "mentor", "learner"}:
        raise HTTPException(
            status_code=400,
            detail="Role must be one of: student, mentor, learner"
        )
    # Canonicalize end-user accounts to a single dual-role role.
    canonical_role = "student"

    normalized_email = user_data.email.strip().lower()
    if not is_allowed_signup_email(normalized_email):
        raise HTTPException(
            status_code=400,
            detail="Only .edu or gmail.com email addresses are allowed",
        )
    
    existing = db.query(models.User).filter(models.User.email == normalized_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    try:
        # Hashing only the first 72 characters to ensure Bcrypt compatibility
        password_hash = get_password_hash(user_data.password[:72])
        
        new_user = models.User(
            name=user_data.name,
            email=normalized_email,
            password_hash=password_hash,
            role=canonical_role,
            is_active=True
        )
        db.add(new_user)
        db.flush()
        
        profile = models.UserProfile(
            user_id=new_user.id,
            full_name=user_data.name,
            qualification=user_data.qualification,
            studying=user_data.studying,
            bio=user_data.learning_goals
        )
        db.add(profile)
        
        # Initialize wallet with configured initial allocation policy (20 tokens).
        wallet = models.TokenWallet(user_id=new_user.id, balance=20)
        db.add(wallet)
        
        db.commit()
        return {"message": "Registration successful"}
        
    except Exception as e:
        db.rollback()
        print(f"Registration Error: {repr(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ===== LOGIN ENDPOINT =====

@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Verify credentials and return access token"""
    user = db.query(models.User).filter(
        models.User.email == credentials.email.strip().lower()
    ).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }


@router.post("/admin/login", response_model=Token)
async def admin_login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Login endpoint restricted to admin accounts only."""
    normalized_email = credentials.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == normalized_email).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")

    if (user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }
