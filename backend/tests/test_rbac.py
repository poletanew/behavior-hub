from tests.conftest import (
    assign_professional,
    create_patient,
    invite_and_accept,
    invite_and_accept_professional,
    register_clinic,
    register_individual,
)


def _create_objective(client, headers, patient_id, **overrides):
    payload = {"area": "aba", "title": "Objetivo RBAC"}
    payload.update(overrides)
    return client.post(f"/v1/patients/{patient_id}/treatment-plan/objectives", json=payload, headers=headers)


def test_default_permission_settings_are_conservative(client):
    """Seção 17.1 — por padrão, ações "Configurável" começam desabilitadas para
    supervisor/profissional, exceto onde a tabela do PRD já é permissiva por padrão."""
    ctx = register_clinic(client)
    settings = client.get("/v1/clinic/permission-settings", headers=ctx["headers"])
    assert settings.status_code == 200
    body = settings.json()
    assert body["professionals_can_create_patients"] is False
    assert body["supervisors_can_edit_any_objective_area"] is False
    assert body["supervisors_can_restore_deleted_data"] is False
    assert body["supervisors_can_generate_invitations"] is False
    assert body["admins_can_edit_any_objective_area"] is True
    assert body["supervisors_can_register_sessions"] is True


def test_professional_cannot_create_patient_by_default(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    response = client.post(
        "/v1/patients", json={"name": "Paciente X", "birth_date": "2018-01-01"}, headers=professional["headers"]
    )
    assert response.status_code == 403


def test_professional_can_create_patient_when_enabled(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    client.patch(
        "/v1/clinic/permission-settings",
        json={"professionals_can_create_patients": True},
        headers=ctx["headers"],
    )

    response = client.post(
        "/v1/patients", json={"name": "Paciente Y", "birth_date": "2018-01-01"}, headers=professional["headers"]
    )
    assert response.status_code == 201


def test_only_clinic_admin_can_update_permission_settings(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    response = client.patch(
        "/v1/clinic/permission-settings",
        json={"professionals_can_create_patients": True},
        headers=professional["headers"],
    )
    assert response.status_code == 403


def test_supervisor_cannot_edit_objective_by_default_but_can_when_enabled(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    supervisor = invite_and_accept(client, ctx["headers"], role="supervisor")
    assign_professional(client, ctx["headers"], patient["id"], supervisor["user"]["id"], permission="read_only")

    forbidden = _create_objective(client, supervisor["headers"], patient["id"])
    assert forbidden.status_code == 403

    client.patch(
        "/v1/clinic/permission-settings",
        json={"supervisors_can_edit_any_objective_area": True},
        headers=ctx["headers"],
    )
    allowed = _create_objective(client, supervisor["headers"], patient["id"])
    assert allowed.status_code == 201


def test_supervisor_cannot_restore_deleted_data_by_default_but_can_when_enabled(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    supervisor = invite_and_accept(client, ctx["headers"], role="supervisor")
    assign_professional(client, ctx["headers"], patient["id"], supervisor["user"]["id"], permission="full_access")

    client.delete(f"/v1/patients/{patient['id']}", headers=ctx["headers"])

    forbidden = client.post(f"/v1/patients/{patient['id']}/restore", headers=supervisor["headers"])
    assert forbidden.status_code == 403

    client.patch(
        "/v1/clinic/permission-settings",
        json={"supervisors_can_restore_deleted_data": True},
        headers=ctx["headers"],
    )
    allowed = client.post(f"/v1/patients/{patient['id']}/restore", headers=supervisor["headers"])
    assert allowed.status_code == 200


def test_supervisor_cannot_generate_invitation_by_default_but_can_when_enabled(client):
    ctx = register_clinic(client)
    supervisor = invite_and_accept(client, ctx["headers"], role="supervisor")

    forbidden = client.post(
        "/v1/invitations", json={"email": "outro@example.com"}, headers=supervisor["headers"]
    )
    assert forbidden.status_code == 403

    client.patch(
        "/v1/clinic/permission-settings",
        json={"supervisors_can_generate_invitations": True},
        headers=ctx["headers"],
    )
    allowed = client.post(
        "/v1/invitations", json={"email": "outro2@example.com"}, headers=supervisor["headers"]
    )
    assert allowed.status_code == 201


def test_invited_supervisor_has_supervisor_user_type(client):
    ctx = register_clinic(client)
    supervisor = invite_and_accept(client, ctx["headers"], role="supervisor")
    assert supervisor["user"]["user_type"] == "supervisor"


def test_individual_account_unaffected_by_clinic_permission_settings(client):
    """Contas individuais sempre podem cadastrar paciente — não usam ClinicPermissionSettings."""
    ctx = register_individual(client)
    response = client.post(
        "/v1/patients", json={"name": "Paciente Individual", "birth_date": "2018-01-01"}, headers=ctx["headers"]
    )
    assert response.status_code == 201
