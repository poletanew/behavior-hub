import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.family import (
    FamilyAccessResponse,
    FamilyAccessUpdateRequest,
    FamilyAudioMessageResponse,
    FamilyMessageCreateRequest,
    FamilyMessageResponse,
    FamilyRoutineLogResponse,
)
from app.services import family_access_service, family_portal_service

router = APIRouter(tags=["family-access"])


@router.get("/patients/{patient_id}/family-accesses", response_model=list[FamilyAccessResponse])
def list_family_accesses(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 29.6 — gestão, pelo lado da equipe, dos responsáveis com acesso ao Portal da Família."""
    return family_access_service.list_for_patient(db, user, patient_id)


@router.patch("/family-accesses/{access_id}", response_model=FamilyAccessResponse)
def update_family_access_whitelist(
    access_id: uuid.UUID,
    payload: FamilyAccessUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 17.2 — cada categoria da whitelist só é liberada por uma ação explícita aqui."""
    return family_access_service.update_whitelist(db, user, access_id, payload)


@router.post("/family-accesses/{access_id}/revoke", response_model=FamilyAccessResponse)
def revoke_family_access(access_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 17.2 — revogação imediata e auditada, encerrando as sessões ativas do responsável."""
    return family_access_service.revoke_access(db, user, access_id)


@router.get("/patients/{patient_id}/family-messages", response_model=list[FamilyMessageResponse])
def list_patient_family_messages(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return family_portal_service.list_messages_for_team(db, user, patient_id)


@router.post("/patients/{patient_id}/family-messages", response_model=FamilyMessageResponse, status_code=201)
def create_patient_family_message(
    patient_id: uuid.UUID,
    payload: FamilyMessageCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return family_portal_service.post_message_for_team(db, user, patient_id, payload.body)


@router.get("/patients/{patient_id}/routine-logs", response_model=list[FamilyRoutineLogResponse])
def list_patient_routine_logs(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Addendum v3.0, RF-29 — lado da equipe, visível antes do próximo atendimento."""
    return family_portal_service.list_routine_logs_for_team(db, user, patient_id)


@router.get("/patients/{patient_id}/audio-messages", response_model=list[FamilyAudioMessageResponse])
def list_patient_audio_messages(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Addendum v3.0, RF-30 — lado da equipe."""
    return family_portal_service.list_audio_messages_for_team(db, user, patient_id)
