from sqlalchemy.orm import Session
from app import models, schemas
from app.utils.security import get_password_hash
from datetime import datetime

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        email=user.email,
        password_hash=get_password_hash(user.password),
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def create_user_profile(db: Session, profile: schemas.UserProfileCreate, user_id: int):
    db_profile = models.UserProfile(**profile.dict(), user_id=user_id)
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

def get_user_profile(db: Session, user_id: int):
    return db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()

def update_user_profile(db: Session, user_id: int, profile_update: schemas.UserProfileUpdate):
    db_profile = get_user_profile(db, user_id)
    if db_profile:
        update_data = profile_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_profile, key, value)
        db.commit()
        db.refresh(db_profile)
    return db_profile

def create_token_wallet(db: Session, user_id: int):
    wallet = models.TokenWallet(user_id=user_id, balance=0)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet

def get_token_wallet(db: Session, user_id: int):
    return db.query(models.TokenWallet).filter(models.TokenWallet.user_id == user_id).first()