import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from app.models.enums import UserType
from app.models.patient import Patient, PatientAssignment
from app.models.session import ClinicalSession, SessionTraining, Trial
from app.models.training import Training
from app.models.user import User
from app.schemas.aba import ABATrialReviewEntry, ATSummaryResponse

# Addendum v2.1, RF-11 — espaço de trabalho do supervisor: atribuir ATs a
# pacientes (reaproveita PATCH/POST de assignments já existente, Seção 7.3),
# acompanhar treinos aplicados e revisar tentativas registradas pelos ATs.


def _require_supervisor_or_admin(user: User) -> None:
    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.SUPERVISOR) or user.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only supervisors or clinic admins can access the ABA workspace")


def list_ats(db: DbSession, user: User) -> list[ATSummaryResponse]:
    _require_supervisor_or_admin(user)
    ats = (
        db.query(User)
        .filter(User.clinic_id == user.clinic_id, User.user_type == UserType.AT)
        .order_by(User.name)
        .all()
    )
    counts = dict(
        db.query(PatientAssignment.professional_id, func.count(PatientAssignment.id))
        .filter(PatientAssignment.professional_id.in_([at.id for at in ats]))
        .group_by(PatientAssignment.professional_id)
        .all()
    )
    return [
        ATSummaryResponse(
            id=at.id,
            name=at.name,
            email=at.email,
            supervisor_id=at.supervisor_id,
            assigned_patient_count=counts.get(at.id, 0),
        )
        for at in ats
    ]


def _get_at_or_404(db: DbSession, user: User, at_id: uuid.UUID) -> User:
    at = db.get(User, at_id)
    if at is None or at.clinic_id != user.clinic_id or at.user_type != UserType.AT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AT not found in this clinic")
    return at


def list_patients_for_at(db: DbSession, user: User, at_id: uuid.UUID) -> list[Patient]:
    _require_supervisor_or_admin(user)
    at = _get_at_or_404(db, user, at_id)
    patient_ids = db.query(PatientAssignment.patient_id).filter(PatientAssignment.professional_id == at.id)
    return (
        db.query(Patient)
        .filter(Patient.id.in_(patient_ids), Patient.deleted_at.is_(None))
        .order_by(Patient.name)
        .all()
    )


def list_recent_trials(db: DbSession, user: User, *, limit: int = 50) -> list[ABATrialReviewEntry]:
    """"Acompanhar quais treinos foram aplicados por qual AT e quando, e
    revisar as tentativas registradas" (RF-11) — visão somente leitura; a
    camada de aprovação em si é opcional ("se a clínica optar") e não é
    implementada nesta fase."""
    _require_supervisor_or_admin(user)

    rows = (
        db.query(Trial, SessionTraining, ClinicalSession, Training, User, Patient)
        .join(SessionTraining, Trial.session_training_id == SessionTraining.id)
        .join(ClinicalSession, SessionTraining.session_id == ClinicalSession.id)
        .join(Training, SessionTraining.training_id == Training.id)
        .join(User, ClinicalSession.professional_id == User.id)
        .join(Patient, ClinicalSession.patient_id == Patient.id)
        .filter(ClinicalSession.clinic_id == user.clinic_id, User.user_type == UserType.AT)
        .filter(Trial.deleted_at.is_(None))
        .order_by(Trial.recorded_at.desc())
        .limit(limit)
        .all()
    )
    return [
        ABATrialReviewEntry(
            trial_id=trial.id,
            at_user_id=at_user.id,
            at_name=at_user.name,
            patient_id=patient.id,
            patient_name=patient.name,
            training_id=training.id,
            training_title=training.title,
            result=trial.result,
            prompt_level=trial.prompt_level,
            recorded_at=trial.recorded_at,
        )
        for trial, _session_training, _session, training, at_user, patient in rows
    ]
