import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import UserType
from app.models.user import User
from app.schemas.patient import (
    PatientAssignmentCreateRequest,
    PatientAssignmentResponse,
    PatientCreateRequest,
    PatientResponse,
    PatientUpdateRequest,
)
from app.schemas.patient_import import PatientImportCommitResponse, PatientImportPreviewResponse
from app.services import csv_import_service, patient_service, rbac_service

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientResponse])
def list_patients(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 10.1 — permite zero pacientes sem erros; contagem so considera ativos e nao deletados."""
    return patient_service.list_patients(db, user)


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return patient_service.create_patient(db, user, payload)


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return patient_service.get_patient_or_404(db, user, patient_id)


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return patient_service.update_patient(db, user, patient_id, payload)


@router.delete("/{patient_id}", response_model=PatientResponse)
def delete_patient(
    patient_id: uuid.UUID,
    reason: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 10.3 — soft delete apenas; nunca exclusao fisica imediata."""
    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete patients")
    return patient_service.soft_delete_patient(db, user, patient_id, reason)


@router.post("/{patient_id}/restore", response_model=PatientResponse)
def restore_patient(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 16.2/17.1 — restaurar paciente repoe sessoes, planos e indicadores (AC-11);
    Configurável para supervisor."""
    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL) and not rbac_service.can_restore_deleted_data(
        db, user
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to restore patients")
    return patient_service.restore_patient(db, user, patient_id)


@router.get("/deleted/list", response_model=list[PatientResponse])
def list_deleted_patients(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 16.2/17.1 — administradores podem ver; supervisor Configurável; demais não acessam a aba."""
    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL) and not rbac_service.can_restore_deleted_data(
        db, user
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return patient_service.list_deleted_patients(db, user)


@router.post("/import/preview", response_model=PatientImportPreviewResponse)
async def preview_patient_import(
    file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Seção 32.7 — pré-visualização do CSV antes de confirmar a importação."""
    if not rbac_service.can_create_patient(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to import patients")
    return await csv_import_service.preview_import(file)


@router.post("/import/commit", response_model=PatientImportCommitResponse)
async def commit_patient_import(
    file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Seção 32.7 — importa em lote e retorna relatório de linhas importadas versus rejeitadas."""
    if not rbac_service.can_create_patient(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to import patients")
    return await csv_import_service.commit_import_from_file(db, user, file)


@router.post(
    "/{patient_id}/assignments",
    response_model=PatientAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_professional(
    patient_id: uuid.UUID,
    payload: PatientAssignmentCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 7.3 — a clinica pode atribuir um paciente a um ou varios profissionais."""
    if user.user_type != UserType.CLINIC_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only clinic admins can assign patients")
    return patient_service.assign_professional(db, user, patient_id, payload)


@router.delete("/{patient_id}/assignments/{professional_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_assignment(
    patient_id: uuid.UUID,
    professional_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.user_type != UserType.CLINIC_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only clinic admins can manage assignments")
    patient_service.remove_assignment(db, user, patient_id, professional_id)
