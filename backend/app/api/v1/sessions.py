import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.session import (
    AddTrainingsRequest,
    SessionCreateRequest,
    SessionResponse,
    SessionTrainingProgressResponse,
    TrialCreateRequest,
    TrialResponse,
    TrialUpdateRequest,
)
from app.schemas.session_template import (
    DuplicateSessionRequest,
    SaveAsTemplateRequest,
    SessionFromTemplateRequest,
    SessionTemplateResponse,
)
from app.services import session_service, session_template_service

router = APIRouter(tags=["sessions"])


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    patient_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 9.2 / 11.1 — mesma fonte de dados para Dashboard e Atendimentos."""
    return session_service.list_sessions(db, user, patient_id=patient_id)


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return session_service.create_session(db, user, payload)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """AC-07 — clicar no paciente em Sessions abre apenas o historico daquele paciente."""
    return session_service.get_session_or_404(db, user, session_id)


@router.post("/sessions/{session_id}/trainings", response_model=SessionResponse)
def add_trainings(
    session_id: uuid.UUID,
    payload: AddTrainingsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return session_service.add_trainings(db, user, session_id, payload.training_ids)


@router.post(
    "/session-trainings/{session_training_id}/trials",
    response_model=TrialResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_trial(
    session_training_id: uuid.UUID,
    payload: TrialCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 11.3 / AC-04 — cria a proxima tentativa individualizada (Tentativa 1, 2, 3...)."""
    return session_service.add_trial(db, user, session_training_id, payload)


@router.get(
    "/session-trainings/{session_training_id}/progress",
    response_model=SessionTrainingProgressResponse,
)
def get_progress(
    session_training_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """AC-05 — percentual de acerto calculado com a formula da Seção 14.4."""
    return session_service.get_training_progress(db, user, session_training_id)


@router.patch("/trials/{trial_id}", response_model=TrialResponse)
def update_trial(
    trial_id: uuid.UUID,
    payload: TrialUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return session_service.update_trial(db, user, trial_id, payload)


@router.delete("/trials/{trial_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trial(trial_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session_service.delete_trial(db, user, trial_id)


@router.post(
    "/sessions/{session_id}/save-as-template",
    response_model=SessionTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def save_as_template(
    session_id: uuid.UUID,
    payload: SaveAsTemplateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 32.4 — salvar um modelo de atendimento a partir de uma sessão existente."""
    return session_template_service.save_session_as_template(db, user, session_id, payload.name)


@router.post(
    "/sessions/from-template/{template_id}", response_model=SessionResponse, status_code=status.HTTP_201_CREATED
)
def create_session_from_template(
    template_id: uuid.UUID,
    payload: SessionFromTemplateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 32.4 — iniciar uma nova sessão a partir do modelo em um clique."""
    return session_template_service.create_session_from_template(db, user, template_id, payload)


@router.post("/sessions/{session_id}/duplicate", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def duplicate_session(
    session_id: uuid.UUID,
    payload: DuplicateSessionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 32.4 — duplicar a sessão anterior do mesmo paciente como ponto de partida."""
    return session_template_service.duplicate_session(db, user, session_id, payload)
