import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.resource_link import ResourceLinkCreateRequest, ResourceLinkResponse
from app.services import resource_link_service

router = APIRouter(tags=["resource-links"])


@router.post("/resource-links", response_model=ResourceLinkResponse, status_code=status.HTTP_201_CREATED)
def create_resource_link(
    payload: ResourceLinkCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Seção 29.7 — vincula manualmente um recurso a um treino ou objetivo (Biblioteca Inteligente)."""
    return resource_link_service.create_link(db, user, payload)


@router.delete("/resource-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource_link(link_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resource_link_service.delete_link(db, user, link_id)


@router.get("/trainings/{training_id}/resource-links", response_model=list[ResourceLinkResponse])
def list_training_resource_links(
    training_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return resource_link_service.list_links_for_training(db, user, training_id)


@router.get("/objectives/{objective_id}/resource-links", response_model=list[ResourceLinkResponse])
def list_objective_resource_links(
    objective_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Seção 29.7 — recursos recomendados para o objetivo (diretos + via treinos vinculados)."""
    return resource_link_service.list_links_for_objective(db, user, objective_id)
