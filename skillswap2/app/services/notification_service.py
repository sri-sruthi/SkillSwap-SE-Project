from __future__ import annotations

import logging
import threading
from typing import List, Optional

from sqlalchemy.orm import Session

from app import models
from app.models.notification import Notification
from app.utils.email import is_email_enabled, send_email

logger = logging.getLogger(__name__)


EMAIL_SUBJECT_BY_EVENT = {
    "session_requested": "New session request on SkillSwap",
    "session_confirmed": "Your session was confirmed on SkillSwap",
    "session_declined": "Session request update on SkillSwap",
    "session_completed": "Session marked completed on SkillSwap",
    "session_cancelled": "Session cancelled on SkillSwap",
    "session_reschedule_requested": "Reschedule request on SkillSwap",
    "session_reschedule_accepted": "Reschedule accepted on SkillSwap",
    "session_reschedule_declined": "Reschedule declined on SkillSwap",
    "review_received": "You received a new review on SkillSwap",
}


def list_user_notifications(
    db: Session,
    *,
    user_id: int,
    unread_only: bool = False,
    limit: int = 50,
) -> List[Notification]:
    query = db.query(Notification).filter(Notification.recipient_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.order_by(Notification.created_at.desc()).limit(limit).all()


def mark_notification_read(
    db: Session,
    *,
    user_id: int,
    notification_id: int,
) -> Optional[Notification]:
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.recipient_id == user_id,
    ).first()
    if not notification:
        return None
    notification.is_read = True
    db.commit()
    return notification


def mark_all_notifications_read(db: Session, *, user_id: int) -> int:
    updated = db.query(Notification).filter(
        Notification.recipient_id == user_id,
        Notification.is_read.is_(False),
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()
    return int(updated)


def get_unread_count(db: Session, *, user_id: int) -> int:
    return db.query(Notification).filter(
        Notification.recipient_id == user_id,
        Notification.is_read.is_(False),
    ).count()


def create_notification(
    db: Session,
    *,
    recipient_id: int,
    actor_id: Optional[int],
    session_id: Optional[int],
    event_type: str,
    message: str,
) -> Notification:
    notification = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        session_id=session_id,
        event_type=event_type,
        message=message,
    )
    db.add(notification)
    db.flush()
    return notification


def _send_notification_email(to_email: str, subject: str, body_text: str, *, notification_id: Optional[int], recipient_id: Optional[int]) -> None:
    """Send SMTP mail in a background thread so API latency stays low."""
    sent = send_email(
        to_email=to_email,
        subject=subject,
        body_text=body_text,
    )
    if not sent:
        logger.info(
            "Notification email not sent (recipient_id=%s, notification_id=%s)",
            recipient_id,
            notification_id,
        )


def dispatch_email_for_notification(db: Session, notification: Notification) -> bool:
    """
    Best-effort email delivery for a committed notification.
    This function never raises and should not impact request success.
    """
    try:
        if not is_email_enabled():
            return False

        recipient = db.query(models.User).filter(
            models.User.id == notification.recipient_id
        ).first()
        if not recipient or not recipient.email:
            return False

        subject = EMAIL_SUBJECT_BY_EVENT.get(
            notification.event_type,
            "New notification from SkillSwap",
        )
        recipient_name = (recipient.name or "there").strip() or "there"
        body_text = (
            f"Hi {recipient_name},\n\n"
            f"{notification.message}\n\n"
            f"Event: {notification.event_type}\n"
            f"Session ID: {notification.session_id or 'N/A'}\n\n"
            "Open SkillSwap to view details."
        )

        worker = threading.Thread(
            target=_send_notification_email,
            args=(
                recipient.email,
                subject,
                body_text,
            ),
            kwargs={
                "notification_id": getattr(notification, "id", None),
                "recipient_id": notification.recipient_id,
            },
            daemon=True,
        )
        worker.start()
        return True
    except Exception as exc:
        logger.warning(
            "Notification email dispatch failed (notification_id=%s): %s",
            getattr(notification, "id", None),
            exc,
        )
        return False
