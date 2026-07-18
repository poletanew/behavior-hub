import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session as DbSession

from app.models.enums import TrainingVisibility
from app.models.training import Training, TrainingCategory
from app.models.user import User
from app.schemas.training import TrainingCreateRequest


def list_categories(db: DbSession) -> list[TrainingCategory]:
    return db.query(TrainingCategory).order_by(TrainingCategory.name).all()


def list_trainings(
    db: DbSession,
    user: User,
    *,
    category_id: uuid.UUID | None = None,
    search: str | None = None,
) -> list[Training]:
    """Seção 12.1 — busca por titulo/objetivo, filtro por categoria; inclui treinos de
    sistema, os da clinica/individuo e privados do proprio usuario."""
    visibility_scope = [Training.visibility == TrainingVisibility.SYSTEM]
    if user.clinic_id is not None:
        visibility_scope.append(
            (Training.visibility == TrainingVisibility.CLINIC_SHARED) & (Training.clinic_id == user.clinic_id)
        )
    visibility_scope.append(
        (Training.visibility == TrainingVisibility.PRIVATE) & (Training.owner_user_id == user.id)
    )

    query = db.query(Training).filter(or_(*visibility_scope))
    if category_id is not None:
        query = query.filter(Training.category_id == category_id)
    if search:
        like = f"%{search.lower()}%"
        query = query.filter(
            or_(Training.title.ilike(like), Training.objective.ilike(like))
        )
    return query.order_by(Training.title).all()


def get_training_or_404(db: DbSession, training_id: uuid.UUID) -> Training:
    training = db.get(Training, training_id)
    if training is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
    return training


def create_custom_training(db: DbSession, user: User, payload: TrainingCreateRequest) -> Training:
    """Seção 12.1 — treinos personalizados podem ser privados ou compartilhados com a clinica."""
    category = db.get(TrainingCategory, payload.category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    training = Training(
        category_id=payload.category_id,
        title=payload.title,
        objective=payload.objective,
        discriminative_instruction=payload.discriminative_instruction,
        expected_response=payload.expected_response,
        prompt_hierarchy=payload.prompt_hierarchy,
        mastery_criteria=payload.mastery_criteria,
        notes=payload.notes,
        suggested_age_range=payload.suggested_age_range,
        visibility=TrainingVisibility.CLINIC_SHARED if user.clinic_id else TrainingVisibility.PRIVATE,
        clinic_id=user.clinic_id,
        owner_user_id=user.id if user.clinic_id is None else None,
    )
    db.add(training)
    db.commit()
    db.refresh(training)
    return training


def delete_custom_training(db: DbSession, user: User, training_id: uuid.UUID) -> None:
    """Seção 12.1 — treinos de sistema sao protegidos contra exclusao."""
    training = get_training_or_404(db, training_id)
    if training.is_system_protected():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System trainings cannot be deleted")

    owns_it = (
        (user.clinic_id is not None and training.clinic_id == user.clinic_id)
        or (user.clinic_id is None and training.owner_user_id == user.id)
    )
    if not owns_it:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to delete this training")

    db.delete(training)
    db.commit()
