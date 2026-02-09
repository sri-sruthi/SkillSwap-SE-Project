# app/crud/session.py
from sqlalchemy.orm import Session
from app import models

def create_session(db: Session, learner_id: int, mentor_id: int, skill_id: int = None, scheduled_time=None, notes: str = None):
    session = models.Session(
        learner_id=learner_id,
        mentor_id=mentor_id,
        skill_id=skill_id,
        scheduled_time=scheduled_time,
        status="Pending",
        notes=notes
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def get_session(db: Session, session_id: int):
    return db.query(models.Session).filter(models.Session.id == session_id).first()

def update_session_status(db: Session, session_id: int, new_status: str):
    session = get_session(db, session_id)
    if session:
        session.status = new_status
        db.commit()
        db.refresh(session)
    return session

def delete_session(db: Session, session_id: int):
    session = get_session(db, session_id)
    if session:
        db.delete(session)
        db.commit()
        return True
    return False