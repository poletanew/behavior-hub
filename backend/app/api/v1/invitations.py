import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_clinic_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse, UserResponse
from app.schemas.invitation import (
    InvitationAcceptRequest,
    InvitationCreatedResponse,
    InvitationCreateRequest,
    InvitationResponse,
)
from app.services import auth_service

router = APIRouter(tags=["invitations"])


@router.post(
    "/invitations",
    response_model=InvitationCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invitation(
    payload: InvitationCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 7.1/17.1 — Sim para admin de clínica; Configurável para supervisor."""
    invitation, raw_token = auth_service.create_invitation(db, user, payload)
    return InvitationCreatedResponse(
        id=invitation.id,
        email=invitation.email,
        specialty=invitation.specialty,
        role=invitation.role,
        status=invitation.status,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        raw_token=raw_token,
    )


@router.get("/invitations", response_model=list[InvitationResponse])
def list_invitations(
    db: Session = Depends(get_db),
    clinic_admin: User = Depends(require_clinic_admin),
):
    from app.models.invitation import Invitation

    return (
        db.query(Invitation)
        .filter(Invitation.clinic_id == clinic_admin.clinic_id)
        .order_by(Invitation.created_at.desc())
        .all()
    )


@router.post("/invitations/{invitation_id}/revoke", response_model=InvitationResponse)
def revoke_invitation(
    invitation_id: uuid.UUID,
    db: Session = Depends(get_db),
    clinic_admin: User = Depends(require_clinic_admin),
):
    return auth_service.revoke_invitation(db, clinic_admin, invitation_id)


@router.post("/invitations/{token}/accept", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def accept_invitation(token: str, payload: InvitationAcceptRequest, db: Session = Depends(get_db)):
    """Seção 7.1 / AC-09 — o profissional entra vinculado a clinica que gerou o convite."""
    return auth_service.accept_invitation(db, token, payload)
