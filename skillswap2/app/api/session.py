# skillswap2/app/api/session.py
"""
Session Management API with Token Integration
Phase 3: Integrated token deduction/reward logic
"""

from fastapi import APIRouter, Depends, HTTPException, Form, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, UTC, timedelta

from app.database import get_db
from app.models import session as models
from app.models.skill import Skill, UserSkill
from app.models.user import User
from app.services import notification_service
from app.utils.security import get_current_user
from app.schemas.session import SessionResponse

# ✅ NEW: Import token service functions
from app.services.token_service import (
    spend_tokens_for_session,
    reward_tokens_for_session,
    refund_tokens_for_session,
    get_wallet_balance
)

router = APIRouter(prefix="/sessions", tags=["sessions"])
TEACH_SKILL_TYPES = ("teach", "offer")


# ======================
# HELPER FUNCTIONS
# ======================
def _create_notification(
    db: Session,
    recipient_id: int,
    actor_id: int,
    session_id: int,
    event_type: str,
    message: str,
):
    """Create in-app notification for a session event."""
    return notification_service.create_notification(
        db,
        recipient_id=recipient_id,
        actor_id=actor_id,
        session_id=session_id,
        event_type=event_type,
        message=message,
    )


def _dispatch_notification_email(db: Session, notification) -> None:
    """Best-effort email dispatch that must not break request success."""
    if not notification:
        return
    notification_service.dispatch_email_for_notification(db, notification)


def _get_counterparty_id(session: models.Session, current_user_id: int) -> int:
    """Get the other party in a session"""
    return session.mentor_id if session.learner_id == current_user_id else session.learner_id


def _get_reconfirm_user_id(session: models.Session) -> Optional[int]:
    """Extract reconfirm user ID from system tags"""
    if not session.notes:
        return None
    if "[SYSTEM:RECONFIRM:" in session.notes:
        import re
        match = re.search(r"\[SYSTEM:RECONFIRM:(\d+)\]", session.notes)
        if match:
            return int(match.group(1))
    return None


def _extract_prev_time(notes: Optional[str]) -> Optional[datetime]:
    """Extract previous time from system tags"""
    if not notes:
        return None
    if "[SYSTEM:PREV_TIME:" in notes:
        import re
        match = re.search(r"\[SYSTEM:PREV_TIME:(.*?)\]", notes)
        if match:
            try:
                return datetime.fromisoformat(match.group(1))
            except:
                return None
    return None


def _strip_system_tags(notes: Optional[str]) -> Optional[str]:
    """Remove system tags from notes"""
    if not notes:
        return notes
    import re
    cleaned = re.sub(r"\[SYSTEM:.*?\]", "", notes)
    return cleaned.strip() if cleaned.strip() else None


def _awaiting_my_confirmation(session: models.Session, current_user_id: int) -> bool:
    """
    For pending sessions:
    - Initial request => mentor confirms
    - Reschedule request => tagged reconfirm user confirms
    """
    if session.status != "Pending":
        return False
    reconfirm_user_id = _get_reconfirm_user_id(session)
    if reconfirm_user_id is not None:
        return reconfirm_user_id == current_user_id
    return session.mentor_id == current_user_id


def _is_reschedule_pending(session: models.Session) -> bool:
    """True when a pending session is waiting on reschedule reconfirmation."""
    if session.status != "Pending":
        return False
    return _get_reconfirm_user_id(session) is not None


# ======================
# SESSION LISTING
# ======================
@router.get("/", response_model=List[SessionResponse])
@router.get("/my", response_model=List[SessionResponse])
def get_sessions(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all sessions for current user, optionally filtered by status"""
    query = db.query(models.Session).filter(
        (models.Session.learner_id == current_user.id) | 
        (models.Session.mentor_id == current_user.id)
    )
    
    if status:
        query = query.filter(models.Session.status == status)
    
    sessions = query.order_by(models.Session.scheduled_time.desc()).all()
    
    return [
        SessionResponse(
            id=s.id,
            learner_id=s.learner_id,
            mentor_id=s.mentor_id,
            skill_id=s.skill_id,
            scheduled_time=s.scheduled_time,
            status=s.status,
            notes=_strip_system_tags(s.notes),
            learner_name=s.learner.name if s.learner else None,
            mentor_name=s.mentor.name if s.mentor else None,
            mentor_qualification=(
                s.mentor.profile.qualification
                if s.mentor and getattr(s.mentor, "profile", None)
                else None
            ),
            skill_name=(
                s.skill.title
                if s.skill and getattr(s.skill, "title", None) is not None
                else (s.skill.name if s.skill and getattr(s.skill, "name", None) is not None else None)
            ),
            awaiting_my_confirmation=_awaiting_my_confirmation(s, current_user.id),
            is_reschedule_pending=_is_reschedule_pending(s),
            created_at=s.created_at,
            updated_at=s.updated_at
        )
        for s in sessions
    ]


@router.get("/pending", response_model=List[SessionResponse])
def get_pending_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Backward-compatible endpoint used by older frontend polling code."""
    return get_sessions(status="Pending", current_user=current_user, db=db)


# ======================
# CREATE SESSION REQUEST
# ======================
@router.post("/request")
@router.post("/")
def create_session_request(
    mentor_id: int = Form(...),
    skill_id: int = Form(...),
    scheduled_time: str = Form(...),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new session request.
    
    ✅ PHASE 3 UPDATE: No token deduction yet (deducted on accept/confirm)
    """
    
    # ✅ NEW: Check token eligibility BEFORE creating request
    try:
        learner_balance = get_wallet_balance(db, current_user.id)
        if learner_balance < 10:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient tokens. You have {learner_balance} tokens, but need 10 to book a session."
            )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Prevent self-mentoring
    if mentor_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot create session with yourself"
        )
    
    # Verify mentor exists
    mentor = db.query(User).filter(User.id == mentor_id).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")

    # Verify skill exists
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Capability check: selected mentor must teach the selected skill
    mentor_teaches_skill = db.query(UserSkill.id).filter(
        UserSkill.user_id == mentor_id,
        UserSkill.skill_id == skill_id,
        UserSkill.skill_type.in_(TEACH_SKILL_TYPES),
    ).first()
    if not mentor_teaches_skill:
        raise HTTPException(
            status_code=400,
            detail="Selected mentor does not teach this skill"
        )
    
    # Parse scheduled time
    try:
        scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
        scheduled_dt = scheduled_dt.replace(microsecond=0)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid scheduled_time format. Use ISO 8601 (e.g., '2026-02-20T14:00:00')"
        )

    # Prevent accidental duplicate requests (double-clicks/retries).
    # Treat same learner+mentor+skill within +/-1 minute as duplicate while active.
    existing_active = db.query(models.Session).filter(
        models.Session.learner_id == current_user.id,
        models.Session.mentor_id == mentor_id,
        models.Session.skill_id == skill_id,
        models.Session.status.in_(["Pending", "Confirmed"]),
        models.Session.scheduled_time >= (scheduled_dt - timedelta(minutes=1)),
        models.Session.scheduled_time <= (scheduled_dt + timedelta(minutes=1)),
    ).order_by(models.Session.created_at.desc()).first()

    if existing_active:
        return {
            "message": "An active session request already exists for this mentor, skill, and time.",
            "session_id": existing_active.id,
            "status": existing_active.status,
            "note": "Duplicate request prevented; existing session returned."
        }
    
    # Create session
    new_session = models.Session(
        learner_id=current_user.id,
        mentor_id=mentor_id,
        skill_id=skill_id,
        scheduled_time=scheduled_dt,
        status="Pending",
        notes=notes
    )
    db.add(new_session)
    db.flush()
    
    # Notify mentor
    created_notification = _create_notification(
        db=db,
        recipient_id=mentor_id,
        actor_id=current_user.id,
        session_id=new_session.id,
        event_type="session_requested",
        message=f"{current_user.name} requested a session with you."
    )
    
    db.commit()
    _dispatch_notification_email(db, created_notification)
    db.refresh(new_session)
    
    return {
        "message": "Session request created successfully",
        "session_id": new_session.id,
        "status": "Pending",
        "note": "Tokens will be deducted when the assigned mentor accepts this request."
    }


# ======================
# ACCEPT SESSION (Token Deduction Happens Here)
# ======================
@router.patch("/{session_id}/accept")
def accept_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accept a pending session.
    
    ✅ PHASE 3 UPDATE: Deduct tokens from learner when mentor accepts
    """
    
    session = db.query(models.Session).filter(
        models.Session.id == session_id,
        models.Session.status == "Pending"
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Pending session not found"
        )

    if session.learner_id != current_user.id and session.mentor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this session")

    reconfirm_user_id = _get_reconfirm_user_id(session)
    if reconfirm_user_id is not None:
        if reconfirm_user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Reschedule must be confirmed by the other party"
            )
    elif session.mentor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the assigned mentor can accept new session requests"
        )
    
    tokens_deducted = 0
    # Initial confirmation deducts tokens; reschedule reconfirmation does not.
    if reconfirm_user_id is None:
        try:
            spend_tokens_for_session(db, session.learner_id, session.id)
            tokens_deducted = 10
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Token deduction failed: {str(e)}"
            )
    
    session.status = "Confirmed"
    session.notes = _strip_system_tags(session.notes)
    
    created_notification = None
    if reconfirm_user_id is not None:
        created_notification = _create_notification(
            db=db,
            recipient_id=_get_counterparty_id(session, current_user.id),
            actor_id=current_user.id,
            session_id=session.id,
            event_type="session_reschedule_accepted",
            message=f"{current_user.name} accepted your reschedule request."
        )
    else:
        created_notification = _create_notification(
            db=db,
            recipient_id=session.learner_id,
            actor_id=current_user.id,
            session_id=session.id,
            event_type="session_confirmed",
            message=f"{current_user.name} accepted your session request. 10 tokens have been deducted."
        )
    
    if hasattr(session, 'updated_at'):
        session.updated_at = datetime.now(UTC)
    
    db.commit()
    _dispatch_notification_email(db, created_notification)
    
    return {
        "message": (
            "Session confirmed and tokens deducted"
            if tokens_deducted > 0
            else "Reschedule confirmed"
        ),
        "status": "Confirmed",
        "tokens_deducted": tokens_deducted
    }


# ======================
# DECLINE SESSION
# ======================
@router.patch("/{session_id}/decline")
def decline_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Decline a pending session.
    
    ✅ PHASE 3 UPDATE: No token changes (session never confirmed)
    """
    
    session = db.query(models.Session).filter(
        models.Session.id == session_id,
        models.Session.status == "Pending"
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Pending session not found"
        )

    if session.learner_id != current_user.id and session.mentor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this session")

    reconfirm_user_id = _get_reconfirm_user_id(session)
    created_notification = None
    if reconfirm_user_id is not None:
        if reconfirm_user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Reschedule must be declined by the other party"
            )
        prev_time = _extract_prev_time(session.notes)
        if prev_time is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Cannot decline this reschedule because previous confirmed time metadata "
                    "is missing. Ask the requester to send a new reschedule request."
                ),
            )
        session.status = "Confirmed"
        session.scheduled_time = prev_time
        response_status = "Confirmed"
        response_message = "Reschedule declined; previous confirmed slot retained"
        created_notification = _create_notification(
            db=db,
            recipient_id=_get_counterparty_id(session, current_user.id),
            actor_id=current_user.id,
            session_id=session.id,
            event_type="session_reschedule_declined",
            message=f"{current_user.name} declined your reschedule request. Previous confirmed slot remains active."
        )
    elif session.mentor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the assigned mentor can decline new session requests"
        )
    else:
        session.status = "Cancelled"
        response_status = "Cancelled"
        response_message = "Session declined (no tokens deducted)"
        created_notification = _create_notification(
            db=db,
            recipient_id=session.learner_id,
            actor_id=current_user.id,
            session_id=session.id,
            event_type="session_declined",
            message=f"{current_user.name} declined your session request."
        )
    
    session.notes = _strip_system_tags(session.notes)
    
    if hasattr(session, 'updated_at'):
        session.updated_at = datetime.now(UTC)
    
    db.commit()
    _dispatch_notification_email(db, created_notification)
    
    return {
        "message": response_message,
        "status": response_status
    }


# ======================
# COMPLETE SESSION (Token Reward Happens Here)
# ======================
@router.patch("/{session_id}/complete")
def complete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark session as completed.
    
    ✅ PHASE 3 UPDATE: Reward tokens to mentor when session completed
    """
    
    session = db.query(models.Session).filter(
        models.Session.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check authorization
    if session.learner_id != current_user.id and session.mentor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to complete this session"
        )
    
    # Can only complete confirmed sessions
    if session.status != "Confirmed":
        raise HTTPException(
            status_code=400,
            detail="Only confirmed sessions can be marked as completed"
        )
    
    # ✅ NEW: Reward tokens to mentor
    try:
        reward_tokens_for_session(db, session.mentor_id, session.id)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Token reward failed: {str(e)}"
        )
    
    session.status = "Completed"
    
    created_notification = _create_notification(
        db=db,
        recipient_id=_get_counterparty_id(session, current_user.id),
        actor_id=current_user.id,
        session_id=session.id,
        event_type="session_completed",
        message=f"{current_user.name} marked the session as completed. Mentor received 10 tokens!"
    )
    
    if hasattr(session, 'updated_at'):
        session.updated_at = datetime.now(UTC)
    
    db.commit()
    _dispatch_notification_email(db, created_notification)
    
    return {
        "message": "Session marked as completed and mentor rewarded",
        "status": "Completed",
        "tokens_rewarded": 10
    }


# ======================
# CANCEL SESSION (Token Refund if Applicable)
# ======================
@router.patch("/{session_id}/cancel")
def cancel_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a session.
    
    ✅ PHASE 3 UPDATE: Refund tokens if session was confirmed (tokens already deducted)
    """
    
    session = db.query(models.Session).filter(
        models.Session.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check authorization
    if session.learner_id != current_user.id and session.mentor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to cancel this session"
        )
    
    # Can't cancel completed or already cancelled sessions
    if session.status not in ["Pending", "Confirmed"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel this session (already completed or cancelled)"
        )
    
    # ✅ NEW: Refund tokens if session was confirmed
    tokens_refunded = 0
    if session.status == "Confirmed":
        try:
            refund_tokens_for_session(db, session.learner_id, session.id)
            tokens_refunded = 10
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Token refund failed: {str(e)}"
            )
    
    session.status = "Cancelled"
    
    refund_message = f" 10 tokens refunded to learner." if tokens_refunded > 0 else ""
    
    created_notification = _create_notification(
        db=db,
        recipient_id=_get_counterparty_id(session, current_user.id),
        actor_id=current_user.id,
        session_id=session.id,
        event_type="session_cancelled",
        message=f"{current_user.name} cancelled the session.{refund_message}"
    )
    
    if hasattr(session, 'updated_at'):
        session.updated_at = datetime.now(UTC)
    
    db.commit()
    _dispatch_notification_email(db, created_notification)
    
    return {
        "message": f"Session cancelled{refund_message}",
        "status": "Cancelled",
        "tokens_refunded": tokens_refunded
    }


# ======================
# RESCHEDULE SESSION
# ======================
@router.patch("/{session_id}/reschedule")
async def reschedule_session(
    session_id: int,
    request: Request,
    new_time: Optional[str] = Form(None),
    reason: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reschedule a session (both parties can request).
    
    ✅ PHASE 3 UPDATE: No token changes during reschedule
    """
    
    session = db.query(models.Session).filter(
        models.Session.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check authorization
    if session.learner_id != current_user.id and session.mentor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to reschedule this session"
        )
    
    # Can only reschedule confirmed sessions
    if session.status != "Confirmed":
        raise HTTPException(
            status_code=400,
            detail="Only confirmed sessions can be rescheduled"
        )
    
    if not new_time:
        try:
            payload = await request.json()
        except Exception:
            payload = None

        if isinstance(payload, dict):
            new_time = payload.get("new_time") or payload.get("scheduled_time")
            if reason is None:
                reason = payload.get("reason")

    if not new_time:
        raise HTTPException(
            status_code=422,
            detail="new_time is required"
        )

    normalized_reason = reason.strip() if reason else ""

    # Parse new time
    try:
        new_dt = datetime.fromisoformat(new_time.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid new_time format. Use ISO 8601"
        )
    
    # Store original confirmed time (preserve across repeated reschedule attempts)
    existing_prev_time = _extract_prev_time(session.notes)
    prev_confirmed_time = existing_prev_time if existing_prev_time is not None else session.scheduled_time
    prev_time_tag = f"[SYSTEM:PREV_TIME:{prev_confirmed_time.isoformat()}]"
    reconfirm_tag = f"[SYSTEM:RECONFIRM:{_get_counterparty_id(session, current_user.id)}]"
    
    existing_notes = session.notes or ""
    existing_notes = _strip_system_tags(existing_notes)

    reschedule_note = f"[Rescheduled: {normalized_reason}]" if normalized_reason else "[Rescheduled]"
    if existing_notes:
        combined_notes = f"{existing_notes} {reschedule_note}".strip()
    else:
        combined_notes = reschedule_note

    session.notes = f"{prev_time_tag} {reconfirm_tag} {combined_notes}".strip()
    session.scheduled_time = new_dt
    session.status = "Pending"
    
    reason_text = f" Reason: {normalized_reason}" if normalized_reason else ""
    
    created_notification = _create_notification(
        db=db,
        recipient_id=_get_counterparty_id(session, current_user.id),
        actor_id=current_user.id,
        session_id=session.id,
        event_type="session_reschedule_requested",
        message=f"{current_user.name} requested to reschedule the session.{reason_text}"
    )
    
    if hasattr(session, 'updated_at'):
        session.updated_at = datetime.now(UTC)
    
    db.commit()
    _dispatch_notification_email(db, created_notification)
    
    return {
        "message": "Reschedule request sent (awaiting confirmation)",
        "status": "Pending",
        "new_time": new_dt.isoformat(),
        "note": "No token changes during reschedule"
    }
