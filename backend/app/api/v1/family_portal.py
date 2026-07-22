import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.family import (
    FamilyApplierObjectiveResponse,
    FamilyApplyObjectiveRequest,
    FamilyApplyObjectiveResponse,
    FamilyAppointmentResponse,
    FamilyEvolutionResponse,
    FamilyGuidanceResponse,
    FamilyMessageCreateRequest,
    FamilyMessageResponse,
    FamilyMyAccessResponse,
)
from app.schemas.resource_link import ResourceLinkResponse
from app.schemas.white_label import PublicBrandingResponse
from app.services import family_portal_service

router = APIRouter(prefix="/family-portal", tags=["family-portal"])


@router.get("/my-accesses", response_model=list[FamilyMyAccessResponse])
def list_my_accesses(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 29.6 — pacientes (e categorias liberadas) visíveis para este responsável."""
    return family_portal_service.list_my_accesses(db, user)


@router.get("/patients/{patient_id}/branding", response_model=PublicBrandingResponse)
def get_patient_branding(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 32.9 — identidade visual (logo/cor/nome) da clínica do paciente, quando Enterprise."""
    return family_portal_service.get_branding(db, user, patient_id)


@router.get("/patients/{patient_id}/evolution", response_model=FamilyEvolutionResponse)
def get_patient_evolution(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return family_portal_service.get_evolution(db, user, patient_id)


@router.get("/patients/{patient_id}/appointments", response_model=list[FamilyAppointmentResponse])
def list_patient_appointments(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return family_portal_service.list_upcoming_appointments(db, user, patient_id)


@router.get("/patients/{patient_id}/guidance", response_model=list[FamilyGuidanceResponse])
def list_patient_guidance(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return family_portal_service.list_team_guidance(db, user, patient_id)


@router.get("/patients/{patient_id}/materials", response_model=list[ResourceLinkResponse])
def list_patient_materials(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return family_portal_service.list_home_materials(db, user, patient_id)


@router.get("/patients/{patient_id}/messages", response_model=list[FamilyMessageResponse])
def list_patient_messages(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return family_portal_service.list_messages(db, user, patient_id)


@router.post("/patients/{patient_id}/messages", response_model=FamilyMessageResponse, status_code=201)
def create_patient_message(
    patient_id: uuid.UUID,
    payload: FamilyMessageCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return family_portal_service.post_message(db, user, patient_id, payload.body)


@router.get("/patients/{patient_id}/applier-objectives", response_model=list[FamilyApplierObjectiveResponse])
def list_applier_objectives(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Addendum v3.0, RF-25 — objetivos em que este responsável foi marcado como aplicador."""
    return family_portal_service.list_applier_objectives(db, user, patient_id)


@router.post(
    "/patients/{patient_id}/applier-objectives/{objective_id}/apply", response_model=FamilyApplyObjectiveResponse
)
def apply_objective_today(
    patient_id: uuid.UUID,
    objective_id: uuid.UUID,
    payload: FamilyApplyObjectiveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Addendum v3.0, RF-25 — critério de aceite: registrar "apliquei hoje"."""
    return family_portal_service.record_objective_application(db, user, patient_id, objective_id, payload.notes)
