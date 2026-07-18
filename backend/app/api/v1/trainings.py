import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.training import TrainingCategoryResponse, TrainingCreateRequest, TrainingResponse
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


@router.delete("/trainings/{training_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_training(training_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    training_service.delete_custom_training(db, user, training_id)
