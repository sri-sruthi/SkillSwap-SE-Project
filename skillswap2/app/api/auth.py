from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.utils.security import get_password_hash, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


# ============================
# REGISTER
# ============================

@router.post("/register")
def register_user(
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),

    full_name: str = Form(...),

    # learner optional fields
    phone: str = Form(None),
    bio: str = Form(None),
    studying: str = Form(None),

    db: Session = Depends(get_db)
):

    # Check existing user
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    # Create user
    user = models.User(
        email=email,
        password_hash=get_password_hash(password),
        role=role
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Create profile for both mentor & learner
    profile = models.UserProfile(
        user_id=user.id,
        full_name=full_name,
        phone=phone,
        bio=bio,
        studying=studying
    )

    db.add(profile)
    db.commit()

    return {"message": "Registered successfully"}


# ============================
# LOGIN
# ============================

@router.post("/login")
def login_user(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Wrong password")

    # Return role for redirect
    return {
        "message": "Login successful",
        "role": user.role
    }
