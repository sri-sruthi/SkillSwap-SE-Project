# app/schemas/user.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    role: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
        
class UserProfileBase(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileUpdate(UserProfileBase):
    pass

class UserProfile(UserProfileBase):
    id: int
    user_id: int
    
    class Config:
        from_attributes = True

class TokenWalletResponse(BaseModel):
    balance: int
    
    class Config:
        from_attributes = True