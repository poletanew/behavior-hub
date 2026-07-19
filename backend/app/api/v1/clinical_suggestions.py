import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.clinical_suggestion import ClinicalSuggestionResponse
from app.services import clinical_suggestion_service, patient_service

router = APIRouter(tags=["clinical-suggestions"])


@router.get("/patients/{patient_id}/suggestions", response_model=list[ClinicalSuggestionResponse])
def list_patient_suggestions(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 29.1 (Fase 4b) — sugestões clínicas do paciente (pendentes e já decididas)."""
    patient = patient_service.get_patient_or_404(db, user, patient_id)
    return clinical_suggestion_service.list_suggestions(db, patient)


@router.post("/suggestions/{suggestion_id}/approve", response_model=ClinicalSuggestionResponse)
def approve_suggestion(suggestion_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return clinical_suggestion_service.approve_suggestion(db, user, suggestion_id)


@router.post("/suggestions/{suggestion_id}/dismiss", response_model=ClinicalSuggestionResponse)
def dismiss_suggestion(suggestion_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return clinical_suggestion_service.dismiss_suggestion(db, user, suggestion_id)
