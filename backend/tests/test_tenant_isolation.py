from tests.conftest import invite_and_accept_professional, register_clinic, register_individual


def _create_patient(client, headers, name="Paciente Exemplo"):
    response = client.post(
        "/v1/patients",
        json={"name": name, "birth_date": "2018-05-10"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_other_clinic_cannot_access_patient_by_direct_id(client):
    """AC-14 — usuario de outra clinica nunca acessa o paciente por URL direta."""
    clinic_a = register_clinic(client, "Clinica A")
    clinic_b = register_clinic(client, "Clinica B")

    patient = _create_patient(client, clinic_a["headers"])

    response = client.get(f"/v1/patients/{patient['id']}", headers=clinic_b["headers"])
    assert response.status_code == 404


def test_other_clinic_cannot_list_patient(client):
    clinic_a = register_clinic(client, "Clinica A")
    clinic_b = register_clinic(client, "Clinica B")

    _create_patient(client, clinic_a["headers"])

    listing = client.get("/v1/patients", headers=clinic_b["headers"])
    assert listing.json() == []


def test_individual_tenants_are_isolated_from_each_other(client):
    individual_a = register_individual(client)
    individual_b = register_individual(client)

    patient = _create_patient(client, individual_a["headers"])

    response = client.get(f"/v1/patients/{patient['id']}", headers=individual_b["headers"])
    assert response.status_code == 404


def test_professional_only_sees_assigned_patients(client):
    """Seção 7.3/17.1 — profissional visualiza apenas pacientes atribuidos."""
    clinic = register_clinic(client)
    professional = invite_and_accept_professional(client, clinic["headers"])

    assigned_patient = _create_patient(client, clinic["headers"], name="Atribuido")
    unassigned_patient = _create_patient(client, clinic["headers"], name="Nao atribuido")

    assign_response = client.post(
        f"/v1/patients/{assigned_patient['id']}/assignments",
        json={"professional_id": professional["user"]["id"], "permission": "edit_sessions"},
        headers=clinic["headers"],
    )
    assert assign_response.status_code == 201

    listing = client.get("/v1/patients", headers=professional["headers"])
    ids = {p["id"] for p in listing.json()}
    assert ids == {assigned_patient["id"]}

    forbidden = client.get(f"/v1/patients/{unassigned_patient['id']}", headers=professional["headers"])
    assert forbidden.status_code == 404


def test_removing_assignment_revokes_access(client):
    clinic = register_clinic(client)
    professional = invite_and_accept_professional(client, clinic["headers"])
    patient = _create_patient(client, clinic["headers"])

    client.post(
        f"/v1/patients/{patient['id']}/assignments",
        json={"professional_id": professional["user"]["id"]},
        headers=clinic["headers"],
    )
    accessible = client.get(f"/v1/patients/{patient['id']}", headers=professional["headers"])
    assert accessible.status_code == 200

    remove_response = client.delete(
        f"/v1/patients/{patient['id']}/assignments/{professional['user']['id']}", headers=clinic["headers"]
    )
    assert remove_response.status_code == 204

    now_forbidden = client.get(f"/v1/patients/{patient['id']}", headers=professional["headers"])
    assert now_forbidden.status_code == 404


def test_sessions_are_isolated_by_tenant(client):
    clinic_a = register_clinic(client, "Clinica A")
    clinic_b = register_clinic(client, "Clinica B")
    patient_a = _create_patient(client, clinic_a["headers"])

    session_response = client.post(
        "/v1/sessions",
        json={
            "patient_id": patient_a["id"],
            "professional_id": clinic_a["user"]["id"],
            "occurred_at": "2026-07-14T10:00:00Z",
            "training_ids": [],
        },
        headers=clinic_a["headers"],
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["id"]

    forbidden = client.get(f"/v1/sessions/{session_id}", headers=clinic_b["headers"])
    assert forbidden.status_code == 404

    listing_b = client.get("/v1/sessions", headers=clinic_b["headers"])
    assert listing_b.json() == []
