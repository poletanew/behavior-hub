from app.models.clinic import Clinic
from app.models.enums import SubscriptionPlan, SubscriptionStatus
from tests.conftest import create_patient, create_training, create_training_category, invite_and_accept, register_clinic


def _create_objective(client, headers, patient_id, training_id, **overrides):
    payload = {
        "area": "aba",
        "title": "Objetivo de teste",
        "priority": "medium",
        "training_ids": [training_id],
    }
    payload.update(overrides)
    return client.post(f"/v1/patients/{patient_id}/treatment-plan/objectives", json=payload, headers=headers)


def test_program_performance_requires_clinic_admin(client):
    ctx = register_clinic(client)
    supervisor = invite_and_accept(client, ctx["headers"], role="supervisor")

    response = client.get("/v1/clinic/manager-dashboard/program-performance", headers=supervisor["headers"])
    assert response.status_code == 403


def test_program_performance_excludes_training_with_fewer_than_two_patients(client, db_session):
    """Addendum v3.0, RF-32 — "mínimo 2 pacientes" para aparecer no relatório."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    objective = _create_objective(client, ctx["headers"], patient["id"], str(training.id))
    assert objective.status_code == 201, objective.text

    response = client.get("/v1/clinic/manager-dashboard/program-performance", headers=ctx["headers"])
    assert response.status_code == 200
    assert response.json() == []


def test_program_performance_aggregates_mastery_rate_across_patients(client, db_session):
    ctx = register_clinic(client)
    patient_a = create_patient(client, ctx["headers"], name="Paciente A")
    patient_b = create_patient(client, ctx["headers"], name="Paciente B")
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    objective_a = _create_objective(client, ctx["headers"], patient_a["id"], str(training.id)).json()
    objective_b = _create_objective(client, ctx["headers"], patient_b["id"], str(training.id)).json()

    mastered = client.patch(
        f"/v1/objectives/{objective_a['id']}", json={"status": "mastered"}, headers=ctx["headers"]
    )
    assert mastered.status_code == 200, mastered.text

    response = client.get("/v1/clinic/manager-dashboard/program-performance", headers=ctx["headers"])
    assert response.status_code == 200, response.text
    rows = response.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["patients_count"] == 2
    assert row["objectives_count"] == 2
    assert row["mastery_rate_pct"] == 50.0
    assert row["average_days_to_mastery"] is not None
    assert objective_b["status"] == "not_started"


def test_financial_outlook_requires_clinic_admin(client):
    ctx = register_clinic(client)
    supervisor = invite_and_accept(client, ctx["headers"], role="supervisor")

    response = client.get("/v1/clinic/manager-dashboard/financial-outlook", headers=supervisor["headers"])
    assert response.status_code == 403


def test_financial_outlook_reflects_subscription_status(client, db_session):
    """Addendum v3.0, RF-32 — previsibilidade financeira usando os dados de
    assinatura Stripe já existentes (Seção 8.3), por clínica."""
    ctx = register_clinic(client)

    no_subscription = client.get("/v1/clinic/manager-dashboard/financial-outlook", headers=ctx["headers"])
    assert no_subscription.status_code == 200, no_subscription.text
    assert no_subscription.json()["subscription_status"] == "none"
    assert no_subscription.json()["churn_risk_label"] == "nao_aplicavel"

    clinic = db_session.query(Clinic).filter(Clinic.id == ctx["user"]["clinic_id"]).first()
    clinic.subscription_plan = SubscriptionPlan.PREMIUM
    clinic.subscription_status = SubscriptionStatus.PAST_DUE
    db_session.commit()

    at_risk = client.get("/v1/clinic/manager-dashboard/financial-outlook", headers=ctx["headers"])
    assert at_risk.status_code == 200
    body = at_risk.json()
    assert body["subscription_plan"] == "premium"
    assert body["churn_risk_label"] == "alto"
