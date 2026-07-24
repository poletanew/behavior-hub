import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session as DbSession

from app.models.enums import TrainingLinkStatus, TrainingVisibility
from app.models.training import Training, TrainingCategory
from app.models.training_patient_link import TrainingPatientLink
from app.models.user import User
from app.schemas.training import TrainingAIFillResponse, TrainingCreateRequest, TrainingPatientLinkResponse
from app.services import ai_chat_service, patient_service

TRAINING_AI_FILL_SYSTEM_PROMPT = (
    "Você ajuda a estruturar um novo treino da Biblioteca de Treino do Behavior Hub, "
    "sistema para terapia infantil (ABA, Psicologia, Fonoaudiologia, Terapia Ocupacional "
    "e áreas afins). Responda APENAS com um objeto JSON válido, sem markdown, sem crases, "
    "exatamente no formato: {\"objective\": string, \"discriminative_instruction\": string, "
    "\"expected_response\": string, \"prompt_hierarchy\": string, \"mastery_criteria\": string}. "
    "Use linguagem de sugestão clínica revisável, nunca diagnóstico ou causalidade definitiva."
)


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


async def generate_training_ai_draft(db: DbSession, category_id: uuid.UUID, title: str) -> TrainingAIFillResponse:
    """Seção 12.1 — "Preencher com IA" no Novo Treinamento: a partir só do título
    e da categoria, gera um rascunho editável dos demais campos. Revisão humana
    obrigatória antes de salvar (mesma regra do Plano de Tratamento/Recursos)."""
    category = db.get(TrainingCategory, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    user_prompt = f"Categoria: {category.name}\nTítulo do treino: {title}\n\nGere a estrutura completa deste treino."
    draft = await ai_chat_service.generate_json(TRAINING_AI_FILL_SYSTEM_PROMPT, user_prompt)
    return TrainingAIFillResponse(
        objective=draft.get("objective", ""),
        discriminative_instruction=draft.get("discriminative_instruction", ""),
        expected_response=draft.get("expected_response", ""),
        prompt_hierarchy=draft.get("prompt_hierarchy", ""),
        mastery_criteria=draft.get("mastery_criteria", ""),
    )


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
        ai_generated=payload.ai_generated,
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


def _to_link_response(link: TrainingPatientLink, training_title: str) -> TrainingPatientLinkResponse:
    return TrainingPatientLinkResponse(
        id=link.id,
        training_id=link.training_id,
        training_title=training_title,
        patient_id=link.patient_id,
        status=link.status,
        linked_by_user_id=link.linked_by_user_id,
        linked_at=link.linked_at,
    )


def link_training_to_patient(
    db: DbSession, user: User, training_id: uuid.UUID, patient_id: uuid.UUID
) -> TrainingPatientLinkResponse:
    """Addendum v2.1, RF-10 — "Vincular" um treino a um paciente ("treino prescrito")."""
    training = get_training_or_404(db, training_id)
    patient = patient_service.get_patient_or_404(db, user, patient_id)

    existing = (
        db.query(TrainingPatientLink)
        .filter(TrainingPatientLink.training_id == training.id, TrainingPatientLink.patient_id == patient.id)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Training already linked to this patient")

    link = TrainingPatientLink(
        training_id=training.id,
        patient_id=patient.id,
        linked_by_user_id=user.id,
        linked_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return _to_link_response(link, training.title)


def unlink_training_from_patient(db: DbSession, user: User, link_id: uuid.UUID) -> None:
    link = db.get(TrainingPatientLink, link_id)
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    # Garante isolamento de tenant: só quem acessa o paciente pode desvincular.
    patient_service.get_patient_or_404(db, user, link.patient_id)

    db.delete(link)
    db.commit()


def list_links_for_patient(db: DbSession, user: User, patient_id: uuid.UUID) -> list[TrainingPatientLinkResponse]:
    patient = patient_service.get_patient_or_404(db, user, patient_id)
    links = db.query(TrainingPatientLink).filter(TrainingPatientLink.patient_id == patient.id).all()
    if not links:
        return []
    training_ids = [link.training_id for link in links]
    trainings = {t.id: t for t in db.query(Training).filter(Training.id.in_(training_ids)).all()}
    return [_to_link_response(link, trainings[link.training_id].title) for link in links]


def mark_links_applied(db: DbSession, patient_id: uuid.UUID, training_ids: list[uuid.UUID]) -> None:
    """Chamado por session_service.create_session — a primeira sessão que
    efetivamente usa um treino prescrito passa o vínculo de "prescrito" para
    "aplicado", sem precisar de nenhuma ação manual extra do profissional."""
    if not training_ids:
        return
    db.query(TrainingPatientLink).filter(
        TrainingPatientLink.patient_id == patient_id,
        TrainingPatientLink.training_id.in_(training_ids),
        TrainingPatientLink.status == TrainingLinkStatus.PRESCRIBED,
    ).update({"status": TrainingLinkStatus.APPLIED}, synchronize_session=False)
