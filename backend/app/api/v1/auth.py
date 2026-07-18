from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ClinicRegisterRequest,
    IndividualRegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/clinic", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_clinic(payload: ClinicRegisterRequest, db: Session = Depends(get_db)) -> User:
    return auth_service.register_clinic(db, payload)


@router.post("/register/individual", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_individual(payload: IndividualRegisterRequest, db: Session = Depends(get_db)) -> User:
    return auth_service.register_individual(db, payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = auth_service.authenticate(db, payload)
    access, refresh = auth_service.issue_tokens(user)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    access, refresh_token = auth_service.refresh_access_token(db, payload.refresh_token)
    return TokenResponse(access_token=access, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
