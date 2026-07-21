import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.aba import ABAAssignedPatientResponse, ABATrialReviewEntry, ATSummaryResponse
from app.services import aba_service

router = APIRouter(prefix="/aba", tags=["aba"])


@router.get("/ats", response_model=list[ATSummaryResponse])
def list_ats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return aba_service.list_ats(db, user)


@router.get("/ats/{at_id}/patients", response_model=list[ABAAssignedPatientResponse])
def list_patients_for_at(at_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return aba_service.list_patients_for_at(db, user, at_id)


@router.get("/trials", response_model=list[ABATrialReviewEntry])
def list_recent_trials(
    limit: int = Query(default=50, le=200), db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return aba_service.list_recent_trials(db, user, limit=limit)
