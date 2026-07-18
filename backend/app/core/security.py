import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    TWO_FACTOR = "two_factor"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_token(subject: str, token_type: TokenType, extra_claims: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    if token_type == TokenType.ACCESS:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    elif token_type == TokenType.TWO_FACTOR:
        expire = now + timedelta(minutes=5)
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": subject,
        "type": token_type.value,
        "iat": now,
        "exp": expire,
        "jti": secrets.token_hex(16),
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


def generate_invitation_token() -> tuple[str, str]:
    """Returns (raw_token, token_hash). Only the hash is stored, per PRD 7.1."""
    raw_token = secrets.token_urlsafe(32)
    return raw_token, hash_password(raw_token)


def verify_invitation_token(raw_token: str, token_hash: str) -> bool:
    return verify_password(raw_token, token_hash)
