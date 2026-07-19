import datetime

from app.models.treatment_plan import Objective
from app.services import clinical_alert_service
from tests.conftest import (
    assign_professional,
    create_patient,
    create_training,
    create_training_category,
    invite_and_accept,
    invite_and_accept_professional,
    register_clinic,
    register_individual,
)


def _create_objective_with_training(client, headers, patient_id, training_id, **overrides):
    payload = {"area": "aba", "title": "Objetivo Supervisor", "training_ids": [str(training_id)]}
    payload.update(overrides)
    response = client.post(f"/v1/patients/{patient_id}/treatment-plan/objectives", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _add_session(db_session, patient_id, professional_id, training_id, occurred_at, trial_count=3):
    from app.models.enums import PromptLevel, TrialResult
    from app.models.patient import Patient
    from app.models.session import ClinicalSession, SessionTraining, Trial

    session = ClinicalSession(patient_id=patient_id, professional_id=professional_id, occurred_at=occurred_at)
    patient = db_session.get(Patient, patient_id)
    session.clinic_id = patient.clinic_id
    session.individual_owner_id = patient.individual_owner_id
    db_session.add(session)
    db_session.flush()

    session_training = SessionTraining(session_id=session.id, training_id=training_id, sequence=1)
    db_session.add(session_training)
    db_session.flush()

    for i in range(trial_count):
        db_session.add(
            Trial(
                session_training_id=session_training.id,
                attempt_number=i + 1,
                result=TrialResult.CORRECT,
                prompt_level=PromptLevel.INDEPENDENT,
                recorded_at=occurred_at,
            )
        )
    db_session.commit()
    return session


def _create_appointment_and_complete_it(client, headers, patient_id, professional_id, occurred_at):
    appt = client.post(
        "/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "scheduled_start": occurred_at.isoformat(),
            "scheduled_end": (occurred_at + datetime.timedelta(minutes=30)).isoformat(),
        },
        headers=headers,
    )
    assert appt.status_code == 201, appt.text
    client.post(
        "/v1/sessions",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "occurred_at": occurred_at.isoformat(),
            "appointment_id": appt.json()["id"],
        },
        headers=headers,
    )


def _create_no_show_appointment(client, headers, patient_id, professional_id, occurred_at):
    appt = client.post(
        "/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "scheduled_start": occurred_at.isoformat(),
            "scheduled_end": (occurred_at + datetime.timedelta(minutes=30)).isoformat(),
        },
        headers=headers,
    )
    assert appt.status_code == 201, appt.text
    client.post(f"/v1/appointments/{appt.json()['id']}/no-show", json={"reason": "patient"}, headers=headers)


def test_dashboard_forbidden_for_professional(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    response = client.get("/v1/clinic/supervisor-dashboard", headers=professional["headers"])
    assert response.status_code == 403


def test_dashboard_forbidden_for_individual_account(client):
    ctx = register_individual(client)

    response = client.get("/v1/clinic/supervisor-dashboard", headers=ctx["headers"])
    assert response.status_code == 403


def test_dashboard_allows_supervisor_role(client):
    ctx = register_clinic(client)
    supervisor = invite_and_accept(client, ctx["headers"], role="supervisor")

    response = client.get("/v1/clinic/supervisor-dashboard", headers=supervisor["headers"])
    assert response.status_code == 200


def test_dashboard_computes_session_completion_pct(client):
    """Seção 29.4 — percentual de sessões completas por terapeuta."""
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])
    patient = create_patient(client, ctx["headers"])
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"])

    now = datetime.datetime.now(datetime.timezone.utc)
    _create_appointment_and_complete_it(
        client, professional["headers"], patient["id"], professional["user"]["id"], now
    )
    _create_no_show_appointment(
        client, professional["headers"], patient["id"], professional["user"]["id"], now + datetime.timedelta(days=1)
    )

    data = client.get("/v1/clinic/supervisor-dashboard", headers=ctx["headers"]).json()
    row = next(t for t in data["therapists"] if t["professional_id"] == professional["user"]["id"])
    assert row["assigned_patients_count"] == 1
    assert row["completed_sessions_count"] == 1
    assert row["no_show_count"] == 1
    assert row["session_completion_pct"] == 50.0


def test_dashboard_full_adherence_when_no_alerts(client, db_session):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])
    patient = create_patient(client, ctx["headers"])
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"])

    category = create_training_category(db_session)
    training = create_training(db_session, category)
    _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    data = client.get("/v1/clinic/supervisor-dashboard", headers=ctx["headers"]).json()
    row = next(t for t in data["therapists"] if t["professional_id"] == professional["user"]["id"])
    assert row["active_objectives_count"] == 1
    assert row["treatment_plan_adherence_pct"] == 100.0
    assert row["low_adherence_alert"] is False


def test_dashboard_flags_low_adherence_and_no_recent_registration(client, db_session):
    """Seção 29.4 — alertas automáticos de baixa adesão e ausência de registro."""
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])
    patient = create_patient(client, ctx["headers"])
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"])

    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    old_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=20)
    _add_session(db_session, patient["id"], professional["user"]["id"], training.id, old_date)

    import uuid as uuid_module

    objective_model = db_session.get(Objective, uuid_module.UUID(objective["id"]))
    clinical_alert_service.recompute_alerts_for_objective(db_session, objective_model)

    data = client.get("/v1/clinic/supervisor-dashboard", headers=ctx["headers"]).json()
    row = next(t for t in data["therapists"] if t["professional_id"] == professional["user"]["id"])
    assert row["treatment_plan_adherence_pct"] == 0.0
    assert row["low_adherence_alert"] is True
    assert row["no_recent_registration_alert"] is True


def test_dashboard_no_alert_for_therapist_without_assigned_patients(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    data = client.get("/v1/clinic/supervisor-dashboard", headers=ctx["headers"]).json()
    row = next(t for t in data["therapists"] if t["professional_id"] == professional["user"]["id"])
    assert row["assigned_patients_count"] == 0
    assert row["no_recent_registration_alert"] is False
    assert row["treatment_plan_adherence_pct"] is None


def test_dashboard_tenant_isolation(client):
    clinic_a = register_clinic(client, "Clinica Supervisor A")
    clinic_b = register_clinic(client, "Clinica Supervisor B")
    professional_a = invite_and_accept_professional(client, clinic_a["headers"])

    data_b = client.get("/v1/clinic/supervisor-dashboard", headers=clinic_b["headers"]).json()
    assert all(t["professional_id"] != professional_a["user"]["id"] for t in data_b["therapists"])
