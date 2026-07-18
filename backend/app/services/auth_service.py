import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    TokenType,
    create_token,
    decode_token,
    generate_invitation_token,
    hash_password,
    verify_invitation_token,
    verify_password,
)
from app.models.clinic import Clinic
from app.models.enums import InvitationStatus, UserStatus, UserType
from app.models.invitation import Invitation
from app.models.user import User
from app.schemas.auth import (
    ClinicRegisterRequest,
    IndividualRegisterRequest,
    LoginRequest,
)
from app.schemas.invitation import InvitationAcceptRequest, InvitationCreateRequest
from app.services import audit_service

INVITATION_EXPIRATION_DAYS = 7


def _ensure_email_available(db: Session, email: str) -> None:
    existing = db.query(User).filter(User.email == email.lower()).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )


def register_clinic(db: Session, payload: ClinicRegisterRequest) -> User:
    """Seção 6.2 — Cadastro de clínica: cria organização e usuário administrador.
    Seção 6.1 — a conta nova inicia vazia: nenhuma outra entidade e criada aqui."""
    if not payload.accept_terms:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Terms must be accepted")

    _ensure_email_available(db, payload.email)

    clinic = Clinic(name=payload.clinic_name)
    db.add(clinic)
    db.flush()

    admin = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        name=payload.admin_name,
        user_type=UserType.CLINIC_ADMIN,
        status=UserStatus.ACTIVE,
        clinic_id=clinic.id,
        terms_accepted_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(admin)
    db.flush()

    clinic.owner_user_id = admin.id
    audit_service.record(
        db,
        actor_user_id=admin.id,
        action="clinic_registered",
        entity_type="clinic",
        entity_id=clinic.id,
        after={"name": clinic.name},
    )
    db.commit()
    db.refresh(admin)
    return admin


def register_individual(db: Session, payload: IndividualRegisterRequest) -> User:
    """Seção 6.2 — Cadastro profissional individual: cria um tenant individual sem clinic_id."""
    if not payload.accept_terms:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Terms must be accepted")

    _ensure_email_available(db, payload.email)

    from app.models.enums import SubscriptionPlan

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        name=payload.name,
        user_type=UserType.INDIVIDUAL,
        specialty=payload.specialty,
        status=UserStatus.ACTIVE,
        clinic_id=None,
        subscription_plan=SubscriptionPlan.FREE,
        terms_accepted_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(user)
    db.flush()
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="individual_registered",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, payload: LoginRequest) -> User:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    # Constant-shape response to avoid user enumeration (Seção 6.3).
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user


def issue_tokens(user: User) -> tuple[str, str]:
    access = create_token(str(user.id), TokenType.ACCESS)
    refresh = create_token(str(user.id), TokenType.REFRESH)
    return access, refresh


def refresh_access_token(db: Session, refresh_token: str) -> tuple[str, str]:
    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    if payload.get("type") != TokenType.REFRESH.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    return issue_tokens(user)


def create_invitation(db: Session, clinic_admin: User, payload: InvitationCreateRequest) -> tuple[Invitation, str]:
    """Seção 7.1 — gerar link unico com token criptograficamente seguro, expiracao padrao 7 dias."""
    raw_token, token_hash = generate_invitation_token()
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        days=INVITATION_EXPIRATION_DAYS
    )
    invitation = Invitation(
        clinic_id=clinic_admin.clinic_id,
        email=payload.email.lower(),
        specialty=payload.specialty,
        token_hash=token_hash,
        expires_at=expires_at,
        created_by_user_id=clinic_admin.id,
    )
    db.add(invitation)
    db.flush()
    audit_service.record(
        db,
        actor_user_id=clinic_admin.id,
        action="invitation_created",
        entity_type="invitation",
        entity_id=invitation.id,
        after={"email": invitation.email},
    )
    db.commit()
    db.refresh(invitation)
    return invitation, raw_token


def _find_invitation_by_token(db: Session, raw_token: str) -> Invitation:
    now = datetime.datetime.now(datetime.timezone.utc)
    candidates = (
        db.query(Invitation).filter(Invitation.status == InvitationStatus.PENDING).all()
    )
    for candidate in candidates:
        if verify_invitation_token(raw_token, candidate.token_hash):
            if candidate.expires_at < now:
                candidate.status = InvitationStatus.EXPIRED
                db.commit()
                raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation expired")
            return candidate
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")


def revoke_invitation(db: Session, clinic_admin: User, invitation_id: uuid.UUID) -> Invitation:
    invitation = db.get(Invitation, invitation_id)
    if invitation is None or invitation.clinic_id != clinic_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation cannot be revoked")
    invitation.status = InvitationStatus.REVOKED
    invitation.revoked_at = datetime.datetime.now(datetime.timezone.utc)
    audit_service.record(
        db,
        actor_user_id=clinic_admin.id,
        action="invitation_revoked",
        entity_type="invitation",
        entity_id=invitation.id,
    )
    db.commit()
    db.refresh(invitation)
    return invitation


def accept_invitation(db: Session, raw_token: str, payload: InvitationAcceptRequest) -> User:
    """Seção 7.1 — vincular automaticamente o novo usuario a clinica que gerou o convite.
    Regra AC-09: profissional convidado entra vinculado e nunca ve ProfessionalRegistration."""
    if not payload.accept_terms:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Terms must be accepted")

    invitation = _find_invitation_by_token(db, raw_token)
    _ensure_email_available(db, invitation.email)

    user = User(
        email=invitation.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        user_type=UserType.PROFESSIONAL,
        specialty=invitation.specialty,
        status=UserStatus.ACTIVE,
        clinic_id=invitation.clinic_id,
        terms_accepted_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(user)
    db.flush()

    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_at = datetime.datetime.now(datetime.timezone.utc)
    invitation.accepted_by_user_id = user.id

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="invitation_accepted",
        entity_type="invitation",
        entity_id=invitation.id,
    )
    db.commit()
    db.refresh(user)
    return user
