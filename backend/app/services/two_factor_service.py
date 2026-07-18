import pyotp
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.enums import SubscriptionPlan, UserType
from app.models.user import User
from app.services import audit_service

ISSUER_NAME = "Behavior Hub"


def requires_2fa_setup(user: User) -> bool:
    """Seção 32.8 — obrigatório para administradores de clínica no plano Enterprise;
    opcional para os demais perfis."""
    if user.user_type != UserType.CLINIC_ADMIN or user.clinic_id is None:
        return False
    if user.is_2fa_enabled:
        return False
    clinic = user.clinic
    return clinic is not None and clinic.subscription_plan == SubscriptionPlan.ENTERPRISE


def start_setup(db: Session, user: User) -> dict:
    """Gera um novo segredo TOTP (ainda não confirmado — is_2fa_enabled só vira
    True em /2fa/enable, após o usuário provar posse do segredo com um código válido)."""
    secret = pyotp.random_base32()
    user.totp_secret = secret
    db.commit()

    otpauth_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=ISSUER_NAME)
    return {"secret": secret, "otpauth_uri": otpauth_uri}


def _verify_code(secret: str, code: str) -> bool:
    return pyotp.totp.TOTP(secret).verify(code, valid_window=1)


def enable(db: Session, user: User, code: str) -> None:
    if not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start 2FA setup first")
    if not _verify_code(user.totp_secret, code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication code")

    user.is_2fa_enabled = True
    audit_service.record(db, actor_user_id=user.id, action="two_factor_enabled", entity_type="user", entity_id=user.id)
    db.commit()


def disable(db: Session, user: User, password: str) -> None:
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    user.is_2fa_enabled = False
    user.totp_secret = None
    audit_service.record(db, actor_user_id=user.id, action="two_factor_disabled", entity_type="user", entity_id=user.id)
    db.commit()


def verify_login_code(db: Session, user: User, code: str) -> None:
    if not user.totp_secret or not _verify_code(user.totp_secret, code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication code")
