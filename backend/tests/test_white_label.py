from app.models.clinic import Clinic
from app.models.enums import SubscriptionPlan, SubscriptionStatus
from tests.conftest import create_patient, invite_and_accept_professional, register_clinic, register_individual


def _make_enterprise(db_session, clinic_id, *, active=True):
    clinic = db_session.query(Clinic).filter(Clinic.id == clinic_id).first()
    clinic.subscription_plan = SubscriptionPlan.ENTERPRISE
    clinic.subscription_status = SubscriptionStatus.ACTIVE if active else SubscriptionStatus.CANCELED
    db_session.commit()
    return clinic


def test_get_settings_defaults_to_disabled(client):
    ctx = register_clinic(client)
    response = client.get("/v1/clinic/white-label", headers=ctx["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body == {"enabled": False, "logo_url": None, "brand_color": None, "display_name": None}


def test_update_rejected_on_non_enterprise_plan(client):
    ctx = register_clinic(client)
    response = client.patch(
        "/v1/clinic/white-label", json={"display_name": "Clinica X"}, headers=ctx["headers"]
    )
    assert response.status_code == 403


def test_update_rejected_when_enterprise_but_not_active(client, db_session):
    ctx = register_clinic(client)
    _make_enterprise(db_session, ctx["user"]["clinic_id"], active=False)

    response = client.patch(
        "/v1/clinic/white-label", json={"display_name": "Clinica X"}, headers=ctx["headers"]
    )
    assert response.status_code == 403


def test_update_succeeds_on_active_enterprise_plan(client, db_session):
    ctx = register_clinic(client)
    _make_enterprise(db_session, ctx["user"]["clinic_id"])

    response = client.patch(
        "/v1/clinic/white-label",
        json={"display_name": "Clinica Exemplo", "brand_color": "#112233", "logo_url": "https://example.com/logo.png"},
        headers=ctx["headers"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["enabled"] is True
    assert body["display_name"] == "Clinica Exemplo"
    assert body["brand_color"] == "#112233"

    fetched = client.get("/v1/clinic/white-label", headers=ctx["headers"]).json()
    assert fetched == body


def test_invalid_hex_color_rejected(client, db_session):
    ctx = register_clinic(client)
    _make_enterprise(db_session, ctx["user"]["clinic_id"])

    response = client.patch(
        "/v1/clinic/white-label", json={"brand_color": "not-a-color"}, headers=ctx["headers"]
    )
    assert response.status_code == 422


def test_only_clinic_admin_can_manage_white_label(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    response = client.get("/v1/clinic/white-label", headers=professional["headers"])
    assert response.status_code == 403


def test_individual_tenant_cannot_use_white_label(client):
    individual = register_individual(client)
    response = client.get("/v1/clinic/white-label", headers=individual["headers"])
    assert response.status_code == 403


def test_family_portal_branding_reflects_enterprise_status(client, db_session):
    from tests.conftest import invite_and_accept

    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    family = invite_and_accept(client, ctx["headers"], role="family", patient_id=patient["id"])

    default_branding = client.get(
        f"/v1/family-portal/patients/{patient['id']}/branding", headers=family["headers"]
    )
    assert default_branding.status_code == 200
    assert default_branding.json()["enabled"] is False

    _make_enterprise(db_session, ctx["user"]["clinic_id"])
    client.patch(
        "/v1/clinic/white-label",
        json={"display_name": "Clinica Exemplo", "brand_color": "#654321"},
        headers=ctx["headers"],
    )

    enabled_branding = client.get(
        f"/v1/family-portal/patients/{patient['id']}/branding", headers=family["headers"]
    ).json()
    assert enabled_branding["enabled"] is True
    assert enabled_branding["display_name"] == "Clinica Exemplo"


def test_white_label_settings_tenant_isolation(client, db_session):
    clinic_a = register_clinic(client, "Clinica White A")
    clinic_b = register_clinic(client, "Clinica White B")
    _make_enterprise(db_session, clinic_a["user"]["clinic_id"])
    client.patch(
        "/v1/clinic/white-label", json={"display_name": "Marca A"}, headers=clinic_a["headers"]
    )

    settings_b = client.get("/v1/clinic/white-label", headers=clinic_b["headers"]).json()
    assert settings_b["display_name"] is None
    assert settings_b["enabled"] is False
