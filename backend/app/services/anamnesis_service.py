import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.anamnesis import Anamnesis
from app.models.user import User
from app.schemas.anamnesis import AnamnesisSaveRequest
from app.services import audit_service, patient_service


def get_anamnesis_or_404(db: Session, user: User, patient_id: uuid.UUID) -> Anamnesis:
    """Addendum v3.0, RF-21 — "acessível a quem tem permissão de leitura de
    dados clínicos completos" (o mesmo gate usado por prontuário completo,
    plano de tratamento e relatórios — bloqueia o AT)."""
    patient_service.assert_full_clinical_access(user)
    patient = patient_service.get_patient_or_404(db, user, patient_id)
    anamnesis = db.query(Anamnesis).filter(Anamnesis.patient_id == patient.id).first()
    if anamnesis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anamnesis not found")
    return anamnesis


def get_anamnesis_or_none(db: Session, user: User, patient_id: uuid.UUID) -> Anamnesis | None:
    patient_service.assert_full_clinical_access(user)
    patient = patient_service.get_patient_or_404(db, user, patient_id)
    return db.query(Anamnesis).filter(Anamnesis.patient_id == patient.id).first()


def save_anamnesis(db: Session, user: User, patient_id: uuid.UUID, payload: AnamnesisSaveRequest) -> Anamnesis:
    """Cria a anamnese na primeira vez (evento fundacional citado na
    Timeline, Seção 29.2) e permite editá-la depois — é um formulário de
    admissão vivo, preenchido aos poucos, não um evento imutável."""
    patient_service.assert_full_clinical_access(user)
    patient = patient_service.get_patient_or_404(db, user, patient_id)

    anamnesis = db.query(Anamnesis).filter(Anamnesis.patient_id == patient.id).first()
    is_new = anamnesis is None
    if is_new:
        anamnesis = Anamnesis(
            clinic_id=patient.clinic_id,
            individual_owner_id=patient.individual_owner_id,
            patient_id=patient.id,
            created_by_user_id=user.id,
        )
        db.add(anamnesis)

    for field, value in payload.model_dump().items():
        setattr(anamnesis, field, value)
    db.flush()

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="anamnesis_created" if is_new else "anamnesis_updated",
        entity_type="anamnesis",
        entity_id=anamnesis.id,
        after={"patient_id": str(patient.id)},
    )
    db.commit()
    db.refresh(anamnesis)
    return anamnesis
