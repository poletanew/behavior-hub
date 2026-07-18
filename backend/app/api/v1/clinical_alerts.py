import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.clinical_alert import ClinicalAlertResponse, ClinicalAlertThresholdsUpdateRequest
from app.schemas.rbac import ClinicPermissionSettingsResponse
from app.services import clinical_alert_service, patient_service

router = APIRouter(tags=["clinical-alerts"])


@router.get("/patients/{patient_id}/alerts", response_model=list[ClinicalAlertResponse])
def list_patient_alerts(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 19.1/29.9 — alertas clínicos ativos do paciente."""
    patient = patient_service.get_patient_or_404(db, user, patient_id)
    return clinical_alert_service.list_active_alerts(db, patient)


@router.patch("/clinic/alert-thresholds", response_model=ClinicPermissionSettingsResponse)
def update_alert_thresholds(
    payload: ClinicalAlertThresholdsUpdateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Seção 29.1 — limiares configuráveis por clínica, restrito ao plano Enterprise."""
    return clinical_alert_service.update_thresholds(db, user, payload)
