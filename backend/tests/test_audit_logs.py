from tests.conftest import create_patient, invite_and_accept_professional, register_clinic, register_individual


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
