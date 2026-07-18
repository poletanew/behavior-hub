import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Specialty, SubscriptionPlan, UserStatus, UserType


class ClinicRegisterRequest(BaseModel):
    clinic_name: str = Field(min_length=2, max_length=255)
    admin_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    accept_terms: bool

    def validate_terms(self) -> None:
        if not self.accept_terms:
            raise ValueError("accept_terms must be true")


class IndividualRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    specialty: Specialty | None = None
    accept_terms: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    user_type: UserType
    specialty: Specialty | None
    status: UserStatus
    clinic_id: uuid.UUID | None
    subscription_plan: SubscriptionPlan | None

    class Config:
        from_attributes = True
