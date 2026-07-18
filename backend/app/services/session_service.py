import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.models.enums import UserType
from app.models.session import ClinicalSession, SessionTraining, Trial
from app.models.training import Training
from app.models.user import User
from app.schemas.session import SessionCreateRequest, TrialCreateRequest, TrialUpdateRequest
from app.services import appointment_service, audit_service, clinical_alert_service, patient_service, rbac_service
from app.services.calculations import accuracy_pct, independence_pct
from app.services.plan_service import current_plan


def _tenant_scope_filter(user: User):
    if user.clinic_id is not None:
        return ClinicalSession.clinic_id == user.clinic_id
    return ClinicalSession.individual_owner_id == user.id


def create_session(db: DbSession, user: User, payload: SessionCreateRequest) -> ClinicalSession:
    """Seção 11.2 — Novo Atendimento. Garante que o paciente e acessivel ao usuario (AC-14).
    Seção 17.1 — "Registrar sessão" é Configurável para supervisor."""
    if not rbac_service.can_register_session(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to register sessions")

    patient = patient_service.get_patient_or_404(db, user, payload.patient_id)

    if payload.photo_url and current_plan(user) == "free":
        # Seção 8.1/AC-03 — usuario Free nao pode anexar foto a sessao, nem por chamada direta de API.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Photo attachments are not available on the Free plan",
        )

    session = ClinicalSession(
        patient_id=patient.id,
        professional_id=payload.professional_id,
        clinic_id=user.clinic_id,
        individual_owner_id=None if user.clinic_id else user.id,
        occurred_at=payload.occurred_at,
        notes=payload.notes,
        photo_url=payload.photo_url,
    )
    db.add(session)
    db.flush()

    for idx, training_id in enumerate(payload.training_ids, start=1):
        training = db.get(Training, training_id)
        if training is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Training {training_id} not found")
        db.add(SessionTraining(session_id=session.id, training_id=training_id, sequence=idx))

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="session_created",
        entity_type="session",
        entity_id=session.id,
        after={"patient_id": str(patient.id)},
    )
    if payload.appointment_id is not None:
        # Seção 32.2 — "marcar como realizada" abre o Novo Atendimento; salvá-lo
        # vincula e completa o compromisso agendado.
        appointment_service.link_session_to_appointment(db, user, payload.appointment_id, session.id)
    db.commit()
    db.refresh(session)
    return session


def get_session_or_404(db: DbSession, user: User, session_id: uuid.UUID) -> ClinicalSession:
    """AC-07/AC-14 — a sessao so e visivel dentro do tenant e do historico do paciente correto."""
    session = (
        db.query(ClinicalSession)
        .filter(ClinicalSession.id == session_id, _tenant_scope_filter(user), ClinicalSession.deleted_at.is_(None))
        .first()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


def list_sessions(
    db: DbSession, user: User, *, patient_id: uuid.UUID | None = None
) -> list[ClinicalSession]:
    """Seção 9.2 / 11.4 — fonte unica para o widget Sessoes Recentes e para Atendimentos."""
    query = db.query(ClinicalSession).filter(_tenant_scope_filter(user), ClinicalSession.deleted_at.is_(None))
    if patient_id is not None:
        # Validate accessibility of the patient before filtering (AC-07/AC-14).
        patient_service.get_patient_or_404(db, user, patient_id)
        query = query.filter(ClinicalSession.patient_id == patient_id)
    return query.order_by(ClinicalSession.occurred_at.desc()).all()


def add_trainings(db: DbSession, user: User, session_id: uuid.UUID, training_ids: list[uuid.UUID]) -> ClinicalSession:
    session = get_session_or_404(db, user, session_id)
    current_max = (
        db.query(SessionTraining)
        .filter(SessionTraining.session_id == session.id)
        .count()
    )
    for idx, training_id in enumerate(training_ids, start=current_max + 1):
        training = db.get(Training, training_id)
        if training is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Training {training_id} not found")
        db.add(SessionTraining(session_id=session.id, training_id=training_id, sequence=idx))
    db.commit()
    db.refresh(session)
    return session


def _get_session_training_or_404(db: DbSession, user: User, session_training_id: uuid.UUID) -> SessionTraining:
    session_training = db.get(SessionTraining, session_training_id)
    if session_training is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session training not found")
    get_session_or_404(db, user, session_training.session_id)
    return session_training


def _recompute_alerts_after_trial_change(db: DbSession, session_training: SessionTraining) -> None:
    """Seção 19.2/29.1 — TrialCreated/Updated/Deleted recalcula os alertas
    clínicos dos objetivos vinculados a este treino, em tempo real (AC-16)."""
    session = db.get(ClinicalSession, session_training.session_id)
    if session is not None:
        clinical_alert_service.recompute_alerts_for_training(db, session.patient_id, session_training.training_id)


def add_trial(
    db: DbSession, user: User, session_training_id: uuid.UUID, payload: TrialCreateRequest
) -> Trial:
    """Seção 11.3 — cada tentativa e um registro individualizado; o numero sequencial
    nunca e reutilizado, mesmo apos edicao/remocao de tentativas anteriores."""
    session_training = _get_session_training_or_404(db, user, session_training_id)

    max_attempt = (
        db.query(Trial.attempt_number)
        .filter(Trial.session_training_id == session_training.id)
        .order_by(Trial.attempt_number.desc())
        .first()
    )
    next_attempt = (max_attempt[0] + 1) if max_attempt else 1

    trial = Trial(
        session_training_id=session_training.id,
        attempt_number=next_attempt,
        result=payload.result,
        prompt_level=payload.prompt_level,
        notes=payload.notes,
        recorded_at=payload.recorded_at or datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(trial)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="trial_created",
        entity_type="trial",
        entity_id=trial.id,
        after={"attempt_number": next_attempt, "result": payload.result.value},
    )
    db.commit()
    db.refresh(trial)
    _recompute_alerts_after_trial_change(db, session_training)
    return trial


def update_trial(
    db: DbSession, user: User, trial_id: uuid.UUID, payload: TrialUpdateRequest
) -> Trial:
    trial = db.get(Trial, trial_id)
    if trial is None or trial.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found")
    session_training = _get_session_training_or_404(db, user, trial.session_training_id)

    before = {"result": trial.result.value, "prompt_level": trial.prompt_level.value}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(trial, field, value)

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="trial_updated",
        entity_type="trial",
        entity_id=trial.id,
        before=before,
        after={"result": trial.result.value, "prompt_level": trial.prompt_level.value},
    )
    db.commit()
    db.refresh(trial)
    _recompute_alerts_after_trial_change(db, session_training)
    return trial


def delete_trial(db: DbSession, user: User, trial_id: uuid.UUID) -> None:
    """Seção 11.3 — permitir remover uma tentativa com audit log (soft delete, Seção 16.1)."""
    trial = db.get(Trial, trial_id)
    if trial is None or trial.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found")
    session_training = _get_session_training_or_404(db, user, trial.session_training_id)

    trial.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    trial.deleted_by = user.id
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="trial_deleted",
        entity_type="trial",
        entity_id=trial.id,
    )
    db.commit()
    _recompute_alerts_after_trial_change(db, session_training)


def get_training_progress(db: DbSession, user: User, session_training_id: uuid.UUID) -> dict:
    """Seção 11.3 — calcular percentual de acerto por treino ao final e durante o atendimento."""
    session_training = _get_session_training_or_404(db, user, session_training_id)
    trials = (
        db.query(Trial)
        .filter(Trial.session_training_id == session_training.id, Trial.deleted_at.is_(None))
        .order_by(Trial.attempt_number)
        .all()
    )
    return {
        "session_training_id": session_training.id,
        "training_id": session_training.training_id,
        "trials": trials,
        "accuracy_pct": accuracy_pct(trials),
        "independence_pct": independence_pct(trials),
    }
