from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# ======================
# USER AUTHENTICATION SCHEMAS
# ======================

class UserBase(BaseModel):
    email: EmailStr
    role: str  # "mentor" or "learner"

class UserCreate(UserBase):
    name: str  # Full name at registration
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int
    name: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ======================
# PROFILE SCHEMAS
# ======================

class UserProfileBase(BaseModel):
    full_name: str
    phone: Optional[str] = None
    age: Optional[int] = None

class MentorProfileUpdate(UserProfileBase):
    qualification: str
    experience: Optional[str] = None

class LearnerProfileUpdate(UserProfileBase):
    studying: str  # College/university
    bio: str       # What they want to learn

class UserProfile(UserProfileBase):
    id: int
    user_id: int
    # Role-specific fields
    qualification: Optional[str] = None
    experience: Optional[str] = None
    studying: Optional[str] = None
    bio: Optional[str] = None
    
    class Config:
        from_attributes = True

# ======================
# TOKEN WALLET SCHEMA
# ======================

class TokenWalletResponse(BaseModel):
    balance: int
    
    class Config:
        from_attributes = True

# ======================
# PROFILE DISPLAY FOR FRONTEND
# ======================

class UserProfileDisplay(BaseModel):
    full_name: str
    phone: Optional[str] = None
    age: Optional[int] = None
    # Mentor fields
    qualification: Optional[str] = None
    experience: Optional[str] = None
    # Learner fields  
    studying: Optional[str] = None
    bio: Optional[str] = None

class UserDisplay(BaseModel):
    id: int
    email: str
    name: str
    role: str
    profile: UserProfileDisplay

    class Config:
        from_attributes = True

# ======================
# PASSWORD UPDATE
# ======================

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str
# Add this with your other UserProfile classes
class UserProfileCreate(UserProfileBase):
    user_id: int
    # Mentor-specific fields
    qualification: Optional[str] = None
    experience: Optional[str] = None
    # Learner-specific fields  
    studying: Optional[str] = None
    bio: Optional[str] = None
# Add this with your other profile classes
class UserProfileUpdate(UserProfileBase):
    # Keep all fields optional for partial updates
    full_name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    qualification: Optional[str] = None
    experience: Optional[str] = None
    studying: Optional[str] = None
    bio: Optional[str] = None

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

class UserProfileUpdate(UserProfileBase):
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
    
    class Config:
        from_attributes = True