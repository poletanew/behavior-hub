import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.clinic import Clinic
from app.models.enums import SubscriptionPlan, UserType
from app.models.user import User
from app.schemas.white_label import WhiteLabelUpdateRequest
from app.services import audit_service

DEFAULT_BRANDING = {"enabled": False, "logo_url": None, "brand_color": None, "display_name": None}


def _is_enterprise_and_active(clinic: Clinic) -> bool:
    """Seção 8.3 — "nunca confiar apenas no rótulo do plano": se a clínica
    fizer downgrade ou a assinatura ficar em atraso/cancelada, o white-label
    para de valer imediatamente, mesmo que os campos continuem salvos no
    banco (evita reconfigurar tudo de novo caso a clínica volte ao Enterprise)."""
    return clinic.subscription_plan == SubscriptionPlan.ENTERPRISE and clinic.has_paid_access


def _require_admin_clinic(db: Session, admin: User) -> Clinic:
    if admin.user_type != UserType.CLINIC_ADMIN or admin.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only clinic admins can manage white-label settings")
    clinic = db.get(Clinic, admin.clinic_id)
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    return clinic


def get_settings(db: Session, admin: User) -> dict:
    clinic = _require_admin_clinic(db, admin)
    return {
        "enabled": _is_enterprise_and_active(clinic),
        "logo_url": clinic.white_label_logo_url,
        "brand_color": clinic.white_label_brand_color,
        "display_name": clinic.white_label_display_name,
    }


def update_settings(db: Session, admin: User, payload: WhiteLabelUpdateRequest) -> dict:
    clinic = _require_admin_clinic(db, admin)
    if not _is_enterprise_and_active(clinic):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="White-label is available only on an active Enterprise plan",
        )

    before = {
        "logo_url": clinic.white_label_logo_url,
        "brand_color": clinic.white_label_brand_color,
        "display_name": clinic.white_label_display_name,
    }
    updates = payload.model_dump(exclude_unset=True)
    if "logo_url" in updates:
        clinic.white_label_logo_url = updates["logo_url"]
    if "brand_color" in updates:
        clinic.white_label_brand_color = updates["brand_color"]
    if "display_name" in updates:
        clinic.white_label_display_name = updates["display_name"]

    audit_service.record(
        db,
        actor_user_id=admin.id,
        action="white_label_settings_updated",
        entity_type="clinic",
        entity_id=clinic.id,
        before=before,
        after=updates,
    )
    db.commit()
    db.refresh(clinic)
    return get_settings(db, admin)


def get_branding_for_clinic(db: Session, clinic_id: uuid.UUID | None) -> dict:
    """Usado por superfícies que não são administrativas (exportação de
    Reports, Family Portal): nunca exige permissão de admin, só devolve os
    três campos de marca (ou o padrão desligado) para o clinic_id informado."""
    if clinic_id is None:
        return dict(DEFAULT_BRANDING)
    clinic = db.get(Clinic, clinic_id)
    if clinic is None or not _is_enterprise_and_active(clinic):
        return dict(DEFAULT_BRANDING)
    return {
        "enabled": True,
        "logo_url": clinic.white_label_logo_url,
        "brand_color": clinic.white_label_brand_color,
        "display_name": clinic.white_label_display_name,
    }
