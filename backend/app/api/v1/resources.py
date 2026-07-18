import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import ResourceVisibility
from app.models.user import User
from app.schemas.resource import ResourceResponse, ResourceWithUrlResponse
from app.services import resource_service

router = APIRouter(prefix="/resources", tags=["therapeutic-resources"])


@router.get("", response_model=list[ResourceResponse])
def list_resources(
    category: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 15 — biblioteca em lista/grade com busca e filtros."""
    return resource_service.list_resources(db, user, category=category, search=search)


@router.post("", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_resource(
    title: str = Form(...),
    description: str | None = Form(default=None),
    category: str | None = Form(default=None),
    suggested_age_range: str | None = Form(default=None),
    visibility: ResourceVisibility = Form(default=ResourceVisibility.PRIVATE),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 15 — upload de PDFs, imagens e atividades textuais conforme plano e permissão."""
    return await resource_service.upload_resource(
        db,
        user,
        title=title,
        description=description,
        category=category,
        suggested_age_range=suggested_age_range,
        visibility=visibility,
        file=file,
    )


@router.get("/{resource_id}", response_model=ResourceWithUrlResponse)
def get_resource(resource_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 15/17.2 — abre com URL temporária e assinada, nunca pública direta."""
    resource = resource_service.get_resource_or_404(db, user, resource_id)
    view_url = resource_service.get_view_url(resource)
    return ResourceWithUrlResponse(**ResourceResponse.model_validate(resource).model_dump(), view_url=view_url)


@router.delete("/{resource_id}", response_model=ResourceResponse)
def delete_resource(resource_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return resource_service.soft_delete_resource(db, user, resource_id)


@router.post("/{resource_id}/restore", response_model=ResourceResponse)
def restore_resource(resource_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return resource_service.restore_resource(db, user, resource_id)
