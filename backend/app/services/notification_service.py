import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User


def create_notification(
    db: Session,
    *,
    recipient_user_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    notification_type: str,
    message: str,
    entity_type: str,
    entity_id: uuid.UUID,
) -> Notification:
    notification = Notification(
        recipient_user_id=recipient_user_id,
        actor_user_id=actor_user_id,
        type=notification_type,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(notification)
    return notification


def list_notifications(db: Session, user: User, *, unread_only: bool = False) -> list[Notification]:
    query = db.query(Notification).filter(Notification.recipient_user_id == user.id)
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))
    return query.order_by(Notification.created_at.desc()).all()


def mark_read(db: Session, user: User, notification_id: uuid.UUID) -> Notification:
    notification = db.get(Notification, notification_id)
    if notification is None or notification.recipient_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.read_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user: User) -> int:
    now = datetime.datetime.now(datetime.timezone.utc)
    updated = (
        db.query(Notification)
        .filter(Notification.recipient_user_id == user.id, Notification.read_at.is_(None))
        .update({"read_at": now}, synchronize_session=False)
    )
    db.commit()
    return updated
