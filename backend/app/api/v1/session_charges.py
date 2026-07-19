import datetime
import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.session_charge import (
    SessionChargeCreateRequest,
    SessionChargeResponse,
    SessionChargeStatusUpdateRequest,
    SessionChargeUpdateRequest,
)
from app.services import session_charge_service

router = APIRouter(tags=["session-charges"])


@router.post("/sessions/{session_id}/charge", response_model=SessionChargeResponse, status_code=201)
def create_session_charge(
    session_id: uuid.UUID,
    payload: SessionChargeCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 32.10 — Faturamento por Sessão (Premium/Enterprise)."""
    return session_charge_service.create_charge(db, user, session_id, payload)


@router.get("/sessions/{session_id}/charge", response_model=SessionChargeResponse | None)
def get_session_charge(session_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return session_charge_service.get_charge_for_session(db, user, session_id)


@router.get("/patients/{patient_id}/session-charges", response_model=list[SessionChargeResponse])
def list_patient_session_charges(
    patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return session_charge_service.list_charges_for_patient(db, user, patient_id)


@router.patch("/session-charges/{charge_id}", response_model=SessionChargeResponse)
def update_session_charge(
    charge_id: uuid.UUID,
    payload: SessionChargeUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return session_charge_service.update_charge(db, user, charge_id, payload)


@router.post("/session-charges/{charge_id}/status", response_model=SessionChargeResponse)
def update_session_charge_status(
    charge_id: uuid.UUID,
    payload: SessionChargeStatusUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return session_charge_service.update_status(db, user, charge_id, payload.payment_status)


@router.get("/session-charges/export.csv")
def export_session_charges_csv(
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 32.10 — "exportação para o financeiro da clínica"."""
    content = session_charge_service.export_csv(db, user, date_from=date_from, date_to=date_to)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="session-charges.csv"'},
    )
