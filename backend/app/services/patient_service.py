import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import AssignmentPermission, PatientStatus, UserType
from app.models.patient import Patient, PatientAssignment
from app.models.user import User
from app.schemas.patient import PatientAssignmentCreateRequest, PatientCreateRequest, PatientUpdateRequest
from app.services import audit_service
from app.services.plan_service import current_plan

settings = get_settings()


def _tenant_scope_filter(user: User):
    """Seção 17 — isolamento de tenant: nunca misturar dados de clinicas/individuos diferentes."""
    if user.clinic_id is not None:
        return Patient.clinic_id == user.clinic_id
    return Patient.individual_owner_id == user.id


def _accessible_patient_ids_stmt(user: User):
    """Restricts a clinic professional to patients explicitly assigned to them.
    Clinic admins and individual tenants see the full tenant scope (Seção 17.1)."""
    if user.user_type == UserType.CLINIC_ADMIN or user.clinic_id is None:
        return None  # no extra restriction beyond tenant scope
    return select(PatientAssignment.patient_id).where(PatientAssignment.professional_id == user.id)


def list_patients(db: Session, user: User, *, include_deleted: bool = False) -> list[Patient]:
    query = db.query(Patient).filter(_tenant_scope_filter(user))
    if not include_deleted:
        query = query.filter(Patient.deleted_at.is_(None))

    assigned_stmt = _accessible_patient_ids_stmt(user)
    if assigned_stmt is not None:
        query = query.filter(Patient.id.in_(assigned_stmt))

    return query.order_by(Patient.name).all()


def get_patient_or_404(db: Session, user: User, patient_id: uuid.UUID, *, include_deleted: bool = False) -> Patient:
    """Seção 17 / AC-14 — usuario de outra clinica nunca acessa paciente por URL direta."""
    query = db.query(Patient).filter(Patient.id == patient_id, _tenant_scope_filter(user))
    if not include_deleted:
        query = query.filter(Patient.deleted_at.is_(None))

    assigned_stmt = _accessible_patient_ids_stmt(user)
    if assigned_stmt is not None:
        query = query.filter(Patient.id.in_(assigned_stmt))

    patient = query.first()
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    return patient


def count_active_patients(db: Session, user: User) -> int:
    return (
        db.query(Patient)
        .filter(_tenant_scope_filter(user), Patient.deleted_at.is_(None))
        .count()
    )


def create_patient(db: Session, user: User, payload: PatientCreateRequest) -> Patient:
    """AC-02 — plano Free bloqueia o quarto paciente ativo no backend."""
    if current_plan(user) == "free":
        active_count = count_active_patients(db, user)
        if active_count >= settings.FREE_PLAN_PATIENT_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Free plan limit of 3 active patients reached. Upgrade your plan to add more.",
            )

    patient = Patient(
        name=payload.name,
        birth_date=payload.birth_date,
        guardian_name=payload.guardian_name,
        diagnosis=payload.diagnosis,
        notes=payload.notes,
        status=PatientStatus.ACTIVE,
        created_by_user_id=user.id,
    )
    if user.clinic_id is not None:
        patient.clinic_id = user.clinic_id
    else:
        patient.individual_owner_id = user.id

    db.add(patient)
    db.flush()
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="patient_created",
        entity_type="patient",
        entity_id=patient.id,
        after={"name": patient.name},
    )
    db.commit()
    db.refresh(patient)
    return patient


def update_patient(db: Session, user: User, patient_id: uuid.UUID, payload: PatientUpdateRequest) -> Patient:
    patient = get_patient_or_404(db, user, patient_id)
    before = {"name": patient.name, "status": patient.status.value}

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="patient_updated",
        entity_type="patient",
        entity_id=patient.id,
        before=before,
        after={"name": patient.name, "status": patient.status.value},
    )
    db.commit()
    db.refresh(patient)
    return patient


def soft_delete_patient(db: Session, user: User, patient_id: uuid.UUID, reason: str | None = None) -> Patient:
    """Seção 10.3 / 16.1 — exclusao e sempre soft delete, nunca fisica imediata."""
    patient = get_patient_or_404(db, user, patient_id)

    now = datetime.datetime.now(datetime.timezone.utc)
    patient.deleted_at = now
    patient.deleted_by = user.id
    patient.deletion_reason = reason

    # Cascade soft delete to sessions/trials so they leave active listings too
    # (Seção 16.3 — sessões, relatórios, planos e listas não podem exibir registros deletados).
    from app.models.session import ClinicalSession, SessionTraining, Trial

    session_ids = [
        row[0]
        for row in db.query(ClinicalSession.id)
        .filter(ClinicalSession.patient_id == patient.id, ClinicalSession.deleted_at.is_(None))
        .all()
    ]
    if session_ids:
        db.query(ClinicalSession).filter(ClinicalSession.id.in_(session_ids)).update(
            {"deleted_at": now, "deleted_by": user.id}, synchronize_session=False
        )
        trial_ids_subquery = (
            db.query(Trial.id)
            .join(SessionTraining, Trial.session_training_id == SessionTraining.id)
            .filter(SessionTraining.session_id.in_(session_ids))
            .subquery()
        )
        db.query(Trial).filter(Trial.id.in_(trial_ids_subquery.select())).update(
            {"deleted_at": now, "deleted_by": user.id}, synchronize_session=False
        )

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="patient_deleted",
        entity_type="patient",
        entity_id=patient.id,
        after={"deleted_at": now.isoformat(), "reason": reason},
    )
    db.commit()
    db.refresh(patient)
    return patient


def restore_patient(db: Session, user: User, patient_id: uuid.UUID) -> Patient:
    """Seção 16.2 — restaurar paciente e todos os dados relacionados em uma operacao transacional."""
    patient = get_patient_or_404(db, user, patient_id, include_deleted=True)
    if patient.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Patient is not deleted")

    retention_deadline = patient.deleted_at + datetime.timedelta(days=settings.DELETED_DATA_RETENTION_DAYS)
    if datetime.datetime.now(datetime.timezone.utc) > retention_deadline:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Retention period has expired")

    patient.deleted_at = None
    patient.deleted_by = None
    patient.deletion_reason = None

    from app.models.session import ClinicalSession, SessionTraining, Trial

    session_ids = [
        row[0]
        for row in db.query(ClinicalSession.id)
        .filter(ClinicalSession.patient_id == patient.id, ClinicalSession.deleted_at.isnot(None))
        .all()
    ]
    if session_ids:
        db.query(ClinicalSession).filter(ClinicalSession.id.in_(session_ids)).update(
            {"deleted_at": None, "deleted_by": None}, synchronize_session=False
        )
        trial_ids_subquery = (
            db.query(Trial.id)
            .join(SessionTraining, Trial.session_training_id == SessionTraining.id)
            .filter(SessionTraining.session_id.in_(session_ids))
            .subquery()
        )
        db.query(Trial).filter(Trial.id.in_(trial_ids_subquery.select())).update(
            {"deleted_at": None, "deleted_by": None}, synchronize_session=False
        )

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="patient_restored",
        entity_type="patient",
        entity_id=patient.id,
    )
    db.commit()
    db.refresh(patient)
    return patient


def list_deleted_patients(db: Session, user: User) -> list[Patient]:
    """Seção 16.2 — apenas administradores acessam esta lista (aplicado no router)."""
    return (
        db.query(Patient)
        .filter(_tenant_scope_filter(user), Patient.deleted_at.isnot(None))
        .order_by(Patient.deleted_at.desc())
        .all()
    )


def assign_professional(
    db: Session, user: User, patient_id: uuid.UUID, payload: PatientAssignmentCreateRequest
) -> PatientAssignment:
    patient = get_patient_or_404(db, user, patient_id)

    professional = db.get(User, payload.professional_id)
    if professional is None or professional.clinic_id != patient.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professional not found in this clinic")

    existing = (
        db.query(PatientAssignment)
        .filter(
            PatientAssignment.patient_id == patient.id,
            PatientAssignment.professional_id == professional.id,
        )
        .first()
    )
    if existing is not None:
        existing.permission = payload.permission
        assignment = existing
    else:
        assignment = PatientAssignment(
            patient_id=patient.id,
            professional_id=professional.id,
            permission=payload.permission,
        )
        db.add(assignment)

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="patient_assignment_upserted",
        entity_type="patient_assignment",
        entity_id=patient.id,
        after={"professional_id": str(professional.id), "permission": payload.permission.value},
    )
    db.commit()
    db.refresh(assignment)
    return assignment


def remove_assignment(db: Session, user: User, patient_id: uuid.UUID, professional_id: uuid.UUID) -> None:
    patient = get_patient_or_404(db, user, patient_id)
    assignment = (
        db.query(PatientAssignment)
        .filter(
            PatientAssignment.patient_id == patient.id,
            PatientAssignment.professional_id == professional_id,
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    db.delete(assignment)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="patient_assignment_removed",
        entity_type="patient_assignment",
        entity_id=patient.id,
        before={"professional_id": str(professional_id)},
    )
    db.commit()
