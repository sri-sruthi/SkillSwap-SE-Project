from pydantic import BaseModel, EmailStr
from typing import Optional

# ======================
# TOKEN SCHEMAS
# ======================

class Token(BaseModel):
    access_token: str
    token_type: str
    # Canonical runtime roles are "student" and "admin".
    # Legacy values may still appear in old tokens during migration windows.
    role: str

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
    # Dual-role default. API canonicalizes legacy mentor/learner input to student.
    role: Optional[str] = "student"

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
