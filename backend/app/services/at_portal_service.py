import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.models.enums import UserType
from app.models.patient import Patient, PatientAssignment
from app.models.session import ClinicalSession
from app.models.training_patient_link import TrainingPatientLink
from app.models.user import User
from app.schemas.at_portal import ATApplyTrainingRequest
from app.schemas.session import SessionCreateRequest
from app.services import session_service, training_service

# Addendum v2.1, RF-11 — espaço de trabalho restrito do AT (Auxiliar
# Terapêutico): só pacientes atribuídos, só treinos vinculados a eles (RF-10),
# sem diagnóstico/plano/relatórios. Segue o mesmo padrão de "portal dedicado"
# já usado para o Family Portal, em vez de remendar os endpoints gerais.


def _require_at(user: User) -> None:
    if user.user_type != UserType.AT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only AT accounts use this portal")


def list_assigned_patients(db: DbSession, user: User) -> list[Patient]:
    _require_at(user)
    patient_ids = db.query(PatientAssignment.patient_id).filter(PatientAssignment.professional_id == user.id)
    return (
        db.query(Patient)
        .filter(Patient.id.in_(patient_ids), Patient.deleted_at.is_(None))
        .order_by(Patient.name)
        .all()
    )


def _get_assigned_patient_or_404(db: DbSession, user: User, patient_id: uuid.UUID) -> Patient:
    patient = (
        db.query(Patient)
        .join(PatientAssignment, PatientAssignment.patient_id == Patient.id)
        .filter(
            Patient.id == patient_id,
            Patient.deleted_at.is_(None),
            PatientAssignment.professional_id == user.id,
        )
        .first()
    )
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found or not assigned to you")
    return patient


def list_prescribed_trainings(db: DbSession, user: User, patient_id: uuid.UUID):
    _require_at(user)
    patient = _get_assigned_patient_or_404(db, user, patient_id)
    return training_service.list_links_for_patient(db, user, patient.id)


def apply_training(
    db: DbSession, user: User, patient_id: uuid.UUID, payload: ATApplyTrainingRequest
) -> ClinicalSession:
    """RF-11 — "AT aplica treino vinculado (RF-10) → Registra tentativas".
    Só permite aplicar um treino que já foi prescrito para esse paciente
    especificamente (não qualquer treino do sistema)."""
    _require_at(user)
    patient = _get_assigned_patient_or_404(db, user, patient_id)

    link = (
        db.query(TrainingPatientLink)
        .filter(
            TrainingPatientLink.patient_id == patient.id,
            TrainingPatientLink.training_id == payload.training_id,
        )
        .first()
    )
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This training is not linked to this patient (see RF-10 Vincular)",
        )

    session_payload = SessionCreateRequest(
        patient_id=patient.id,
        professional_id=user.id,
        occurred_at=payload.occurred_at,
        notes=payload.notes,
        training_ids=[payload.training_id],
    )
    return session_service.create_session(db, user, session_payload)
