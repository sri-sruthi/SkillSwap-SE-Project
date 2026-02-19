from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.user import User
from app.services import notification_service


def _build_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _create_user(db, email: str = "notify@test.edu") -> User:
    user = User(
        name="Notify User",
        email=email,
        password_hash="hash",
        role="student",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_notification_service_crud_flow():
    db = _build_db()
    try:
        user = _create_user(db)
        notification_service.create_notification(
            db,
            recipient_id=user.id,
            actor_id=None,
            session_id=None,
            event_type="session_requested",
            message="Requested",
        )
        notification_service.create_notification(
            db,
            recipient_id=user.id,
            actor_id=None,
            session_id=None,
            event_type="session_confirmed",
            message="Confirmed",
        )
        db.commit()

        unread = notification_service.list_user_notifications(
            db,
            user_id=user.id,
            unread_only=True,
            limit=50,
        )
        assert len(unread) == 2
        assert notification_service.get_unread_count(db, user_id=user.id) == 2

        one = notification_service.mark_notification_read(
            db,
            user_id=user.id,
            notification_id=unread[0].id,
        )
        assert one is not None
        assert one.is_read is True
        assert notification_service.get_unread_count(db, user_id=user.id) == 1

        updated = notification_service.mark_all_notifications_read(db, user_id=user.id)
        assert updated >= 1
        assert notification_service.get_unread_count(db, user_id=user.id) == 0
    finally:
        db.close()


def test_dispatch_email_failure_is_non_blocking(monkeypatch):
    db = _build_db()
    try:
        user = _create_user(db, email="safe@test.edu")
        notification = notification_service.create_notification(
            db,
            recipient_id=user.id,
            actor_id=None,
            session_id=None,
            event_type="session_declined",
            message="Declined",
        )
        db.commit()

        monkeypatch.setattr(notification_service, "is_email_enabled", lambda: True)
        monkeypatch.setattr(
            notification_service,
            "send_email",
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError("SMTP down")),
        )

        assert notification_service.dispatch_email_for_notification(db, notification) is False
    finally:
        db.close()
