from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Skip suite when FastAPI dependency is not present in local environment.
pytest.importorskip("fastapi")

from fastapi import HTTPException
from app.database import Base
from app.models.user import User
from app.services import notification_service
from app.api.notification import (
    get_my_notifications,
    get_unread_count,
    mark_all_notifications_read,
    mark_notification_read,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _create_user(db, email: str = "user@test.edu", name: str = "User") -> User:
    user = User(
        name=name,
        email=email,
        password_hash="hash",
        role="student",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_notification_api_read_flow(db_session):
    user = _create_user(db_session)

    first = notification_service.create_notification(
        db_session,
        recipient_id=user.id,
        actor_id=None,
        session_id=None,
        event_type="session_requested",
        message="New session request",
    )
    second = notification_service.create_notification(
        db_session,
        recipient_id=user.id,
        actor_id=None,
        session_id=None,
        event_type="session_confirmed",
        message="Session confirmed",
    )
    second.is_read = True
    db_session.commit()

    unread = get_my_notifications(
        unread_only=True,
        limit=50,
        current_user=user,
        db=db_session,
    )
    assert len(unread) == 1
    assert unread[0]["id"] == first.id

    count_before = get_unread_count(current_user=user, db=db_session)
    assert count_before["unread_count"] == 1

    marked = mark_notification_read(
        notification_id=first.id,
        current_user=user,
        db=db_session,
    )
    assert marked["id"] == first.id

    count_after = get_unread_count(current_user=user, db=db_session)
    assert count_after["unread_count"] == 0

    third = notification_service.create_notification(
        db_session,
        recipient_id=user.id,
        actor_id=None,
        session_id=None,
        event_type="session_cancelled",
        message="Session cancelled",
    )
    assert third.id is not None
    db_session.commit()

    all_marked = mark_all_notifications_read(current_user=user, db=db_session)
    assert all_marked["updated"] >= 1

    final_count = get_unread_count(current_user=user, db=db_session)
    assert final_count["unread_count"] == 0


def test_mark_notification_read_404(db_session):
    user = _create_user(db_session)
    with pytest.raises(HTTPException) as exc_info:
        mark_notification_read(notification_id=99999, current_user=user, db=db_session)
    assert exc_info.value.status_code == 404


def test_dispatch_email_for_notification_success(db_session, monkeypatch):
    user = _create_user(db_session, email="mailok@test.edu", name="Mail OK")
    notification = notification_service.create_notification(
        db_session,
        recipient_id=user.id,
        actor_id=None,
        session_id=None,
        event_type="session_completed",
        message="Completed",
    )
    db_session.commit()

    sent_payload = {}

    def fake_send_email(**kwargs):
        sent_payload.update(kwargs)
        return True

    monkeypatch.setattr(notification_service, "is_email_enabled", lambda: True)
    monkeypatch.setattr(notification_service, "send_email", fake_send_email)

    sent = notification_service.dispatch_email_for_notification(db_session, notification)
    assert sent is True
    assert sent_payload["to_email"] == "mailok@test.edu"
    assert "Completed" in sent_payload["body_text"]


def test_dispatch_email_for_notification_failure_is_safe(db_session, monkeypatch):
    user = _create_user(db_session, email="mailfail@test.edu", name="Mail Fail")
    notification = notification_service.create_notification(
        db_session,
        recipient_id=user.id,
        actor_id=None,
        session_id=None,
        event_type="session_declined",
        message="Declined",
    )
    db_session.commit()

    monkeypatch.setattr(notification_service, "is_email_enabled", lambda: True)
    monkeypatch.setattr(notification_service, "send_email", lambda **kwargs: False)

    sent = notification_service.dispatch_email_for_notification(db_session, notification)
    assert sent is False
