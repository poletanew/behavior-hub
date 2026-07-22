import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.family_access import FamilyAccess
from app.models.patient import Patient
from app.models.user import User
from app.schemas.family import FamilyAccessUpdateRequest
from app.services import audit_service, patient_service

WHITELIST_FIELDS = (
    "can_view_evolution_charts",
    "can_view_upcoming_appointments",
    "can_view_team_guidance",
    "can_view_home_materials",
    "can_use_messaging",
    "can_submit_routine_logs",
)


def _to_response(db: Session, access: FamilyAccess) -> dict:
    patient = db.get(Patient, access.patient_id)
    family_user = db.get(User, access.family_user_id)
    return {
        "id": access.id,
        "patient_id": access.patient_id,
        "patient_name": patient.name if patient else "?",
        "family_user_id": access.family_user_id,
        "family_user_name": family_user.name if family_user else "?",
        "family_user_email": family_user.email if family_user else "?",
        "granted_by_user_id": access.granted_by_user_id,
        "consent_given_at": access.consent_given_at,
        "can_view_evolution_charts": access.can_view_evolution_charts,
        "can_view_upcoming_appointments": access.can_view_upcoming_appointments,
        "can_view_team_guidance": access.can_view_team_guidance,
        "can_view_home_materials": access.can_view_home_materials,
        "can_use_messaging": access.can_use_messaging,
        "can_submit_routine_logs": access.can_submit_routine_logs,
        "revoked_at": access.revoked_at,
        "created_at": access.created_at,
    }


def _get_access_or_404(db: Session, admin: User, access_id: uuid.UUID) -> FamilyAccess:
    access = db.get(FamilyAccess, access_id)
    if access is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family access not found")
    # Reusa o gate de tenant/atribuição do paciente: só quem enxerga o
    # paciente pode administrar o acesso do responsável a ele.
    patient_service.get_patient_or_404(db, admin, access.patient_id)
    return access


def list_for_patient(db: Session, admin: User, patient_id: uuid.UUID) -> list[dict]:
    patient_service.get_patient_or_404(db, admin, patient_id)
    accesses = (
        db.query(FamilyAccess)
        .filter(FamilyAccess.patient_id == patient_id)
        .order_by(FamilyAccess.created_at.desc())
        .all()
    )
    return [_to_response(db, access) for access in accesses]


def update_whitelist(
    db: Session, admin: User, access_id: uuid.UUID, payload: FamilyAccessUpdateRequest
) -> dict:
    """Seção 17.2 — cada categoria só é liberada por uma ação explícita do
    administrador; nenhum campo novo nasce liberado por omissão."""
    access = _get_access_or_404(db, admin, access_id)
    if access.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This family access was revoked")

    before = {field: getattr(access, field) for field in WHITELIST_FIELDS}
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(access, field, value)

    audit_service.record(
        db,
        actor_user_id=admin.id,
        action="family_access_whitelist_updated",
        entity_type="family_access",
        entity_id=access.id,
        before=before,
        after=updates,
    )
    db.commit()
    db.refresh(access)
    return _to_response(db, access)


def revoke_access(db: Session, admin: User, access_id: uuid.UUID) -> dict:
    """Seção 17.2 — revogação imediata e auditada, com encerramento de sessões
    ativas: bumpar token_version invalida instantaneamente qualquer access
    token já emitido para esse responsável, mesmo antes de expirar."""
    access = _get_access_or_404(db, admin, access_id)
    if access.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This family access was already revoked")

    now = datetime.datetime.now(datetime.timezone.utc)
    access.revoked_at = now
    access.revoked_by_user_id = admin.id

    family_user = db.get(User, access.family_user_id)
    if family_user is not None:
        family_user.token_version += 1

    audit_service.record(
        db,
        actor_user_id=admin.id,
        action="family_access_revoked",
        entity_type="family_access",
        entity_id=access.id,
        after={"revoked_at": now.isoformat()},
    )
    db.commit()
    db.refresh(access)
    return _to_response(db, access)
