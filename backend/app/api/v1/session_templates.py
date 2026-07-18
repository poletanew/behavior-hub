import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.session_template import SessionTemplateCreateRequest, SessionTemplateResponse
from app.services import session_template_service

router = APIRouter(prefix="/session-templates", tags=["session-templates"])


@router.get("", response_model=list[SessionTemplateResponse])
def list_templates(
    patient_id: uuid.UUID | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Seção 32.4 — templates genéricos da clínica + específicos do paciente informado."""
    return session_template_service.list_templates(db, user, patient_id=patient_id)


@router.post("", response_model=SessionTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: SessionTemplateCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return session_template_service.create_template(db, user, payload)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session_template_service.delete_template(db, user, template_id)
