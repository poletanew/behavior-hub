import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.training import (
    TrainingAIFillRequest,
    TrainingAIFillResponse,
    TrainingCategoryResponse,
    TrainingCreateRequest,
    TrainingPatientLinkCreateRequest,
    TrainingPatientLinkResponse,
    TrainingResponse,
)
from app.services import training_service

router = APIRouter(tags=["training-library"])


@router.get("/training-categories", response_model=list[TrainingCategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return training_service.list_categories(db)


@router.get("/trainings", response_model=list[TrainingResponse])
def list_trainings(
    category_id: uuid.UUID | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 12.1 — busca por titulo/objetivo/palavra-chave e filtro por categoria."""
    return training_service.list_trainings(db, user, category_id=category_id, search=search)


@router.post("/trainings", response_model=TrainingResponse, status_code=status.HTTP_201_CREATED)
def create_training(
    payload: TrainingCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return training_service.create_custom_training(db, user, payload)


@router.post("/trainings/ai-fill", response_model=TrainingAIFillResponse)
async def ai_fill_training(
    payload: TrainingAIFillRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Seção 12.1 — "Preencher com IA" no Novo Treinamento: só título + categoria,
    a IA sugere objetivo/instrução discriminativa/resposta esperada/hierarquia de
    ajuda/critério de domínio como rascunho editável (revisão humana obrigatória)."""
    return await training_service.generate_training_ai_draft(db, payload.category_id, payload.title)


@router.delete("/trainings/{training_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_training(training_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    training_service.delete_custom_training(db, user, training_id)


@router.post(
    "/trainings/{training_id}/link",
    response_model=TrainingPatientLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def link_training_to_patient(
    training_id: uuid.UUID,
    payload: TrainingPatientLinkCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Addendum v2.1, RF-10 — "Vincular" treino a um paciente (treino prescrito)."""
    return training_service.link_training_to_patient(db, user, training_id, payload.patient_id)


@router.delete("/training-patient-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_training_from_patient(
    link_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    training_service.unlink_training_from_patient(db, user, link_id)


@router.get("/patients/{patient_id}/training-links", response_model=list[TrainingPatientLinkResponse])
def list_training_links_for_patient(
    patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return training_service.list_links_for_patient(db, user, patient_id)
