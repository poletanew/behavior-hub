import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.clinic_permission_settings import ClinicPermissionSettings
from app.models.enums import UserType
from app.models.user import User
from app.schemas.rbac import ClinicPermissionSettingsUpdateRequest
from app.services import audit_service

# Seção 17.1 — tabela de RBAC do PRD, incluindo as ações marcadas como "Configurável".


def get_or_create_settings(db: Session, clinic_id: uuid.UUID) -> ClinicPermissionSettings:
    settings = db.query(ClinicPermissionSettings).filter(ClinicPermissionSettings.clinic_id == clinic_id).first()
    if settings is None:
        settings = ClinicPermissionSettings(clinic_id=clinic_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def get_settings_for_user(db: Session, user: User) -> ClinicPermissionSettings | None:
    """Contas individuais não têm configurações de clínica (não se aplicam)."""
    if user.clinic_id is None:
        return None
    return get_or_create_settings(db, user.clinic_id)


def update_settings(
    db: Session, admin: User, payload: ClinicPermissionSettingsUpdateRequest
) -> ClinicPermissionSettings:
    if admin.user_type != UserType.CLINIC_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only clinic admins can change permission settings")

    settings = get_or_create_settings(db, admin.clinic_id)
    before = {
        k: getattr(settings, k)
        for k in (
            "professionals_can_create_patients",
            "supervisors_can_register_sessions",
            "supervisors_can_edit_any_objective_area",
            "admins_can_edit_any_objective_area",
            "supervisors_can_restore_deleted_data",
            "supervisors_can_generate_invitations",
        )
    }
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)

    audit_service.record(
        db,
        actor_user_id=admin.id,
        action="clinic_permission_settings_updated",
        entity_type="clinic_permission_settings",
        entity_id=settings.id,
        before=before,
        after=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(settings)
    return settings


def can_create_patient(db: Session, user: User) -> bool:
    """Seção 17.1 — "Cadastrar paciente": Admin clínica Sim, Individual Sim,
    Profissional Configurável, Supervisor Configurável (tratado como profissional)."""
    if user.user_type in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL):
        return True
    settings = get_settings_for_user(db, user)
    return bool(settings and settings.professionals_can_create_patients)


def can_register_session(db: Session, user: User) -> bool:
    """Seção 17.1 — "Registrar sessão": Admin/Profissional/Individual Sim,
    Supervisor Configurável."""
    if user.user_type != UserType.SUPERVISOR:
        return True
    settings = get_settings_for_user(db, user)
    return bool(settings and settings.supervisors_can_register_sessions)


def can_edit_any_objective_area(db: Session, user: User) -> bool:
    """Seção 17.1 — "Editar objetivo de outra área": Admin clínica/Supervisor Configurável."""
    settings = get_settings_for_user(db, user)
    if settings is None:
        return False
    if user.user_type == UserType.CLINIC_ADMIN:
        return settings.admins_can_edit_any_objective_area
    if user.user_type == UserType.SUPERVISOR:
        return settings.supervisors_can_edit_any_objective_area
    return False


def can_restore_deleted_data(db: Session, user: User) -> bool:
    """Seção 17.1 — "Restaurar Deleted Data": Admin/Individual Sim, Supervisor Configurável."""
    if user.user_type in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL):
        return True
    if user.user_type == UserType.SUPERVISOR:
        settings = get_settings_for_user(db, user)
        return bool(settings and settings.supervisors_can_restore_deleted_data)
    return False


def can_generate_invitation(db: Session, user: User) -> bool:
    """Seção 17.1 — "Gerar convite": Admin clínica Sim, Supervisor Configurável."""
    if user.user_type == UserType.CLINIC_ADMIN:
        return True
    if user.user_type == UserType.SUPERVISOR:
        settings = get_settings_for_user(db, user)
        return bool(settings and settings.supervisors_can_generate_invitations)
    return False
