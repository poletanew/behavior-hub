import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.checklist import (
    ChecklistResponseCreateRequest,
    ChecklistResponseDetail,
    ChecklistTemplateCreateRequest,
    ChecklistTemplateResponse,
)
from app.services import checklist_service

router = APIRouter(tags=["checklists"])


@router.post("/checklist-templates", response_model=ChecklistTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_checklist_template(
    payload: ChecklistTemplateCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return checklist_service.create_template(db, user, payload)


@router.get("/checklist-templates", response_model=list[ChecklistTemplateResponse])
def list_checklist_templates(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return checklist_service.list_templates(db, user)


@router.post(
    "/patients/{patient_id}/checklist-responses",
    response_model=ChecklistResponseDetail,
    status_code=status.HTTP_201_CREATED,
)
def apply_checklist(
    patient_id: uuid.UUID,
    payload: ChecklistResponseCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    response = checklist_service.apply_checklist(db, user, patient_id, payload)
    return checklist_service.get_response_detail(db, user, response.id)


@router.get("/patients/{patient_id}/checklist-responses", response_model=list[ChecklistResponseDetail])
def list_checklist_responses(
    patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return checklist_service.list_patient_responses(db, user, patient_id)
