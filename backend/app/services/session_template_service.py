import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.session import ClinicalSession, SessionTraining
from app.models.session_template import SessionTemplate, SessionTemplateTraining
from app.models.training import Training
from app.models.user import User
from app.schemas.session import SessionCreateRequest
from app.schemas.session_template import DuplicateSessionRequest, SessionFromTemplateRequest, SessionTemplateCreateRequest
from app.services import patient_service, session_service


def _tenant_scope_filter(user: User):
    if user.clinic_id is not None:
        return SessionTemplate.clinic_id == user.clinic_id
    return SessionTemplate.individual_owner_id == user.id


def list_templates(db: Session, user: User, *, patient_id: uuid.UUID | None = None) -> list[SessionTemplate]:
    """Seção 32.4 — templates genéricos da clínica (patient_id nulo) mais os
    específicos do paciente informado."""
    query = db.query(SessionTemplate).filter(_tenant_scope_filter(user))
    if patient_id is not None:
        patient_service.get_patient_or_404(db, user, patient_id)
        query = query.filter(or_(SessionTemplate.patient_id == patient_id, SessionTemplate.patient_id.is_(None)))
    return query.order_by(SessionTemplate.name).all()


def create_template(db: Session, user: User, payload: SessionTemplateCreateRequest) -> SessionTemplate:
    if payload.patient_id is not None:
        patient_service.get_patient_or_404(db, user, payload.patient_id)

    template = SessionTemplate(
        clinic_id=user.clinic_id,
        individual_owner_id=user.id if user.clinic_id is None else None,
        patient_id=payload.patient_id,
        name=payload.name,
        created_by_user_id=user.id,
    )
    db.add(template)
    db.flush()

    for idx, training_id in enumerate(payload.training_ids, start=1):
        if db.get(Training, training_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Training {training_id} not found")
        db.add(SessionTemplateTraining(template_id=template.id, training_id=training_id, sequence=idx))

    db.commit()
    db.refresh(template)
    return template


def save_session_as_template(db: Session, user: User, session_id: uuid.UUID, name: str) -> SessionTemplate:
    """Seção 32.4 — salvar um modelo de atendimento a partir de uma sessão existente."""
    session = session_service.get_session_or_404(db, user, session_id)
    session_trainings = (
        db.query(SessionTraining).filter(SessionTraining.session_id == session.id).order_by(SessionTraining.sequence).all()
    )

    template = SessionTemplate(
        clinic_id=user.clinic_id,
        individual_owner_id=user.id if user.clinic_id is None else None,
        patient_id=session.patient_id,
        name=name,
        created_by_user_id=user.id,
    )
    db.add(template)
    db.flush()

    for idx, st in enumerate(session_trainings, start=1):
        db.add(SessionTemplateTraining(template_id=template.id, training_id=st.training_id, sequence=idx))

    db.commit()
    db.refresh(template)
    return template


def delete_template(db: Session, user: User, template_id: uuid.UUID) -> None:
    template = db.query(SessionTemplate).filter(SessionTemplate.id == template_id, _tenant_scope_filter(user)).first()
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    db.delete(template)
    db.commit()


def _get_template_or_404(db: Session, user: User, template_id: uuid.UUID) -> SessionTemplate:
    template = db.query(SessionTemplate).filter(SessionTemplate.id == template_id, _tenant_scope_filter(user)).first()
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


def create_session_from_template(
    db: Session, user: User, template_id: uuid.UUID, payload: SessionFromTemplateRequest
) -> ClinicalSession:
    template = _get_template_or_404(db, user, template_id)
    if template.patient_id is not None and template.patient_id != payload.patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This template is specific to a different patient"
        )

    training_ids = [
        row[0]
        for row in db.query(SessionTemplateTraining.training_id)
        .filter(SessionTemplateTraining.template_id == template.id)
        .order_by(SessionTemplateTraining.sequence)
        .all()
    ]
    request = SessionCreateRequest(
        patient_id=payload.patient_id,
        professional_id=payload.professional_id,
        occurred_at=payload.occurred_at,
        notes=payload.notes,
        training_ids=training_ids,
    )
    return session_service.create_session(db, user, request)


def duplicate_session(
    db: Session, user: User, session_id: uuid.UUID, payload: DuplicateSessionRequest
) -> ClinicalSession:
    """Seção 32.4 — duplicar a sessão anterior do mesmo paciente como ponto de partida."""
    source = session_service.get_session_or_404(db, user, session_id)
    training_ids = [
        row[0]
        for row in db.query(SessionTraining.training_id)
        .filter(SessionTraining.session_id == source.id)
        .order_by(SessionTraining.sequence)
        .all()
    ]
    request = SessionCreateRequest(
        patient_id=source.patient_id,
        professional_id=payload.professional_id or source.professional_id,
        occurred_at=payload.occurred_at,
        notes=payload.notes,
        training_ids=training_ids,
    )
    return session_service.create_session(db, user, request)
