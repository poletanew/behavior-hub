import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.reinforcer import Reinforcer, SessionReinforcer
from app.models.user import User
from app.schemas.reinforcer import ReinforcerCreateRequest, SessionReinforcerCreateRequest
from app.services import audit_service, patient_service, rbac_service, session_service


def create_reinforcer(db: Session, user: User, patient_id: uuid.UUID, payload: ReinforcerCreateRequest) -> Reinforcer:
    """Addendum v3.0, RF-19 — cadastro de reforçador por paciente."""
    if not rbac_service.can_register_session(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to register reinforcers")

    patient = patient_service.get_patient_or_404(db, user, patient_id)
    reinforcer = Reinforcer(
        clinic_id=patient.clinic_id,
        individual_owner_id=patient.individual_owner_id,
        patient_id=patient.id,
        name=payload.name,
        effectiveness_notes=payload.effectiveness_notes,
    )
    db.add(reinforcer)
    db.flush()

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="reinforcer_created",
        entity_type="reinforcer",
        entity_id=reinforcer.id,
        after={"patient_id": str(patient.id), "name": reinforcer.name},
    )
    db.commit()
    db.refresh(reinforcer)
    return reinforcer


def list_reinforcers(db: Session, user: User, patient_id: uuid.UUID) -> list[dict]:
    """Critério de aceite RF-19 — "ver ... quais reforçadores foram mais usados
    no período": cada reforçador já vem com a contagem de uso agregada."""
    patient_service.get_patient_or_404(db, user, patient_id)
    counts = dict(
        db.query(SessionReinforcer.reinforcer_id, func.count(SessionReinforcer.id))
        .join(Reinforcer, Reinforcer.id == SessionReinforcer.reinforcer_id)
        .filter(Reinforcer.patient_id == patient_id)
        .group_by(SessionReinforcer.reinforcer_id)
        .all()
    )
    reinforcers = db.query(Reinforcer).filter(Reinforcer.patient_id == patient_id).order_by(Reinforcer.name).all()
    return [
        {
            "id": reinforcer.id,
            "patient_id": reinforcer.patient_id,
            "name": reinforcer.name,
            "effectiveness_notes": reinforcer.effectiveness_notes,
            "usage_count": counts.get(reinforcer.id, 0),
        }
        for reinforcer in reinforcers
    ]


def _get_reinforcer_or_404(db: Session, user: User, reinforcer_id: uuid.UUID) -> Reinforcer:
    reinforcer = db.get(Reinforcer, reinforcer_id)
    if reinforcer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reinforcer not found")
    patient_service.get_patient_or_404(db, user, reinforcer.patient_id)
    return reinforcer


def link_reinforcer_to_session(
    db: Session, user: User, session_id: uuid.UUID, payload: SessionReinforcerCreateRequest
) -> dict:
    """Critério de aceite RF-19 — "vinculá-lo a uma sessão"."""
    if not rbac_service.can_register_session(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to register reinforcers")

    session = session_service.get_session_or_404(db, user, session_id)
    reinforcer = _get_reinforcer_or_404(db, user, payload.reinforcer_id)
    if reinforcer.patient_id != session.patient_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reinforcer does not belong to this patient")

    link = SessionReinforcer(
        session_id=session.id,
        reinforcer_id=reinforcer.id,
        effectiveness_note=payload.effectiveness_note,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return {
        "id": link.id,
        "session_id": link.session_id,
        "reinforcer_id": link.reinforcer_id,
        "reinforcer_name": reinforcer.name,
        "effectiveness_note": link.effectiveness_note,
        "used_at": link.used_at,
    }


def list_session_reinforcers(db: Session, user: User, session_id: uuid.UUID) -> list[dict]:
    session = session_service.get_session_or_404(db, user, session_id)
    links = (
        db.query(SessionReinforcer, Reinforcer.name)
        .join(Reinforcer, Reinforcer.id == SessionReinforcer.reinforcer_id)
        .filter(SessionReinforcer.session_id == session.id)
        .order_by(SessionReinforcer.used_at)
        .all()
    )
    return [
        {
            "id": link.id,
            "session_id": link.session_id,
            "reinforcer_id": link.reinforcer_id,
            "reinforcer_name": name,
            "effectiveness_note": link.effectiveness_note,
            "used_at": link.used_at,
        }
        for link, name in links
    ]
