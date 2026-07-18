from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import UserType
from app.models.user import User
from app.schemas.rbac import ClinicPermissionSettingsResponse, ClinicPermissionSettingsUpdateRequest
from app.services import rbac_service

router = APIRouter(prefix="/clinic/permission-settings", tags=["rbac"])


@router.get("", response_model=ClinicPermissionSettingsResponse)
def get_permission_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 17.1 — permissões configuráveis da clínica (somente admin/supervisor)."""
    if user.clinic_id is None or user.user_type not in (UserType.CLINIC_ADMIN, UserType.SUPERVISOR):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return rbac_service.get_or_create_settings(db, user.clinic_id)


@router.patch("", response_model=ClinicPermissionSettingsResponse)
def update_permission_settings(
    payload: ClinicPermissionSettingsUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return rbac_service.update_settings(db, user, payload)
