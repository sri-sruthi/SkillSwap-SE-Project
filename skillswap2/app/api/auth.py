from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.utils.security import get_password_hash, verify_password, create_access_token
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ===== REQUEST/RESPONSE MODELS =====

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    # Bcrypt limit is 72 bytes; max_length=72 prevents the "password too long" crash
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
async def register(user_data: RegisterRequest, db: Session = Depends(get_db)):
    """Register new user and create associated profile"""
    if user_data.role not in ["mentor", "learner"]:
        raise HTTPException(status_code=400, detail="Role must be 'mentor' or 'learner'")
    
    existing = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    try:
        # Hashing only the first 72 characters to ensure Bcrypt compatibility
        password_hash = get_password_hash(user_data.password[:72])
        
        new_user = models.User(
            name=user_data.name,
            email=user_data.email,
            password_hash=password_hash,
            role=user_data.role,
            is_active=True
        )
        db.add(new_user)
        db.flush()
        
        profile = models.UserProfile(
            user_id=new_user.id,
            full_name=user_data.name,
            qualification=user_data.qualification if user_data.role == "mentor" else None,
            studying=user_data.studying if user_data.role == "learner" else None,
            bio=user_data.learning_goals if user_data.role == "learner" else None
        )
        db.add(profile)
        
        # Initialize wallet with default balance
        wallet = models.TokenWallet(user_id=new_user.id, balance=100)
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
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }