from pydantic import BaseModel, EmailStr
from typing import Optional

# ======================
# TOKEN SCHEMAS
# ======================

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str  # Critical for frontend role-based redirects

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


# ======================
# USER AUTHENTICATION SCHEMAS
# ======================

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    name: str  # Full name at registration
    email: EmailStr
    password: str
    role: str  # "mentor" or "learner"

# ======================
# MENTOR-SPECIFIC REGISTRATION
# ======================

class MentorRegister(UserRegister):
    qualification: str

# ======================
# LEARNER-SPECIFIC REGISTRATION
# ======================

class LearnerRegister(UserRegister):
    college: str
    what_to_learn: str

# Add this with your other auth classes
class LoginRequest(BaseModel):
    email: EmailStr
    password: str