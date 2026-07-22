import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.behavior_event import BehaviorEvent
from app.models.user import User
from app.schemas.behavior_event import BehaviorEventCreateRequest
from app.services import audit_service, patient_service, rbac_service, session_service


def create_behavior_event(
    db: Session, user: User, patient_id: uuid.UUID, payload: BehaviorEventCreateRequest
) -> BehaviorEvent:
    """Addendum v3.0, RF-18 — registro de comportamento-alvo (modelo ABC),
    independente das tentativas de treino, sempre ligado a um atendimento.
    Mesma permissão de "Registrar sessão" (Seção 17.1) já usada por Trial."""
    if not rbac_service.can_register_session(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to register behavior events")

    patient = patient_service.get_patient_or_404(db, user, patient_id)
    session = session_service.get_session_or_404(db, user, payload.session_id)
    if session.patient_id != patient.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session does not belong to this patient")

    event = BehaviorEvent(
        clinic_id=patient.clinic_id,
        individual_owner_id=patient.individual_owner_id,
        patient_id=patient.id,
        session_id=session.id,
        recorded_by_user_id=user.id,
        antecedent=payload.antecedent,
        behavior=payload.behavior,
        consequence=payload.consequence,
        frequency_count=payload.frequency_count,
        duration_seconds=payload.duration_seconds,
        intensity=payload.intensity,
        occurred_at=payload.occurred_at or datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(event)
    db.flush()

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="behavior_event_created",
        entity_type="behavior_event",
        entity_id=event.id,
        after={"patient_id": str(patient.id), "session_id": str(session.id)},
    )
    db.commit()
    db.refresh(event)
    return event


def list_behavior_events(
    db: Session, user: User, *, patient_id: uuid.UUID | None = None, session_id: uuid.UUID | None = None
) -> list[BehaviorEvent]:
    if patient_id is not None:
        patient_service.get_patient_or_404(db, user, patient_id)
        query = db.query(BehaviorEvent).filter(BehaviorEvent.patient_id == patient_id)
    elif session_id is not None:
        session = session_service.get_session_or_404(db, user, session_id)
        query = db.query(BehaviorEvent).filter(BehaviorEvent.session_id == session.id)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="patient_id or session_id is required")
    return query.order_by(BehaviorEvent.occurred_at.desc()).all()
