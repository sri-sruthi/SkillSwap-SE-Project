from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# ======================
# SESSION REQUEST MODELS
# ======================

class SessionCreate(BaseModel):
    mentor_id: int
    skill_id: Optional[int] = None
    scheduled_time: Optional[datetime] = None
    notes: Optional[str] = None

class SessionRequest(BaseModel):
    """For frontend session request form"""
    mentor_id: int
    skill_id: int
    scheduled_time: str  # ISO format string from frontend
    notes: Optional[str] = None

# ======================
# SESSION UPDATE MODELS
# ======================

class SessionStatusUpdate(BaseModel):
    status: str  # "Confirmed", "Cancelled", "Completed"

class SessionReschedule(BaseModel):
    new_time: str  # ISO format string
    reason: Optional[str] = None

# ======================
# SESSION RESPONSE MODELS
# ======================

class SessionBase(BaseModel):
    id: int
    learner_id: int
    mentor_id: int
    skill_id: Optional[int] = None
    scheduled_time: Optional[datetime] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class Session(SessionBase):
    model_config = ConfigDict(from_attributes=True)


class SessionResponse(SessionBase):
    """Detailed session response used by session API list endpoints."""
    learner_name: Optional[str] = None
    mentor_name: Optional[str] = None
    mentor_qualification: Optional[str] = None
    skill_name: Optional[str] = None
    awaiting_my_confirmation: bool = False
    is_reschedule_pending: bool = False

    model_config = ConfigDict(from_attributes=True)

# ======================
# SESSION DISPLAY FOR FRONTEND
# ======================

class SessionDisplay(BaseModel):
    id: int
    learner_name: str
    mentor_name: str
    skill_name: Optional[str] = None
    scheduled_time: Optional[str] = None  # ISO string for frontend
    status: str
    notes: Optional[str] = None
    created_at: str  # ISO string

class MentorSessionDisplay(BaseModel):
    """For mentor dashboard"""
    id: int
    learner_name: str
    learner_email: str
    skill_name: Optional[str] = None
    scheduled_time: Optional[str] = None
    status: str
    notes: Optional[str] = None

class LearnerSessionDisplay(BaseModel):
    """For learner dashboard"""
    id: int
    mentor_name: str
    mentor_qualification: Optional[str] = None
    skill_name: Optional[str] = None
    scheduled_time: Optional[str] = None
    status: str
    notes: Optional[str] = None
