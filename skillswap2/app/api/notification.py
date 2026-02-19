from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.services import notification_service
from app.utils.security import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/my")
def get_my_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notifications = notification_service.list_user_notifications(
        db,
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
    )

    return [
        {
            "id": n.id,
            "recipient_id": n.recipient_id,
            "actor_id": n.actor_id,
            "session_id": n.session_id,
            "event_type": n.event_type,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None
        }
        for n in notifications
    ]


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notification = notification_service.mark_notification_read(
        db,
        user_id=current_user.id,
        notification_id=notification_id,
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"message": "Notification marked as read", "id": notification.id}


@router.patch("/read-all")
def mark_all_notifications_read(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = notification_service.mark_all_notifications_read(
        db,
        user_id=current_user.id,
    )
    return {"message": "All notifications marked as read", "updated": count}


@router.get("/unread-count")
def get_unread_count(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = notification_service.get_unread_count(db, user_id=current_user.id)
    return {"unread_count": count}
