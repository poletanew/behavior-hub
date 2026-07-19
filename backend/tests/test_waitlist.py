from tests.conftest import invite_and_accept_professional, register_clinic, register_individual


def test_create_and_list_waitlist_entry(client):
    ctx = register_clinic(client)
    response = client.post(
        "/v1/waitlist",
        json={"name": "Criança em triagem", "guardian_name": "Responsável Teste", "contact_phone": "11999999999"},
        headers=ctx["headers"],
    )
    assert response.status_code == 201, response.text
    entry = response.json()
    assert entry["status"] == "waiting"
    assert entry["birth_date"] is None

    listed = client.get("/v1/waitlist", headers=ctx["headers"])
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_update_waiting_entry(client):
    ctx = register_clinic(client)
    entry = client.post("/v1/waitlist", json={"name": "Criança X"}, headers=ctx["headers"]).json()

    updated = client.patch(
        f"/v1/waitlist/{entry['id']}", json={"notes": "Encaminhado pelo pediatra"}, headers=ctx["headers"]
    )
    assert updated.status_code == 200
    assert updated.json()["notes"] == "Encaminhado pelo pediatra"


def test_discard_entry(client):
    ctx = register_clinic(client)
    entry = client.post("/v1/waitlist", json={"name": "Criança Y"}, headers=ctx["headers"]).json()

    discarded = client.post(f"/v1/waitlist/{entry['id']}/discard", headers=ctx["headers"])
    assert discarded.status_code == 200
    assert discarded.json()["status"] == "discarded"

    cannot_edit = client.patch(f"/v1/waitlist/{entry['id']}", json={"notes": "x"}, headers=ctx["headers"])
    assert cannot_edit.status_code == 409

    cannot_discard_again = client.post(f"/v1/waitlist/{entry['id']}/discard", headers=ctx["headers"])
    assert cannot_discard_again.status_code == 409


def test_convert_without_birth_date_requires_one(client):
    ctx = register_clinic(client)
    entry = client.post("/v1/waitlist", json={"name": "Criança Z"}, headers=ctx["headers"]).json()

    missing = client.post(f"/v1/waitlist/{entry['id']}/convert", json={}, headers=ctx["headers"])
    assert missing.status_code == 422

    converted = client.post(
        f"/v1/waitlist/{entry['id']}/convert",
        json={"birth_date": "2019-01-01", "diagnosis": "TEA"},
        headers=ctx["headers"],
    )
    assert converted.status_code == 200, converted.text
    body = converted.json()
    assert body["status"] == "converted"
    assert body["converted_patient_id"] is not None

    patient = client.get(f"/v1/patients/{body['converted_patient_id']}", headers=ctx["headers"]).json()
    assert patient["name"] == "Criança Z"
    assert patient["birth_date"] == "2019-01-01"
    assert patient["diagnosis"] == "TEA"


def test_convert_reuses_birth_date_already_captured(client):
    ctx = register_clinic(client)
    entry = client.post(
        "/v1/waitlist", json={"name": "Criança W", "birth_date": "2020-05-05"}, headers=ctx["headers"]
    ).json()

    converted = client.post(f"/v1/waitlist/{entry['id']}/convert", json={}, headers=ctx["headers"])
    assert converted.status_code == 200, converted.text

    patient = client.get(
        f"/v1/patients/{converted.json()['converted_patient_id']}", headers=ctx["headers"]
    ).json()
    assert patient["birth_date"] == "2020-05-05"


def test_cannot_convert_twice(client):
    ctx = register_clinic(client)
    entry = client.post(
        "/v1/waitlist", json={"name": "Criança V", "birth_date": "2020-01-01"}, headers=ctx["headers"]
    ).json()

    first = client.post(f"/v1/waitlist/{entry['id']}/convert", json={}, headers=ctx["headers"])
    assert first.status_code == 200

    second = client.post(f"/v1/waitlist/{entry['id']}/convert", json={}, headers=ctx["headers"])
    assert second.status_code == 409


def test_filter_by_status(client):
    ctx = register_clinic(client)
    entry1 = client.post(
        "/v1/waitlist", json={"name": "A", "birth_date": "2020-01-01"}, headers=ctx["headers"]
    ).json()
    client.post("/v1/waitlist", json={"name": "B"}, headers=ctx["headers"])
    client.post(f"/v1/waitlist/{entry1['id']}/convert", json={}, headers=ctx["headers"])

    waiting = client.get("/v1/waitlist?status=waiting", headers=ctx["headers"]).json()
    assert len(waiting) == 1
    assert waiting[0]["name"] == "B"

    converted = client.get("/v1/waitlist?status=converted", headers=ctx["headers"]).json()
    assert len(converted) == 1
    assert converted[0]["name"] == "A"


def test_professional_without_permission_rejected(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    response = client.post("/v1/waitlist", json={"name": "Criança"}, headers=professional["headers"])
    assert response.status_code == 403


def test_waitlist_tenant_isolation(client):
    clinic_a = register_clinic(client, "Clinica Waitlist A")
    clinic_b = register_clinic(client, "Clinica Waitlist B")
    entry = client.post("/v1/waitlist", json={"name": "Criança A"}, headers=clinic_a["headers"]).json()

    listed_b = client.get("/v1/waitlist", headers=clinic_b["headers"]).json()
    assert listed_b == []

    forbidden_update = client.patch(
        f"/v1/waitlist/{entry['id']}", json={"notes": "x"}, headers=clinic_b["headers"]
    )
    assert forbidden_update.status_code == 404


def test_individual_tenant_can_use_waitlist(client):
    individual = register_individual(client)
    entry = client.post(
        "/v1/waitlist", json={"name": "Criança Individual", "birth_date": "2021-01-01"}, headers=individual["headers"]
    )
    assert entry.status_code == 201

    converted = client.post(
        f"/v1/waitlist/{entry.json()['id']}/convert", json={}, headers=individual["headers"]
    )
    assert converted.status_code == 200
