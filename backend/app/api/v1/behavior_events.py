import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.behavior_event import BehaviorEventCreateRequest, BehaviorEventResponse
from app.services import behavior_event_service

router = APIRouter(tags=["behavior-events"])


@router.post(
    "/patients/{patient_id}/behavior-events",
    response_model=BehaviorEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_behavior_event(
    patient_id: uuid.UUID,
    payload: BehaviorEventCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Addendum v3.0, RF-18 — registro de comportamento-alvo (modelo ABC)."""
    return behavior_event_service.create_behavior_event(db, user, patient_id, payload)


@router.get("/patients/{patient_id}/behavior-events", response_model=list[BehaviorEventResponse])
def list_patient_behavior_events(
    patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return behavior_event_service.list_behavior_events(db, user, patient_id=patient_id)


@router.get("/sessions/{session_id}/behavior-events", response_model=list[BehaviorEventResponse])
def list_session_behavior_events(
    session_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return behavior_event_service.list_behavior_events(db, user, session_id=session_id)
