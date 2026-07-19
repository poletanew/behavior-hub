import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import TrainingVisibility, UserType
from app.models.resource import Resource
from app.models.resource_link import ResourceLink
from app.models.training import Training
from app.models.treatment_plan import ObjectiveTraining
from app.models.user import User
from app.schemas.resource_link import ResourceLinkCreateRequest
from app.services import audit_service, resource_service, treatment_plan_service


def _training_visible(db: Session, user: User, training_id: uuid.UUID) -> Training | None:
    training = db.get(Training, training_id)
    if training is None:
        return None
    if training.visibility == TrainingVisibility.SYSTEM:
        return training
    if training.visibility == TrainingVisibility.CLINIC_SHARED and user.clinic_id is not None and training.clinic_id == user.clinic_id:
        return training
    if training.visibility == TrainingVisibility.PRIVATE and training.owner_user_id == user.id:
        return training
    return None


def _resource_visible(user: User, resource: Resource) -> bool:
    """Seção 15 — mesma regra de `resource_service.list_resources`: privados de
    outro profissional não aparecem, mesmo dentro da mesma clínica."""
    if user.clinic_id is not None and resource.visibility.value == "private" and resource.uploaded_by_user_id != user.id:
        return False
    return True


def _to_response(link: ResourceLink, resource: Resource) -> dict:
    return {
        "id": link.id,
        "resource_id": link.resource_id,
        "resource_title": resource.title,
        "resource_type": resource.resource_type.value,
        "training_id": link.training_id,
        "objective_id": link.objective_id,
        "relevance_score": link.relevance_score,
        "created_by_user_id": link.created_by_user_id,
        "created_at": link.created_at,
    }


def create_link(db: Session, user: User, payload: ResourceLinkCreateRequest) -> dict:
    """Seção 29.7 — vínculo manual (tagueamento) recurso↔treino ou
    recurso↔objetivo; nunca inferido automaticamente por IA."""
    resource = resource_service.get_resource_or_404(db, user, payload.resource_id)

    if payload.training_id is not None:
        if _training_visible(db, user, payload.training_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
        existing = (
            db.query(ResourceLink)
            .filter(ResourceLink.resource_id == resource.id, ResourceLink.training_id == payload.training_id)
            .first()
        )
    else:
        treatment_plan_service.get_objective(db, user, payload.objective_id)
        existing = (
            db.query(ResourceLink)
            .filter(ResourceLink.resource_id == resource.id, ResourceLink.objective_id == payload.objective_id)
            .first()
        )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This resource is already linked to this target")

    link = ResourceLink(
        resource_id=resource.id,
        training_id=payload.training_id,
        objective_id=payload.objective_id,
        relevance_score=payload.relevance_score,
        created_by_user_id=user.id,
    )
    db.add(link)
    db.flush()
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="resource_link_created",
        entity_type="resource_link",
        entity_id=link.id,
        after={
            "resource_id": str(resource.id),
            "training_id": str(payload.training_id) if payload.training_id else None,
            "objective_id": str(payload.objective_id) if payload.objective_id else None,
        },
    )
    db.commit()
    db.refresh(link)
    return _to_response(link, resource)


def delete_link(db: Session, user: User, link_id: uuid.UUID) -> None:
    link = db.get(ResourceLink, link_id)
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource link not found")
    resource_service.get_resource_or_404(db, user, link.resource_id)

    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL) and link.created_by_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to remove this link")

    audit_service.record(
        db, actor_user_id=user.id, action="resource_link_deleted", entity_type="resource_link", entity_id=link.id
    )
    db.delete(link)
    db.commit()


def list_links_for_training(db: Session, user: User, training_id: uuid.UUID) -> list[dict]:
    if _training_visible(db, user, training_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")

    rows = (
        db.query(ResourceLink, Resource)
        .join(Resource, ResourceLink.resource_id == Resource.id)
        .filter(ResourceLink.training_id == training_id, Resource.deleted_at.is_(None))
        .all()
    )
    visible = [(link, resource) for link, resource in rows if _resource_visible(user, resource)]
    visible.sort(key=lambda pair: -pair[0].relevance_score)
    return [_to_response(link, resource) for link, resource in visible]


def list_links_for_objective(db: Session, user: User, objective_id: uuid.UUID) -> list[dict]:
    """Seção 29.7 — "ao trabalhar um objetivo específico, recomenda
    automaticamente atividades... relacionadas ao mesmo objetivo": agrega
    vínculos diretos ao objetivo com vínculos dos treinos que o objetivo usa
    (ObjectiveTraining), já que um recurso tagueado para o treino de um
    objetivo é igualmente relevante para esse objetivo."""
    _patient, _objective = treatment_plan_service.get_objective(db, user, objective_id)

    direct = (
        db.query(ResourceLink, Resource)
        .join(Resource, ResourceLink.resource_id == Resource.id)
        .filter(ResourceLink.objective_id == objective_id, Resource.deleted_at.is_(None))
        .all()
    )
    training_ids = [
        row[0] for row in db.query(ObjectiveTraining.training_id).filter(ObjectiveTraining.objective_id == objective_id).all()
    ]
    via_training = []
    if training_ids:
        via_training = (
            db.query(ResourceLink, Resource)
            .join(Resource, ResourceLink.resource_id == Resource.id)
            .filter(ResourceLink.training_id.in_(training_ids), Resource.deleted_at.is_(None))
            .all()
        )

    combined: dict[uuid.UUID, tuple[ResourceLink, Resource]] = {}
    for link, resource in direct + via_training:
        if not _resource_visible(user, resource):
            continue
        existing = combined.get(resource.id)
        if existing is None or link.relevance_score > existing[0].relevance_score:
            combined[resource.id] = (link, resource)

    ordered = sorted(combined.values(), key=lambda pair: -pair[0].relevance_score)
    return [_to_response(link, resource) for link, resource in ordered]
