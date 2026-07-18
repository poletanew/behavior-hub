import datetime
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.enums import ResourceType, ResourceVisibility, UserType
from app.models.resource import Resource
from app.models.user import User
from app.services import audit_service, file_service, rbac_service

# Seção 34 — "regras de armazenamento e tamanho de arquivos" fica marcada como
# pendente de confirmação do Product Owner; usamos um padrão conservador de
# engenharia até essa decisão de produto ser confirmada.
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES: dict[str, ResourceType] = {
    "application/pdf": ResourceType.PDF,
    "image/png": ResourceType.IMAGE,
    "image/jpeg": ResourceType.IMAGE,
    "image/webp": ResourceType.IMAGE,
    "text/plain": ResourceType.TEXT,
}


def _tenant_scope_filter(user: User):
    if user.clinic_id is not None:
        return or_(
            Resource.clinic_id == user.clinic_id,
            Resource.individual_owner_id == user.id,
        )
    return Resource.individual_owner_id == user.id


def _tenant_key(user: User) -> str:
    return f"clinic-{user.clinic_id}" if user.clinic_id else f"user-{user.id}"


def list_resources(
    db: Session, user: User, *, category: str | None = None, search: str | None = None
) -> list[Resource]:
    """Seção 15 — biblioteca com busca e filtros; recursos privados só aparecem para o autor."""
    query = db.query(Resource).filter(_tenant_scope_filter(user), Resource.deleted_at.is_(None))
    if user.clinic_id is not None:
        # Dentro da clínica, só mostra privados de outros profissionais se forem próprios.
        query = query.filter(
            or_(
                Resource.visibility == ResourceVisibility.CLINIC_SHARED,
                Resource.uploaded_by_user_id == user.id,
            )
        )
    if category:
        query = query.filter(Resource.category == category)
    if search:
        like = f"%{search.lower()}%"
        query = query.filter(Resource.title.ilike(like))
    return query.order_by(Resource.title).all()


def get_resource_or_404(db: Session, user: User, resource_id: uuid.UUID, *, include_deleted: bool = False) -> Resource:
    query = db.query(Resource).filter(Resource.id == resource_id, _tenant_scope_filter(user))
    if not include_deleted:
        query = query.filter(Resource.deleted_at.is_(None))
    resource = query.first()
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    if (
        user.clinic_id is not None
        and resource.visibility == ResourceVisibility.PRIVATE
        and resource.uploaded_by_user_id != user.id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return resource


async def upload_resource(
    db: Session,
    user: User,
    *,
    title: str,
    description: str | None,
    category: str | None,
    suggested_age_range: str | None,
    visibility: ResourceVisibility,
    file: UploadFile,
) -> Resource:
    """Seção 15 — permitir upload de PDFs, imagens e atividades textuais."""
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {content_type}",
        )

    body = await file.read()
    if len(body) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds size limit")

    if visibility == ResourceVisibility.CLINIC_SHARED and user.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Individual accounts cannot share resources with a clinic")

    key = f"resources/{_tenant_key(user)}/{uuid.uuid4()}-{file.filename}"
    file_service.upload_object(key, body, content_type)

    resource = Resource(
        clinic_id=user.clinic_id,
        individual_owner_id=user.id if user.clinic_id is None else None,
        title=title,
        description=description,
        category=category,
        suggested_age_range=suggested_age_range,
        resource_type=ALLOWED_CONTENT_TYPES[content_type],
        file_key=key,
        original_filename=file.filename or "arquivo",
        content_type=content_type,
        size_bytes=len(body),
        visibility=visibility,
        uploaded_by_user_id=user.id,
    )
    db.add(resource)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="resource_uploaded",
        entity_type="resource",
        entity_id=resource.id,
        after={"title": title},
    )
    db.commit()
    db.refresh(resource)
    return resource


def get_view_url(resource: Resource) -> str:
    return file_service.generate_presigned_url(resource.file_key)


def soft_delete_resource(db: Session, user: User, resource_id: uuid.UUID) -> Resource:
    resource = get_resource_or_404(db, user, resource_id)
    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL) and resource.uploaded_by_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to remove this resource")

    resource.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    resource.deleted_by = user.id
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="resource_deleted",
        entity_type="resource",
        entity_id=resource.id,
    )
    db.commit()
    db.refresh(resource)
    return resource


def restore_resource(db: Session, user: User, resource_id: uuid.UUID) -> Resource:
    resource = get_resource_or_404(db, user, resource_id, include_deleted=True)
    if resource.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resource is not deleted")
    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL) and not rbac_service.can_restore_deleted_data(
        db, user
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to restore resources")

    resource.deleted_at = None
    resource.deleted_by = None
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="resource_restored",
        entity_type="resource",
        entity_id=resource.id,
    )
    db.commit()
    db.refresh(resource)
    return resource
