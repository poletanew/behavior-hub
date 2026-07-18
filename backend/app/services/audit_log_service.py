import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, aliased

from app.models.audit_log import AuditLog
from app.models.enums import UserType
from app.models.user import User

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def list_audit_logs(
    db: Session,
    user: User,
    *,
    entity_type: str | None = None,
    action: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    date_from: datetime.datetime | None = None,
    date_to: datetime.datetime | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> list[dict]:
    """Seção 17/21 — auditoria completa, restrita a administradores e escopada
    por tenant (via o tenant do usuário que praticou a ação).

    Limitação conhecida: ações de sistema sem ator (ex.: purga automática da
    Seção 16.2, actor_user_id nulo) não aparecem nesta consulta escopada por
    tenant — ficam registradas no banco, mas não têm um usuário para derivar o
    tenant. Isso é aceitável para o núcleo da Fase 3; um painel de auditoria
    "de sistema" fica fora deste escopo.
    """
    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view audit logs")

    actor = aliased(User)
    query = db.query(AuditLog, actor.name).join(actor, AuditLog.actor_user_id == actor.id)

    if user.clinic_id is not None:
        query = query.filter(actor.clinic_id == user.clinic_id)
    else:
        query = query.filter(actor.id == user.id)

    if entity_type is not None:
        query = query.filter(AuditLog.entity_type == entity_type)
    if action is not None:
        query = query.filter(AuditLog.action == action)
    if actor_user_id is not None:
        query = query.filter(AuditLog.actor_user_id == actor_user_id)
    if date_from is not None:
        query = query.filter(AuditLog.timestamp >= date_from)
    if date_to is not None:
        query = query.filter(AuditLog.timestamp <= date_to)

    limit = min(limit, MAX_LIMIT)
    rows = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return [
        {
            "id": entry.id,
            "actor_user_id": entry.actor_user_id,
            "actor_name": actor_name,
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "before": entry.before,
            "after": entry.after,
            "timestamp": entry.timestamp,
        }
        for entry, actor_name in rows
    ]
