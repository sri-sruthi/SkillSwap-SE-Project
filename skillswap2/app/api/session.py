# app/api/session.py - CORRECTED VERSION (No Duplicates)

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.database import get_db
from app import models
from app.utils.security import get_current_user

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ======================
# GET PENDING SESSIONS (For notification bell)
# ======================
@router.get("/pending")
def get_pending_sessions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get pending session requests
    - Mentors: See pending requests they need to accept
    - Learners: See pending requests they've sent
    """
    
    if current_user.role == "mentor":
        # Mentor sees requests waiting for their approval
        sessions = db.query(models.Session).filter(
            models.Session.mentor_id == current_user.id,
            models.Session.status == "Pending"
        ).all()
    else:
        # Learner sees their pending requests
        sessions = db.query(models.Session).filter(
            models.Session.learner_id == current_user.id,
            models.Session.status == "Pending"
        ).all()
    
    # Return basic info for notification bell
    return [
        {
            "id": s.id,
            "learner_id": s.learner_id,
            "mentor_id": s.mentor_id,
            "skill_id": s.skill_id,
            "scheduled_time": s.scheduled_time.isoformat() if s.scheduled_time else None,
            "notes": s.notes,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in sessions
    ]


# ======================
# GET MY SESSIONS (Both roles)
# ======================
@router.get("/my")
def get_my_sessions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all sessions for current user with full details
    """
    
    if current_user.role == "mentor":
        # Mentor: Get sessions where I'm teaching
        sessions = db.query(models.Session).filter(
            models.Session.mentor_id == current_user.id
        ).order_by(models.Session.created_at.desc()).all()
        
        result = []
        for s in sessions:
            # Get learner info
            learner = db.query(models.User).filter(
                models.User.id == s.learner_id
            ).first()
            
            # Get skill info
            skill = None
            if s.skill_id:
                skill = db.query(models.Skill).filter(
                    models.Skill.id == s.skill_id
                ).first()
            
            result.append({
                "id": s.id,
                "learner_id": s.learner_id,
                "learner_name": learner.name if learner else "Unknown",
                "learner_email": learner.email if learner else None,
                "skill_id": s.skill_id,
                "skill_name": skill.title if skill else "N/A",  # ✅ FIXED: .title instead of .name
                "scheduled_time": s.scheduled_time.isoformat() if s.scheduled_time else None,
                "status": s.status,
                "notes": s.notes,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if hasattr(s, 'updated_at') and s.updated_at else None
            })
        
        return result
    
    else:  # Learner
        # Learner: Get sessions where I'm learning
        sessions = db.query(models.Session).filter(
            models.Session.learner_id == current_user.id
        ).order_by(models.Session.created_at.desc()).all()
        
        result = []
        for s in sessions:
            # Get mentor info
            mentor = db.query(models.User).filter(
                models.User.id == s.mentor_id
            ).first()
            
            # Get mentor profile
            mentor_profile = None
            if mentor:
                mentor_profile = db.query(models.UserProfile).filter(
                    models.UserProfile.user_id == mentor.id
                ).first()
            
            # Get skill info
            skill = None
            if s.skill_id:
                skill = db.query(models.Skill).filter(
                    models.Skill.id == s.skill_id
                ).first()
            
            result.append({
                "id": s.id,
                "mentor_id": s.mentor_id,
                "mentor_name": mentor.name if mentor else "Unknown",
                "mentor_qualification": mentor_profile.qualification if mentor_profile else None,
                "skill_id": s.skill_id,
                "skill_name": skill.title if skill else "N/A",  # ✅ FIXED: .title instead of .name
                "scheduled_time": s.scheduled_time.isoformat() if s.scheduled_time else None,
                "status": s.status,
                "notes": s.notes,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if hasattr(s, 'updated_at') and s.updated_at else None
            })
        
        return result


# ======================
# CREATE SESSION (Learner requests)
# ======================
@router.post("/")
def create_session(
    mentor_id: int = Form(...),
    skill_id: Optional[int] = Form(None),
    scheduled_time: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Learner requests a session with a mentor
    """
    
    if current_user.role != "learner":
        raise HTTPException(
            status_code=403,
            detail="Only learners can request sessions"
        )
    
    # Validate mentor exists
    mentor = db.query(models.User).filter(
        models.User.id == mentor_id,
        models.User.role == "mentor"
    ).first()
    
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")
    
    # Parse scheduled_time if provided
    parsed_time = None
    if scheduled_time:
        try:
            parsed_time = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
            
            # Optional: Check if time is in the future
            if parsed_time <= datetime.utcnow():
                raise HTTPException(
                    status_code=400,
                    detail="Scheduled time must be in the future"
                )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date/time format. Use ISO format."
            )
    
    # Create session
    new_session = models.Session(
        learner_id=current_user.id,
        mentor_id=mentor_id,
        skill_id=skill_id,
        scheduled_time=parsed_time,
        status="Pending",
        notes=notes
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return {
        "message": "Session request sent successfully",
        "session_id": new_session.id,
        "status": new_session.status
    }


# ======================
# ACCEPT SESSION (Mentor)
# ======================
@router.patch("/{session_id}/accept")
def accept_session(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mentor accepts a pending session request
    """
    
    if current_user.role != "mentor":
        raise HTTPException(
            status_code=403,
            detail="Only mentors can accept sessions"
        )
    
    session = db.query(models.Session).filter(
        models.Session.id == session_id,
        models.Session.mentor_id == current_user.id,
        models.Session.status == "Pending"
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Pending session not found or you're not the mentor"
        )
    
    session.status = "Confirmed"
    
    # Update timestamp if column exists
    if hasattr(session, 'updated_at'):
        session.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Session confirmed",
        "status": "Confirmed"
    }


# ======================
# DECLINE SESSION (Mentor)
# ======================
@router.patch("/{session_id}/decline")
def decline_session(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mentor declines a pending session request
    """
    
    if current_user.role != "mentor":
        raise HTTPException(
            status_code=403,
            detail="Only mentors can decline sessions"
        )
    
    session = db.query(models.Session).filter(
        models.Session.id == session_id,
        models.Session.mentor_id == current_user.id,
        models.Session.status == "Pending"
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Pending session not found or you're not the mentor"
        )
    
    session.status = "Cancelled"
    
    if hasattr(session, 'updated_at'):
        session.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Session declined",
        "status": "Cancelled"
    }


# ======================
# COMPLETE SESSION (Learner)
# ======================
@router.patch("/{session_id}/complete")
def complete_session(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark session as completed
    Typically learner marks complete, but allow mentor too
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
    
    session.status = "Completed"
    
    if hasattr(session, 'updated_at'):
        session.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Session marked as completed",
        "status": "Completed"
    }


# ======================
# CANCEL SESSION (Both)
# ======================
@router.patch("/{session_id}/cancel")
def cancel_session(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a session (both learner and mentor can cancel)
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
    
    session.status = "Cancelled"
    
    if hasattr(session, 'updated_at'):
        session.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Session cancelled",
        "status": "Cancelled"
    }


# ======================
# RESCHEDULE SESSION (Both)
# ======================
@router.patch("/{session_id}/reschedule")
def reschedule_session(
    session_id: int,
    new_time: str = Form(...),
    reason: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reschedule a session (both parties can request)
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
    
    # Can only reschedule pending or confirmed sessions
    if session.status not in ["Pending", "Confirmed"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot reschedule this session"
        )
    
    # Parse new time
    try:
        new_datetime = datetime.fromisoformat(new_time.replace("Z", "+00:00"))
        
        if new_datetime <= datetime.utcnow():
            raise HTTPException(
                status_code=400,
                detail="New time must be in the future"
            )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date/time format"
        )
    
    session.scheduled_time = new_datetime
    session.status = "Pending"  # Reset to pending for re-approval
    
    # Optionally add reason to notes
    if reason:
        if session.notes:
            session.notes = f"{session.notes}\n\n[Rescheduled: {reason}]"
        else:
            session.notes = f"[Rescheduled: {reason}]"
    
    if hasattr(session, 'updated_at'):
        session.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Session rescheduled successfully",
        "new_time": new_datetime.isoformat(),
        "status": "Pending"
    }


# ======================
# DELETE SESSION (Optional)
# ======================
@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a session (only if pending)
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
            detail="Not authorized to delete this session"
        )
    
    # Only allow deletion of pending sessions
    if session.status != "Pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending sessions can be deleted. Use cancel for others."
        )
    
    db.delete(session)
    db.commit()
    
    return {
        "message": "Session deleted successfully"
    }