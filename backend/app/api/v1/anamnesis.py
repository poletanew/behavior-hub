import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.anamnesis import AnamnesisResponse, AnamnesisSaveRequest
from app.services import anamnesis_service

router = APIRouter(tags=["anamnesis"])


@router.put("/patients/{patient_id}/anamnesis", response_model=AnamnesisResponse)
def save_anamnesis(
    patient_id: uuid.UUID,
    payload: AnamnesisSaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Addendum v3.0, RF-21 — cria na primeira vez, edita depois (idempotente)."""
    return anamnesis_service.save_anamnesis(db, user, patient_id, payload)


@router.get("/patients/{patient_id}/anamnesis", response_model=AnamnesisResponse)
def get_anamnesis(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return anamnesis_service.get_anamnesis_or_404(db, user, patient_id)
