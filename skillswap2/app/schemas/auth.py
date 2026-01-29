from pydantic import BaseModel, EmailStr
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str
    # ⚠️ DO NOT include user_id/role here — they’re not in the JWT
    # They should be fetched from DB using email (sub)

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None  # optional, but not used in decode

class LoginRequest(BaseModel):
    email: str
    password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str