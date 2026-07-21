import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.at_portal import ATApplyTrainingRequest, ATPatientResponse
from app.schemas.session import SessionResponse
from app.schemas.training import TrainingPatientLinkResponse
from app.services import at_portal_service

router = APIRouter(prefix="/at-portal", tags=["at-portal"])


@router.get("/patients", response_model=list[ATPatientResponse])
def list_assigned_patients(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return at_portal_service.list_assigned_patients(db, user)


@router.get("/patients/{patient_id}/trainings", response_model=list[TrainingPatientLinkResponse])
def list_prescribed_trainings(
    patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return at_portal_service.list_prescribed_trainings(db, user, patient_id)


@router.post("/patients/{patient_id}/apply", response_model=SessionResponse, status_code=201)
def apply_training(
    patient_id: uuid.UUID,
    payload: ATApplyTrainingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return at_portal_service.apply_training(db, user, patient_id, payload)
