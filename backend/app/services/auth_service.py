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
    ChangeNameRequest,
    ChangePasswordRequest,
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
    # Seção 17.2 — "ver" (token_version) embutido no JWT para permitir revogação
    # imediata (ex.: Family Portal) sem precisar de uma tabela de sessões.
    extra_claims = {"ver": user.token_version}
    access = create_token(str(user.id), TokenType.ACCESS, extra_claims=extra_claims)
    refresh = create_token(str(user.id), TokenType.REFRESH, extra_claims=extra_claims)
    return access, refresh


def issue_two_factor_challenge(user: User) -> str:
    """Seção 32.8 — token de curta duração (5 min) usado apenas para provar que a
    senha já foi validada, trocado por tokens reais em /auth/2fa/verify-login."""
    return create_token(str(user.id), TokenType.TWO_FACTOR)


def resolve_two_factor_challenge(db: Session, two_factor_token: str) -> User:
    try:
        payload = decode_token(two_factor_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired code") from exc

    if payload.get("type") != TokenType.TWO_FACTOR.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or user.status != UserStatus.ACTIVE or not user.is_2fa_enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired code")
    return user


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
    if payload.get("ver") != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    return issue_tokens(user)


def change_password(db: Session, user: User, payload: ChangePasswordRequest) -> tuple[str, str]:
    """Addendum v2.1, RF-15 — autoatendimento de troca de senha: "trocar a senha
    deve encerrar as demais sessões ativas do usuário". Reaproveita o mecanismo
    de token_version (Seção 17.2) para invalidar todos os tokens já emitidos, e
    devolve um par de tokens novo já válido para que a sessão que fez a troca
    continue funcionando sem precisar logar de novo."""
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password")

    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="password_changed",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return issue_tokens(user)


def change_name(db: Session, user: User, payload: ChangeNameRequest) -> User:
    """Addendum v2.1, RF-15 — autoatendimento de troca do nome de usuário. Não há
    um campo de "username" de login separado (o login é feito por email), então
    "nome de usuário" aqui é o nome de exibição (User.name)."""
    before_name = user.name
    user.name = payload.name
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="user_name_updated",
        entity_type="user",
        entity_id=user.id,
        before={"name": before_name},
        after={"name": user.name},
    )
    db.commit()
    db.refresh(user)
    return user


def create_invitation(db: Session, inviter: User, payload: InvitationCreateRequest) -> tuple[Invitation, str]:
    """Seção 7.1 — gerar link unico com token criptograficamente seguro, expiracao padrao 7 dias.
    Seção 17.1 — "Gerar convite" é Sim para admin e Configurável para supervisor.
    Seção 29.6 — convite de responsável (FAMILY) usa um gate diferente: em vez do
    RBAC de convite de equipe, exige que o convidante já tenha acesso ao paciente
    (mesmo gate de app.services.patient_service, que isola tenant e atribuição)."""
    from app.schemas.invitation import INVITABLE_ROLES
    from app.services import rbac_service

    if payload.role not in INVITABLE_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role for invitation")

    patient_id = None
    if payload.role == UserType.FAMILY:
        from app.services import patient_service

        patient = patient_service.get_patient_or_404(db, inviter, payload.patient_id)
        patient_id = patient.id
    elif not rbac_service.can_generate_invitation(db, inviter):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to generate invitations")

    raw_token, token_hash = generate_invitation_token()
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        days=INVITATION_EXPIRATION_DAYS
    )
    invitation = Invitation(
        clinic_id=inviter.clinic_id,
        email=payload.email.lower(),
        specialty=payload.specialty,
        role=payload.role,
        patient_id=patient_id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_by_user_id=inviter.id,
    )
    db.add(invitation)
    db.flush()
    audit_service.record(
        db,
        actor_user_id=inviter.id,
        action="invitation_created",
        entity_type="invitation",
        entity_id=invitation.id,
        after={"email": invitation.email, "role": invitation.role.value},
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

    now = datetime.datetime.now(datetime.timezone.utc)
    user = User(
        email=invitation.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        user_type=invitation.role,
        specialty=invitation.specialty,
        status=UserStatus.ACTIVE,
        clinic_id=invitation.clinic_id,
        terms_accepted_at=now,
        supervisor_id=invitation.created_by_user_id if invitation.role == UserType.AT else None,
    )
    db.add(user)
    db.flush()

    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_at = now
    invitation.accepted_by_user_id = user.id

    if invitation.role == UserType.FAMILY:
        # Seção 17.2 — o aceite do convite (accept_terms=True) É o registro do
        # consentimento explícito do responsável; o acesso nasce com todas as
        # flags de whitelist em False (nada liberado por padrão).
        from app.models.family_access import FamilyAccess

        db.add(
            FamilyAccess(
                patient_id=invitation.patient_id,
                family_user_id=user.id,
                granted_by_user_id=invitation.created_by_user_id,
                consent_given_at=now,
            )
        )

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
