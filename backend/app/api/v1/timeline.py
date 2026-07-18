import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.timeline import TimelineEntryResponse
from app.services import patient_service, timeline_service

router = APIRouter(tags=["timeline"])


@router.get("/patients/{patient_id}/timeline", response_model=list[TimelineEntryResponse])
def get_patient_timeline(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 19.1/29.2 — timeline clínica consolidada do paciente."""
    patient = patient_service.get_patient_or_404(db, user, patient_id)
    return timeline_service.get_patient_timeline(db, patient)
