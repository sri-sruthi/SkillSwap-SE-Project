from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


# ======================
# USER AUTHENTICATION SCHEMAS
# ======================

class UserBase(BaseModel):
    email: EmailStr
    # End-user accounts are typically "student"; "admin" is reserved.
    role: str = "student"


class UserCreate(UserBase):
    name: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: int
    name: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ======================
# PROFILE SCHEMAS
# ======================

class UserProfileBase(BaseModel):
    full_name: str
    phone: Optional[str] = None
    age: Optional[int] = None


class UserProfileCreate(UserProfileBase):
    user_id: int
    qualification: Optional[str] = None
    experience: Optional[str] = None
    studying: Optional[str] = None
    bio: Optional[str] = None


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    qualification: Optional[str] = None
    experience: Optional[str] = None
    studying: Optional[str] = None
    bio: Optional[str] = None


class MentorProfileUpdate(UserProfileBase):
    qualification: str
    experience: Optional[str] = None


class LearnerProfileUpdate(UserProfileBase):
    studying: str
    bio: str


class UserProfile(UserProfileBase):
    id: int
    user_id: int
    qualification: Optional[str] = None
    experience: Optional[str] = None
    studying: Optional[str] = None
    bio: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ======================
# TOKEN WALLET SCHEMA
# ======================

class TokenWalletResponse(BaseModel):
    balance: int

    model_config = ConfigDict(from_attributes=True)


# ======================
# PROFILE DISPLAY FOR FRONTEND
# ======================

class UserProfileDisplay(BaseModel):
    full_name: str
    phone: Optional[str] = None
    age: Optional[int] = None
    qualification: Optional[str] = None
    experience: Optional[str] = None
    studying: Optional[str] = None
    bio: Optional[str] = None


class UserDisplay(BaseModel):
    id: int
    email: str
    name: str
    role: str
    profile: UserProfileDisplay

    model_config = ConfigDict(from_attributes=True)


# ======================
# PASSWORD UPDATE
# ======================

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str
