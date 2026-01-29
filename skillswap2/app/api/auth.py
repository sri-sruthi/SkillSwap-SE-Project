from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import Token, UserCreate, User, LoginRequest
from app.crud.user import get_user_by_email, create_user
from app.utils.security import authenticate_user, create_access_token, get_current_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])





@router.post("/register", response_model=User)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    new_user = create_user(db, user)
    return new_user


@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_data.email, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    

    return {
    "access_token": access_token,
    "token_type": "bearer",
    "role": user.role
    }
