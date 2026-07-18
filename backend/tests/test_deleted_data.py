from tests.conftest import create_patient, invite_and_accept_professional, register_clinic


def _create_objective(client, headers, patient_id):
    return client.post(
        f"/v1/patients/{patient_id}/treatment-plan/objectives",
        json={"area": "aba", "title": "Objetivo de teste"},
        headers=headers,
    ).json()


def _upload_pdf(client, headers, title="Recurso de teste"):
    return client.post(
        "/v1/resources",
        data={"title": title, "visibility": "clinic_shared"},
        files={"file": ("atividade.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        headers=headers,
    ).json()


def test_deleted_data_unifies_patients_objectives_and_resources(client, mock_s3):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"], name="Paciente a Excluir")
    other_patient = create_patient(client, ctx["headers"], name="Paciente com Objetivo")
    objective = _create_objective(client, ctx["headers"], other_patient["id"])
    resource = _upload_pdf(client, ctx["headers"])

    client.delete(f"/v1/patients/{patient['id']}", headers=ctx["headers"])
    client.delete(f"/v1/objectives/{objective['id']}", headers=ctx["headers"])
    client.delete(f"/v1/resources/{resource['id']}", headers=ctx["headers"])

    listing = client.get("/v1/deleted-data", headers=ctx["headers"])
    assert listing.status_code == 200
    entity_types = {item["entity_type"] for item in listing.json()}
    assert entity_types == {"patient", "objective", "resource"}
    for item in listing.json():
        assert item["days_remaining"] == 59 or item["days_remaining"] == 60


def test_deleted_data_restricted_to_admins(client):
    """Seção 16.2 — profissionais comuns não acessam a aba de Dados Excluídos."""
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    response = client.get("/v1/deleted-data", headers=professional["headers"])
    assert response.status_code == 403


def test_restore_dispatch_for_each_entity_type(client, mock_s3):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    objective = _create_objective(client, ctx["headers"], patient["id"])
    resource = _upload_pdf(client, ctx["headers"])

    client.delete(f"/v1/objectives/{objective['id']}", headers=ctx["headers"])
    client.delete(f"/v1/resources/{resource['id']}", headers=ctx["headers"])

    restore_objective = client.post(f"/v1/deleted-data/objective/{objective['id']}/restore", headers=ctx["headers"])
    assert restore_objective.status_code == 200

    restore_resource = client.post(f"/v1/deleted-data/resource/{resource['id']}/restore", headers=ctx["headers"])
    assert restore_resource.status_code == 200

    listing = client.get("/v1/deleted-data", headers=ctx["headers"])
    assert listing.json() == []


def test_deleted_data_isolated_by_tenant(client):
    clinic_a = register_clinic(client, "Clinica A")
    clinic_b = register_clinic(client, "Clinica B")
    patient = create_patient(client, clinic_a["headers"])
    client.delete(f"/v1/patients/{patient['id']}", headers=clinic_a["headers"])

    listing_b = client.get("/v1/deleted-data", headers=clinic_b["headers"])
    assert listing_b.json() == []
