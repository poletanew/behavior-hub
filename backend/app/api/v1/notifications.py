import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationResponse
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    unread_only: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Seção 32.6 — painel único consolidando comentários novos e menções (@)."""
    return notification_service.list_notifications(db, user, unread_only=unread_only)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(notification_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return notification_service.mark_read(db, user, notification_id)


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    count = notification_service.mark_all_read(db, user)
    return {"marked_read": count}
