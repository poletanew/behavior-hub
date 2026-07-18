import datetime

from tests.conftest import register_clinic, register_individual


def _create_patient(client, headers, name="Paciente Exemplo"):
    response = client.post(
        "/v1/patients",
        json={
            "name": name,
            "birth_date": "2018-05-10",
            "guardian_name": "Responsavel Exemplo",
            "diagnosis": "TEA",
        },
        headers=headers,
    )
    return response


def test_create_and_list_patient(client):
    ctx = register_clinic(client)
    response = _create_patient(client, ctx["headers"])
    assert response.status_code == 201
    patient = response.json()
    assert patient["name"] == "Paciente Exemplo"
    assert patient["clinic_id"] == ctx["user"]["clinic_id"]

    listing = client.get("/v1/patients", headers=ctx["headers"])
    assert len(listing.json()) == 1


def test_free_plan_blocks_fourth_active_patient(client):
    """AC-02 — o quarto paciente e bloqueado no backend."""
    ctx = register_clinic(client)
    for i in range(3):
        response = _create_patient(client, ctx["headers"], name=f"Paciente {i}")
        assert response.status_code == 201

    fourth = _create_patient(client, ctx["headers"], name="Paciente 4")
    assert fourth.status_code == 403


def test_soft_delete_removes_patient_from_active_list_and_dashboard(client):
    """AC-10 — excluir paciente remove-o das abas ativas e o coloca em Deleted Data."""
    ctx = register_clinic(client)
    patient = _create_patient(client, ctx["headers"]).json()

    delete_response = client.delete(f"/v1/patients/{patient['id']}", headers=ctx["headers"])
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_at"] is not None

    listing = client.get("/v1/patients", headers=ctx["headers"])
    assert listing.json() == []

    dashboard = client.get("/v1/dashboard", headers=ctx["headers"])
    assert dashboard.json()["active_patients_count"] == 0

    deleted_list = client.get("/v1/patients/deleted/list", headers=ctx["headers"])
    assert len(deleted_list.json()) == 1
    assert deleted_list.json()[0]["id"] == patient["id"]


def test_restore_patient(client):
    """AC-11 — restaurar paciente repoe o registro nas listas ativas."""
    ctx = register_clinic(client)
    patient = _create_patient(client, ctx["headers"]).json()
    client.delete(f"/v1/patients/{patient['id']}", headers=ctx["headers"])

    restore_response = client.post(f"/v1/patients/{patient['id']}/restore", headers=ctx["headers"])
    assert restore_response.status_code == 200
    assert restore_response.json()["deleted_at"] is None

    listing = client.get("/v1/patients", headers=ctx["headers"])
    assert len(listing.json()) == 1


def test_deleted_data_tab_restricted_to_admins(client):
    """Seção 16.2 — profissionais comuns nao acessam a aba de Deleted Data."""
    from tests.conftest import invite_and_accept_professional

    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    response = client.get("/v1/patients/deleted/list", headers=professional["headers"])
    assert response.status_code == 403


def test_individual_tenant_can_manage_own_patients(client):
    ctx = register_individual(client)
    response = _create_patient(client, ctx["headers"])
    assert response.status_code == 201
    assert response.json()["individual_owner_id"] == ctx["user"]["id"]
