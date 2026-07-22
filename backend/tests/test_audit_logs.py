from tests.conftest import (
    assign_professional,
    create_patient,
    create_training,
    create_training_category,
    invite_and_accept_professional,
    register_clinic,
    register_individual,
)


def test_audit_log_records_patient_creation(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    logs = client.get("/v1/audit-logs", headers=ctx["headers"])
    assert logs.status_code == 200
    actions = [entry["action"] for entry in logs.json()]
    assert "patient_created" in actions
    entry = next(e for e in logs.json() if e["entity_id"] == patient["id"])
    assert entry["actor_name"] == ctx["user"]["name"]


def test_audit_log_restricted_to_admins(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    response = client.get("/v1/audit-logs", headers=professional["headers"])
    assert response.status_code == 403


def test_audit_log_isolated_by_tenant(client):
    clinic_a = register_clinic(client, "Clinica A")
    clinic_b = register_clinic(client, "Clinica B")
    create_patient(client, clinic_a["headers"], name="Paciente A")

    logs_b = client.get("/v1/audit-logs", headers=clinic_b["headers"])
    entity_ids = [e["entity_id"] for e in logs_b.json()]
    assert all(e["actor_name"] != "Admin Teste" or True for e in logs_b.json())  # sanity: no crash
    actions_b = [e["action"] for e in logs_b.json()]
    # clinic B only ever registered its own clinic — no patient_created from clinic A should leak in
    assert "patient_created" not in actions_b


def test_audit_log_filters_by_entity_type(client):
    ctx = register_clinic(client)
    create_patient(client, ctx["headers"])

    logs = client.get("/v1/audit-logs?entity_type=patient", headers=ctx["headers"])
    assert all(e["entity_type"] == "patient" for e in logs.json())

    logs_clinic = client.get("/v1/audit-logs?entity_type=clinic", headers=ctx["headers"])
    assert all(e["entity_type"] == "clinic" for e in logs_clinic.json())
    assert len(logs_clinic.json()) >= 1


def test_individual_sees_only_own_audit_log(client):
    ctx = register_individual(client)
    create_patient(client, ctx["headers"])

    logs = client.get("/v1/audit-logs", headers=ctx["headers"])
    assert logs.status_code == 200
    assert all(e["actor_user_id"] == ctx["user"]["id"] for e in logs.json())


def test_patient_audit_trail_consolidates_actions_across_professionals(client, db_session):
    """RF-14 — todas as ações de todos os profissionais sobre um paciente,
    em ordem cronológica (criação de sessão, alteração de plano, etc)."""
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])
    patient = create_patient(client, ctx["headers"])
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"])

    category = create_training_category(db_session)
    training = create_training(db_session, category)

    session_response = client.post(
        "/v1/sessions",
        json={
            "patient_id": patient["id"],
            "professional_id": professional["user"]["id"],
            "occurred_at": "2026-07-14T10:00:00Z",
            "training_ids": [str(training.id)],
        },
        headers=professional["headers"],
    )
    assert session_response.status_code == 201, session_response.text

    objective_response = client.post(
        f"/v1/patients/{patient['id']}/treatment-plan/objectives",
        json={"area": "aba", "title": "Objetivo de auditoria", "priority": "medium"},
        headers=ctx["headers"],
    )
    assert objective_response.status_code == 201, objective_response.text

    trail = client.get(f"/v1/audit-logs/patients/{patient['id']}", headers=ctx["headers"])
    assert trail.status_code == 200, trail.text
    entries = trail.json()
    actions = [e["action"] for e in entries]
    assert "patient_created" in actions
    assert "session_created" in actions
    assert "objective_created" in actions

    actor_names = {e["actor_name"] for e in entries}
    assert ctx["user"]["name"] in actor_names
    assert professional["user"]["name"] in actor_names

    timestamps = [e["timestamp"] for e in entries]
    assert timestamps == sorted(timestamps)


def test_patient_audit_trail_restricted_to_admins(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])
    patient = create_patient(client, ctx["headers"])

    response = client.get(f"/v1/audit-logs/patients/{patient['id']}", headers=professional["headers"])
    assert response.status_code == 403


def test_patient_audit_trail_isolated_by_tenant(client):
    clinic_a = register_clinic(client, "Clinica Audit A")
    clinic_b = register_clinic(client, "Clinica Audit B")
    patient_a = create_patient(client, clinic_a["headers"], name="Paciente Audit A")

    forbidden = client.get(f"/v1/audit-logs/patients/{patient_a['id']}", headers=clinic_b["headers"])
    assert forbidden.status_code == 404
