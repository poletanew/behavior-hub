from app.models.clinic import Clinic
from app.models.enums import SubscriptionPlan, SubscriptionStatus
from tests.conftest import (
    create_patient,
    create_training,
    create_training_category,
    invite_and_accept_professional,
    register_clinic,
    register_individual,
)


def _make_plan(db_session, clinic_id, plan, *, active=True):
    clinic = db_session.query(Clinic).filter(Clinic.id == clinic_id).first()
    clinic.subscription_plan = plan
    clinic.subscription_status = SubscriptionStatus.ACTIVE if active else SubscriptionStatus.CANCELED
    db_session.commit()
    return clinic


def _create_session(client, headers, patient_id, professional_id, training_id):
    response = client.post(
        "/v1/sessions",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "occurred_at": "2026-07-14T10:00:00Z",
            "training_ids": [training_id],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _setup_session(client, ctx, db_session):
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = _create_session(client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id))
    return patient, session


def test_create_charge_rejected_without_premium_plan(client, db_session):
    ctx = register_clinic(client)
    patient, session = _setup_session(client, ctx, db_session)

    response = client.post(f"/v1/sessions/{session['id']}/charge", json={"amount": 150.0}, headers=ctx["headers"])
    assert response.status_code == 403


def test_create_charge_succeeds_on_premium_plan(client, db_session):
    ctx = register_clinic(client)
    _make_plan(db_session, ctx["user"]["clinic_id"], SubscriptionPlan.PREMIUM)
    patient, session = _setup_session(client, ctx, db_session)

    response = client.post(
        f"/v1/sessions/{session['id']}/charge",
        json={"amount": 150.5, "due_date": "2026-08-01", "notes": "Convênio X"},
        headers=ctx["headers"],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["amount"] == 150.5
    assert body["payment_status"] == "pending"
    assert body["patient_id"] == patient["id"]


def test_create_charge_rejected_when_premium_but_not_active(client, db_session):
    ctx = register_clinic(client)
    _make_plan(db_session, ctx["user"]["clinic_id"], SubscriptionPlan.PREMIUM, active=False)
    patient, session = _setup_session(client, ctx, db_session)

    response = client.post(f"/v1/sessions/{session['id']}/charge", json={"amount": 100}, headers=ctx["headers"])
    assert response.status_code == 403


def test_duplicate_charge_for_same_session_conflicts(client, db_session):
    ctx = register_clinic(client)
    _make_plan(db_session, ctx["user"]["clinic_id"], SubscriptionPlan.ENTERPRISE)
    patient, session = _setup_session(client, ctx, db_session)

    first = client.post(f"/v1/sessions/{session['id']}/charge", json={"amount": 100}, headers=ctx["headers"])
    assert first.status_code == 201

    second = client.post(f"/v1/sessions/{session['id']}/charge", json={"amount": 200}, headers=ctx["headers"])
    assert second.status_code == 409


def test_negative_or_zero_amount_rejected(client, db_session):
    ctx = register_clinic(client)
    _make_plan(db_session, ctx["user"]["clinic_id"], SubscriptionPlan.PREMIUM)
    patient, session = _setup_session(client, ctx, db_session)

    response = client.post(f"/v1/sessions/{session['id']}/charge", json={"amount": 0}, headers=ctx["headers"])
    assert response.status_code == 422


def test_only_admin_can_create_charge(client, db_session):
    ctx = register_clinic(client)
    _make_plan(db_session, ctx["user"]["clinic_id"], SubscriptionPlan.PREMIUM)
    professional = invite_and_accept_professional(client, ctx["headers"])
    patient, session = _setup_session(client, ctx, db_session)

    response = client.post(
        f"/v1/sessions/{session['id']}/charge", json={"amount": 100}, headers=professional["headers"]
    )
    assert response.status_code == 403


def test_update_status_sets_and_clears_paid_at(client, db_session):
    ctx = register_clinic(client)
    _make_plan(db_session, ctx["user"]["clinic_id"], SubscriptionPlan.PREMIUM)
    patient, session = _setup_session(client, ctx, db_session)
    charge = client.post(
        f"/v1/sessions/{session['id']}/charge", json={"amount": 100}, headers=ctx["headers"]
    ).json()

    paid = client.post(
        f"/v1/session-charges/{charge['id']}/status", json={"payment_status": "paid"}, headers=ctx["headers"]
    )
    assert paid.status_code == 200
    assert paid.json()["paid_at"] is not None

    back_to_pending = client.post(
        f"/v1/session-charges/{charge['id']}/status", json={"payment_status": "pending"}, headers=ctx["headers"]
    )
    assert back_to_pending.json()["paid_at"] is None


def test_update_charge_amount_and_notes(client, db_session):
    ctx = register_clinic(client)
    _make_plan(db_session, ctx["user"]["clinic_id"], SubscriptionPlan.PREMIUM)
    patient, session = _setup_session(client, ctx, db_session)
    charge = client.post(
        f"/v1/sessions/{session['id']}/charge", json={"amount": 100}, headers=ctx["headers"]
    ).json()

    updated = client.patch(
        f"/v1/session-charges/{charge['id']}", json={"amount": 175.25, "notes": "Ajustado"}, headers=ctx["headers"]
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == 175.25
    assert updated.json()["notes"] == "Ajustado"


def test_get_charge_for_session_returns_none_then_the_charge(client, db_session):
    ctx = register_clinic(client)
    _make_plan(db_session, ctx["user"]["clinic_id"], SubscriptionPlan.PREMIUM)
    patient, session = _setup_session(client, ctx, db_session)

    before = client.get(f"/v1/sessions/{session['id']}/charge", headers=ctx["headers"])
    assert before.status_code == 200
    assert before.json() is None

    client.post(f"/v1/sessions/{session['id']}/charge", json={"amount": 100}, headers=ctx["headers"])

    after = client.get(f"/v1/sessions/{session['id']}/charge", headers=ctx["headers"])
    assert after.json()["amount"] == 100.0


def test_list_charges_for_patient(client, db_session):
    ctx = register_clinic(client)
    _make_plan(db_session, ctx["user"]["clinic_id"], SubscriptionPlan.PREMIUM)
    patient, session = _setup_session(client, ctx, db_session)
    client.post(f"/v1/sessions/{session['id']}/charge", json={"amount": 100}, headers=ctx["headers"])

    listed = client.get(f"/v1/patients/{patient['id']}/session-charges", headers=ctx["headers"])
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_export_csv_includes_charge_row(client, db_session):
    ctx = register_clinic(client)
    _make_plan(db_session, ctx["user"]["clinic_id"], SubscriptionPlan.PREMIUM)
    patient, session = _setup_session(client, ctx, db_session)
    client.post(f"/v1/sessions/{session['id']}/charge", json={"amount": 250}, headers=ctx["headers"])

    response = client.get("/v1/session-charges/export.csv", headers=ctx["headers"])
    assert response.status_code == 200
    assert patient["name"] in response.text
    assert "250.00" in response.text


def test_session_charges_tenant_isolation(client, db_session):
    clinic_a = register_clinic(client, "Clinica Billing A")
    clinic_b = register_clinic(client, "Clinica Billing B")
    _make_plan(db_session, clinic_a["user"]["clinic_id"], SubscriptionPlan.ENTERPRISE)
    _make_plan(db_session, clinic_b["user"]["clinic_id"], SubscriptionPlan.ENTERPRISE)
    patient_a, session_a = _setup_session(client, clinic_a, db_session)
    charge_a = client.post(
        f"/v1/sessions/{session_a['id']}/charge", json={"amount": 100}, headers=clinic_a["headers"]
    ).json()

    forbidden_list = client.get(f"/v1/patients/{patient_a['id']}/session-charges", headers=clinic_b["headers"])
    assert forbidden_list.status_code == 404

    forbidden_update = client.patch(
        f"/v1/session-charges/{charge_a['id']}", json={"amount": 500}, headers=clinic_b["headers"]
    )
    assert forbidden_update.status_code == 404

    export_b = client.get("/v1/session-charges/export.csv", headers=clinic_b["headers"])
    assert patient_a["name"] not in export_b.text


def test_individual_tenant_can_bill_sessions(client, db_session):
    individual = register_individual(client)
    from app.models.user import User

    user = db_session.query(User).filter(User.id == individual["user"]["id"]).first()
    user.subscription_plan = SubscriptionPlan.PREMIUM
    user.subscription_status = SubscriptionStatus.ACTIVE
    db_session.commit()

    patient = create_patient(client, individual["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = _create_session(client, individual["headers"], patient["id"], individual["user"]["id"], str(training.id))

    response = client.post(
        f"/v1/sessions/{session['id']}/charge", json={"amount": 120}, headers=individual["headers"]
    )
    assert response.status_code == 201, response.text
