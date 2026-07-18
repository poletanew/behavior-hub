import pyotp

from app.models.clinic import Clinic
from app.models.enums import SubscriptionPlan
from tests.conftest import register_clinic, register_individual


def _totp_code(secret: str) -> str:
    return pyotp.TOTP(secret).now()


def test_setup_returns_secret_and_otpauth_uri(client):
    ctx = register_clinic(client)
    response = client.post("/v1/auth/2fa/setup", headers=ctx["headers"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["secret"]) >= 16
    assert body["otpauth_uri"].startswith("otpauth://totp/")
    assert ctx["user"]["email"] in body["otpauth_uri"] or "Behavior%20Hub" in body["otpauth_uri"]


def test_enable_requires_valid_code(client):
    ctx = register_clinic(client)
    client.post("/v1/auth/2fa/setup", headers=ctx["headers"])

    response = client.post("/v1/auth/2fa/enable", json={"code": "000000"}, headers=ctx["headers"])
    assert response.status_code == 401

    status_response = client.get("/v1/auth/2fa/status", headers=ctx["headers"])
    assert status_response.json()["is_2fa_enabled"] is False


def test_enable_cannot_happen_without_setup(client):
    ctx = register_clinic(client)
    response = client.post("/v1/auth/2fa/enable", json={"code": "123456"}, headers=ctx["headers"])
    assert response.status_code == 400


def test_full_enable_and_login_challenge_flow(client):
    ctx = register_clinic(client)
    setup = client.post("/v1/auth/2fa/setup", headers=ctx["headers"]).json()
    secret = setup["secret"]

    enable_response = client.post(
        "/v1/auth/2fa/enable", json={"code": _totp_code(secret)}, headers=ctx["headers"]
    )
    assert enable_response.status_code == 204

    status_response = client.get("/v1/auth/2fa/status", headers=ctx["headers"])
    assert status_response.json()["is_2fa_enabled"] is True

    login_response = client.post(
        "/v1/auth/login", json={"email": ctx["email"], "password": "senha-super-segura-123"}
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["requires_2fa"] is True
    assert login_body["access_token"] is None
    two_factor_token = login_body["two_factor_token"]
    assert two_factor_token

    wrong_code = client.post(
        "/v1/auth/2fa/verify-login", json={"two_factor_token": two_factor_token, "code": "000000"}
    )
    assert wrong_code.status_code == 401

    correct = client.post(
        "/v1/auth/2fa/verify-login", json={"two_factor_token": two_factor_token, "code": _totp_code(secret)}
    )
    assert correct.status_code == 200
    assert correct.json()["access_token"] is not None


def test_login_without_2fa_returns_tokens_directly(client):
    ctx = register_clinic(client)
    login_response = client.post(
        "/v1/auth/login", json={"email": ctx["email"], "password": "senha-super-segura-123"}
    )
    body = login_response.json()
    assert body["requires_2fa"] is False
    assert body["access_token"] is not None


def test_disable_requires_correct_password(client):
    ctx = register_clinic(client)
    setup = client.post("/v1/auth/2fa/setup", headers=ctx["headers"]).json()
    client.post("/v1/auth/2fa/enable", json={"code": _totp_code(setup["secret"])}, headers=ctx["headers"])

    wrong_password = client.post("/v1/auth/2fa/disable", json={"password": "senha-errada"}, headers=ctx["headers"])
    assert wrong_password.status_code == 401

    correct = client.post(
        "/v1/auth/2fa/disable", json={"password": "senha-super-segura-123"}, headers=ctx["headers"]
    )
    assert correct.status_code == 204

    login_response = client.post(
        "/v1/auth/login", json={"email": ctx["email"], "password": "senha-super-segura-123"}
    )
    assert login_response.json()["requires_2fa"] is False


def test_enterprise_clinic_admin_flagged_as_requiring_2fa(client, db_session):
    ctx = register_clinic(client)
    clinic = db_session.query(Clinic).filter(Clinic.id == ctx["user"]["clinic_id"]).first()
    clinic.subscription_plan = SubscriptionPlan.ENTERPRISE
    db_session.commit()

    status_response = client.get("/v1/auth/2fa/status", headers=ctx["headers"])
    assert status_response.json()["required"] is True

    login_response = client.post(
        "/v1/auth/login", json={"email": ctx["email"], "password": "senha-super-segura-123"}
    )
    assert login_response.json()["requires_2fa_setup"] is True


def test_non_enterprise_admin_not_required(client):
    ctx = register_clinic(client)
    status_response = client.get("/v1/auth/2fa/status", headers=ctx["headers"])
    assert status_response.json()["required"] is False


def test_individual_account_never_required_regardless_of_plan(client):
    ctx = register_individual(client)
    status_response = client.get("/v1/auth/2fa/status", headers=ctx["headers"])
    assert status_response.json()["required"] is False
