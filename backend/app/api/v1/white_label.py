from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.white_label import WhiteLabelResponse, WhiteLabelUpdateRequest
from app.services import white_label_service

router = APIRouter(prefix="/clinic/white-label", tags=["white-label"])


@router.get("", response_model=WhiteLabelResponse)
def get_white_label_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 32.9 — configuração de white-label (Enterprise): logo, cor e nome
    exibido em relatórios exportados e no Family Portal."""
    return white_label_service.get_settings(db, user)


@router.patch("", response_model=WhiteLabelResponse)
def update_white_label_settings(
    payload: WhiteLabelUpdateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return white_label_service.update_settings(db, user, payload)
