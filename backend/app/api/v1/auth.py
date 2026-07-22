from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangeNameRequest,
    ChangePasswordRequest,
    ClinicRegisterRequest,
    IndividualRegisterRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.two_factor import (
    TwoFactorDisableRequest,
    TwoFactorEnableRequest,
    TwoFactorSetupResponse,
    TwoFactorStatusResponse,
    TwoFactorVerifyLoginRequest,
)
from app.services import auth_service, two_factor_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/clinic", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_clinic(payload: ClinicRegisterRequest, db: Session = Depends(get_db)) -> User:
    return auth_service.register_clinic(db, payload)


@router.post("/register/individual", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_individual(payload: IndividualRegisterRequest, db: Session = Depends(get_db)) -> User:
    return auth_service.register_individual(db, payload)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = auth_service.authenticate(db, payload)
    if user.is_2fa_enabled:
        two_factor_token = auth_service.issue_two_factor_challenge(user)
        return LoginResponse(requires_2fa=True, two_factor_token=two_factor_token)

    access, refresh = auth_service.issue_tokens(user)
    return LoginResponse(
        access_token=access,
        refresh_token=refresh,
        requires_2fa_setup=two_factor_service.requires_2fa_setup(user),
    )


@router.post("/2fa/verify-login", response_model=LoginResponse)
def verify_two_factor_login(payload: TwoFactorVerifyLoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Seção 32.8 — segunda etapa do login quando o usuário tem 2FA habilitado."""
    user = auth_service.resolve_two_factor_challenge(db, payload.two_factor_token)
    two_factor_service.verify_login_code(db, user, payload.code)
    access, refresh = auth_service.issue_tokens(user)
    return LoginResponse(access_token=access, refresh_token=refresh)


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def setup_two_factor(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> TwoFactorSetupResponse:
    return two_factor_service.start_setup(db, user)


@router.post("/2fa/enable", status_code=status.HTTP_204_NO_CONTENT)
def enable_two_factor(
    payload: TwoFactorEnableRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    two_factor_service.enable(db, user, payload.code)


@router.post("/2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
def disable_two_factor(
    payload: TwoFactorDisableRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    two_factor_service.disable(db, user, payload.password)


@router.get("/2fa/status", response_model=TwoFactorStatusResponse)
def two_factor_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> TwoFactorStatusResponse:
    return TwoFactorStatusResponse(
        is_2fa_enabled=user.is_2fa_enabled,
        required=two_factor_service.requires_2fa_setup(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    access, refresh_token = auth_service.refresh_access_token(db, payload.refresh_token)
    return TokenResponse(access_token=access, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/change-password", response_model=TokenResponse)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TokenResponse:
    access, refresh_token = auth_service.change_password(db, user, payload)
    return TokenResponse(access_token=access, refresh_token=refresh_token)


@router.patch("/change-name", response_model=UserResponse)
def change_name(
    payload: ChangeNameRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    return auth_service.change_name(db, user, payload)
