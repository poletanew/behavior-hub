import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import WaitlistStatus
from app.models.user import User
from app.schemas.waitlist import (
    WaitlistConvertRequest,
    WaitlistEntryCreateRequest,
    WaitlistEntryResponse,
    WaitlistEntryUpdateRequest,
)
from app.services import waitlist_service

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


@router.post("", response_model=WaitlistEntryResponse, status_code=201)
def create_waitlist_entry(
    payload: WaitlistEntryCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Seção 32.11 — Lista de Espera: cadastro simplificado antes da admissão formal."""
    return waitlist_service.create_entry(db, user, payload)


@router.get("", response_model=list[WaitlistEntryResponse])
def list_waitlist_entries(
    status: WaitlistStatus | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return waitlist_service.list_entries(db, user, status_filter=status)


@router.patch("/{entry_id}", response_model=WaitlistEntryResponse)
def update_waitlist_entry(
    entry_id: uuid.UUID,
    payload: WaitlistEntryUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return waitlist_service.update_entry(db, user, entry_id, payload)


@router.post("/{entry_id}/discard", response_model=WaitlistEntryResponse)
def discard_waitlist_entry(entry_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return waitlist_service.discard_entry(db, user, entry_id)


@router.post("/{entry_id}/convert", response_model=WaitlistEntryResponse)
def convert_waitlist_entry(
    entry_id: uuid.UUID,
    payload: WaitlistConvertRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 32.11 — converte em paciente completo sem redigitação."""
    return waitlist_service.convert_entry(db, user, entry_id, payload)
