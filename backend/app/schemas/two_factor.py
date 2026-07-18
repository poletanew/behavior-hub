from pydantic import BaseModel


class TwoFactorSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class TwoFactorEnableRequest(BaseModel):
    code: str


class TwoFactorDisableRequest(BaseModel):
    password: str


class TwoFactorVerifyLoginRequest(BaseModel):
    two_factor_token: str
    code: str


class TwoFactorStatusResponse(BaseModel):
    is_2fa_enabled: bool
    required: bool
