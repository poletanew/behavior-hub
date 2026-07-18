import datetime
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.audit_log import AuditLogResponse
from app.services import audit_log_service

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    entity_type: str | None = None,
    action: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    date_from: datetime.datetime | None = None,
    date_to: datetime.datetime | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 17/21 — auditoria completa (somente administradores), escopada por tenant."""
    return audit_log_service.list_audit_logs(
        db,
        user,
        entity_type=entity_type,
        action=action,
        actor_user_id=actor_user_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
