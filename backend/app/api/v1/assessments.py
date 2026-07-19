import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import AssessmentProtocol
from app.models.user import User
from app.schemas.assessment import (
    AssessmentComparisonResponse,
    AssessmentCreateRequest,
    AssessmentResponse,
    AssessmentUpdateRequest,
    ProtocolDefinitionResponse,
)
from app.services import assessment_protocols, assessment_service

router = APIRouter(tags=["assessments"])


@router.get("/assessment-protocols", response_model=list[ProtocolDefinitionResponse])
def list_protocols():
    """Seção 30.1 — protocolos-piloto disponíveis e seus domínios (ProtocolDefinition)."""
    return assessment_protocols.list_protocol_definitions()


@router.post("/patients/{patient_id}/assessments", response_model=AssessmentResponse, status_code=201)
def create_assessment(
    patient_id: uuid.UUID,
    payload: AssessmentCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return assessment_service.create_assessment(db, user, patient_id, payload)


@router.get("/patients/{patient_id}/assessments", response_model=list[AssessmentResponse])
def list_assessments(
    patient_id: uuid.UUID,
    protocol: AssessmentProtocol | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return assessment_service.list_assessments(db, user, patient_id, protocol)


@router.get("/patients/{patient_id}/assessments/compare", response_model=AssessmentComparisonResponse)
def compare_assessments(
    patient_id: uuid.UUID,
    protocol: AssessmentProtocol,
    assessment_ids: list[uuid.UUID] = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 30.2/AC-19 — ganho absoluto e percentual por domínio entre a
    avaliação mais antiga e a mais recente do conjunto selecionado."""
    return assessment_service.compare_assessments(db, user, patient_id, protocol, assessment_ids)


@router.get("/assessments/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(assessment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return assessment_service.get_assessment(db, user, assessment_id)


@router.patch("/assessments/{assessment_id}", response_model=AssessmentResponse)
def update_assessment(
    assessment_id: uuid.UUID,
    payload: AssessmentUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return assessment_service.update_assessment(db, user, assessment_id, payload)


@router.delete("/assessments/{assessment_id}", status_code=204)
def delete_assessment(assessment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    assessment_service.soft_delete_assessment(db, user, assessment_id)
