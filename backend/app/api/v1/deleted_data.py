import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.deleted_data import DeletedItemResponse, EntityType
from app.services import deleted_data_service

router = APIRouter(prefix="/deleted-data", tags=["deleted-data"])


@router.get("", response_model=list[DeletedItemResponse])
def list_deleted_data(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 16.2 — lista unificada com tipo, nome, data de exclusão, responsável e dias restantes."""
    return deleted_data_service.list_deleted_items(db, user)


@router.post("/{entity_type}/{item_id}/restore")
def restore_deleted_item(
    entity_type: EntityType,
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 16.2 — restaurar item em uma operação transacional (AC-11)."""
    deleted_data_service.restore_item(db, user, entity_type, item_id)
    return {"restored": True}
