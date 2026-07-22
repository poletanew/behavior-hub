import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.reinforcer import (
    ReinforcerCreateRequest,
    ReinforcerResponse,
    SessionReinforcerCreateRequest,
    SessionReinforcerResponse,
)
from app.services import reinforcer_service

router = APIRouter(tags=["reinforcers"])


@router.post(
    "/patients/{patient_id}/reinforcers", response_model=ReinforcerResponse, status_code=status.HTTP_201_CREATED
)
def create_reinforcer(
    patient_id: uuid.UUID,
    payload: ReinforcerCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Addendum v3.0, RF-19 — cadastro de reforçador por paciente."""
    return reinforcer_service.create_reinforcer(db, user, patient_id, payload)


@router.get("/patients/{patient_id}/reinforcers", response_model=list[ReinforcerResponse])
def list_reinforcers(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return reinforcer_service.list_reinforcers(db, user, patient_id)


@router.post(
    "/sessions/{session_id}/reinforcers",
    response_model=SessionReinforcerResponse,
    status_code=status.HTTP_201_CREATED,
)
def link_reinforcer_to_session(
    session_id: uuid.UUID,
    payload: SessionReinforcerCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return reinforcer_service.link_reinforcer_to_session(db, user, session_id, payload)


@router.get("/sessions/{session_id}/reinforcers", response_model=list[SessionReinforcerResponse])
def list_session_reinforcers(
    session_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return reinforcer_service.list_session_reinforcers(db, user, session_id)
