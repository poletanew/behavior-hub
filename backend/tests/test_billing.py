import uuid
from unittest.mock import MagicMock, patch

from app.models.clinic import Clinic
from app.services import billing_service
from tests.conftest import invite_and_accept_professional, register_clinic, register_individual


def test_billing_status_defaults_to_free_and_unconfigured(client):
    ctx = register_clinic(client)
    response = client.get("/v1/billing/status", headers=ctx["headers"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["subscription_plan"] == "free"
    assert body["subscription_status"] == "none"
    assert body["has_paid_access"] is False
    assert body["stripe_configured"] is False


def test_checkout_fails_gracefully_when_stripe_not_configured(client):
    ctx = register_clinic(client)
    response = client.post("/v1/stripe/checkout", json={"plan": "basic"}, headers=ctx["headers"])
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_checkout_requires_billing_owner(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])
    response = client.post("/v1/stripe/checkout", json={"plan": "basic"}, headers=professional["headers"])
    assert response.status_code == 403


def test_checkout_creates_session_when_configured(client, monkeypatch):
    ctx = register_clinic(client)
    monkeypatch.setattr(billing_service.settings, "STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setattr(billing_service.settings, "STRIPE_PRICE_ID_BASIC", "price_basic_123")

    fake_customer = MagicMock(id="cus_123")
    fake_session = MagicMock(url="https://checkout.stripe.com/pay/cs_test_123")

    with patch.object(billing_service.stripe.Customer, "create", return_value=fake_customer) as mock_customer, patch.object(
        billing_service.stripe.checkout.Session, "create", return_value=fake_session
    ) as mock_checkout:
        response = client.post("/v1/stripe/checkout", json={"plan": "basic"}, headers=ctx["headers"])

    assert response.status_code == 200, response.text
    assert response.json()["checkout_url"] == fake_session.url
    mock_customer.assert_called_once()
    mock_checkout.assert_called_once()
    assert mock_checkout.call_args.kwargs["line_items"][0]["price"] == "price_basic_123"


def test_checkout_fails_when_price_not_configured_for_plan(client, monkeypatch):
    ctx = register_clinic(client)
    monkeypatch.setattr(billing_service.settings, "STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setattr(billing_service.settings, "STRIPE_PRICE_ID_ENTERPRISE", None)

    response = client.post("/v1/stripe/checkout", json={"plan": "enterprise"}, headers=ctx["headers"])
    assert response.status_code == 503


def test_portal_requires_existing_customer(client, monkeypatch):
    ctx = register_clinic(client)
    monkeypatch.setattr(billing_service.settings, "STRIPE_SECRET_KEY", "sk_test_dummy")

    response = client.post("/v1/stripe/portal", headers=ctx["headers"])
    assert response.status_code == 400


def test_portal_creates_session_when_customer_exists(client, monkeypatch, db_session):
    ctx = register_clinic(client)
    monkeypatch.setattr(billing_service.settings, "STRIPE_SECRET_KEY", "sk_test_dummy")

    clinic = db_session.query(Clinic).filter(Clinic.id == ctx["user"]["clinic_id"]).first()
    clinic.stripe_customer_id = "cus_existing"
    db_session.commit()

    fake_portal = MagicMock(url="https://billing.stripe.com/session/xyz")
    with patch.object(billing_service.stripe.billing_portal.Session, "create", return_value=fake_portal) as mock_portal:
        response = client.post("/v1/stripe/portal", headers=ctx["headers"])

    assert response.status_code == 200, response.text
    assert response.json()["portal_url"] == fake_portal.url
    mock_portal.assert_called_once_with(customer="cus_existing", return_url=f"{billing_service.settings.FRONTEND_URL}/plans")


def _fake_event(event_id: str, event_type: str, data_object: dict) -> dict:
    return {"id": event_id, "type": event_type, "data": {"object": data_object}}


def test_webhook_rejects_invalid_signature(client, monkeypatch):
    monkeypatch.setattr(billing_service.settings, "STRIPE_WEBHOOK_SECRET", "whsec_dummy")

    with patch.object(
        billing_service.stripe.Webhook, "construct_event", side_effect=ValueError("bad payload")
    ):
        response = client.post(
            "/v1/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t=1,v1=bad"}
        )
    assert response.status_code == 400


def test_webhook_missing_secret_configured_returns_503(client):
    response = client.post("/v1/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})
    assert response.status_code == 503


def test_webhook_checkout_completed_updates_entitlements(client, monkeypatch, db_session):
    ctx = register_clinic(client)
    monkeypatch.setattr(billing_service.settings, "STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    monkeypatch.setattr(billing_service.settings, "STRIPE_PRICE_ID_PREMIUM", "price_premium_123")

    clinic = db_session.query(Clinic).filter(Clinic.id == ctx["user"]["clinic_id"]).first()
    clinic.stripe_customer_id = "cus_abc"
    db_session.commit()

    event = _fake_event(
        f"evt_{uuid.uuid4().hex}",
        "checkout.session.completed",
        {"customer": "cus_abc", "subscription": "sub_123"},
    )
    fake_subscription = {
        "id": "sub_123",
        "status": "active",
        "current_period_end": 1893456000,
        "items": {"data": [{"price": {"id": "price_premium_123"}}]},
    }

    with patch.object(billing_service.stripe.Webhook, "construct_event", return_value=event), patch.object(
        billing_service.stripe.Subscription, "retrieve", return_value=fake_subscription
    ):
        response = client.post(
            "/v1/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t=1,v1=x"}
        )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "processed"

    db_session.refresh(clinic)
    assert clinic.subscription_plan.value == "premium"
    assert clinic.subscription_status.value == "active"
    assert clinic.stripe_subscription_id == "sub_123"


def test_webhook_duplicate_event_is_ignored(client, monkeypatch, db_session):
    ctx = register_clinic(client)
    monkeypatch.setattr(billing_service.settings, "STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    monkeypatch.setattr(billing_service.settings, "STRIPE_PRICE_ID_PREMIUM", "price_premium_123")

    clinic = db_session.query(Clinic).filter(Clinic.id == ctx["user"]["clinic_id"]).first()
    clinic.stripe_customer_id = "cus_dup"
    db_session.commit()

    event_id = f"evt_{uuid.uuid4().hex}"
    event = _fake_event(event_id, "checkout.session.completed", {"customer": "cus_dup", "subscription": "sub_dup"})
    fake_subscription = {
        "id": "sub_dup",
        "status": "active",
        "current_period_end": 1893456000,
        "items": {"data": [{"price": {"id": "price_premium_123"}}]},
    }

    with patch.object(billing_service.stripe.Webhook, "construct_event", return_value=event), patch.object(
        billing_service.stripe.Subscription, "retrieve", return_value=fake_subscription
    ) as mock_retrieve:
        first = client.post("/v1/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})
        second = client.post("/v1/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})

    assert first.json()["status"] == "processed"
    assert second.json()["status"] == "duplicate_ignored"
    mock_retrieve.assert_called_once()


def test_webhook_subscription_deleted_reverts_to_free(client, monkeypatch, db_session):
    ctx = register_clinic(client)
    monkeypatch.setattr(billing_service.settings, "STRIPE_WEBHOOK_SECRET", "whsec_dummy")

    clinic = db_session.query(Clinic).filter(Clinic.id == ctx["user"]["clinic_id"]).first()
    clinic.stripe_customer_id = "cus_cancel"
    from app.models.enums import SubscriptionPlan, SubscriptionStatus

    clinic.subscription_plan = SubscriptionPlan.PREMIUM
    clinic.subscription_status = SubscriptionStatus.ACTIVE
    clinic.stripe_subscription_id = "sub_cancel"
    db_session.commit()

    event = _fake_event(
        f"evt_{uuid.uuid4().hex}", "customer.subscription.deleted", {"customer": "cus_cancel", "id": "sub_cancel"}
    )
    with patch.object(billing_service.stripe.Webhook, "construct_event", return_value=event):
        response = client.post("/v1/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})

    assert response.status_code == 200
    db_session.refresh(clinic)
    assert clinic.subscription_plan.value == "free"
    assert clinic.subscription_status.value == "canceled"
    assert clinic.stripe_subscription_id is None


def test_webhook_invoice_payment_failed_marks_past_due(client, monkeypatch, db_session):
    ctx = register_clinic(client)
    monkeypatch.setattr(billing_service.settings, "STRIPE_WEBHOOK_SECRET", "whsec_dummy")

    clinic = db_session.query(Clinic).filter(Clinic.id == ctx["user"]["clinic_id"]).first()
    clinic.stripe_customer_id = "cus_fail"
    from app.models.enums import SubscriptionStatus

    clinic.subscription_status = SubscriptionStatus.ACTIVE
    db_session.commit()

    event = _fake_event(f"evt_{uuid.uuid4().hex}", "invoice.payment_failed", {"customer": "cus_fail"})
    with patch.object(billing_service.stripe.Webhook, "construct_event", return_value=event):
        response = client.post("/v1/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})

    assert response.status_code == 200
    db_session.refresh(clinic)
    assert clinic.subscription_status.value == "past_due"


def test_plan_gating_falls_back_to_free_when_subscription_not_active(client, db_session):
    from app.models.enums import SubscriptionPlan, SubscriptionStatus
    from app.services.plan_service import current_plan

    ctx = register_clinic(client)
    clinic = db_session.query(Clinic).filter(Clinic.id == ctx["user"]["clinic_id"]).first()
    clinic.subscription_plan = SubscriptionPlan.PREMIUM
    clinic.subscription_status = SubscriptionStatus.PAST_DUE
    db_session.commit()

    admin = clinic.users[0] if clinic.users else None
    from app.models.user import User

    admin = db_session.query(User).filter(User.id == ctx["user"]["id"]).first()
    assert current_plan(admin) == "free"

    clinic.subscription_status = SubscriptionStatus.ACTIVE
    db_session.commit()
    assert current_plan(admin) == "premium"


def test_individual_billing_owner_can_checkout(client, monkeypatch):
    ctx = register_individual(client)
    monkeypatch.setattr(billing_service.settings, "STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setattr(billing_service.settings, "STRIPE_PRICE_ID_BASIC", "price_basic_123")

    fake_customer = MagicMock(id="cus_ind_123")
    fake_session = MagicMock(url="https://checkout.stripe.com/pay/cs_test_ind")

    with patch.object(billing_service.stripe.Customer, "create", return_value=fake_customer), patch.object(
        billing_service.stripe.checkout.Session, "create", return_value=fake_session
    ):
        response = client.post("/v1/stripe/checkout", json={"plan": "basic"}, headers=ctx["headers"])

    assert response.status_code == 200, response.text
