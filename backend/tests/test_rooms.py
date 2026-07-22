import datetime

from tests.conftest import create_patient, register_clinic, register_individual


def _iso(dt: datetime.datetime) -> str:
    return dt.isoformat()


def test_create_and_list_rooms(client):
    ctx = register_clinic(client)
    response = client.post("/v1/rooms", json={"name": "Sala 1"}, headers=ctx["headers"])
    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Sala 1"

    listed = client.get("/v1/rooms", headers=ctx["headers"])
    assert listed.status_code == 200
    assert [r["name"] for r in listed.json()] == ["Sala 1"]


def test_rooms_isolated_by_tenant(client):
    clinic_a = register_clinic(client, "Clinica A")
    clinic_b = register_clinic(client, "Clinica B")
    client.post("/v1/rooms", json={"name": "Sala da Clinica A"}, headers=clinic_a["headers"])

    listed_b = client.get("/v1/rooms", headers=clinic_b["headers"])
    assert listed_b.json() == []


def test_individual_account_can_create_room(client):
    individual = register_individual(client)
    response = client.post("/v1/rooms", json={"name": "Sala Única"}, headers=individual["headers"])
    assert response.status_code == 201, response.text


def test_delete_unused_room(client):
    ctx = register_clinic(client)
    room = client.post("/v1/rooms", json={"name": "Sala 1"}, headers=ctx["headers"]).json()
    response = client.delete(f"/v1/rooms/{room['id']}", headers=ctx["headers"])
    assert response.status_code == 204
    assert client.get("/v1/rooms", headers=ctx["headers"]).json() == []


def test_cannot_delete_room_with_upcoming_appointment(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    room = client.post("/v1/rooms", json={"name": "Sala 1"}, headers=ctx["headers"]).json()
    start = datetime.datetime(2026, 9, 1, 10, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=50)
    client.post(
        "/v1/appointments",
        json={
            "patient_id": patient["id"],
            "professional_id": ctx["user"]["id"],
            "scheduled_start": _iso(start),
            "scheduled_end": _iso(end),
            "room_id": room["id"],
        },
        headers=ctx["headers"],
    )

    response = client.delete(f"/v1/rooms/{room['id']}", headers=ctx["headers"])
    assert response.status_code == 409


def test_appointment_room_conflict_detection(client):
    """Addendum v3.0, RF-26 — mesma sala não pode ter dois atendimentos sobrepostos,
    mesmo com profissionais diferentes."""
    ctx = register_clinic(client)
    patient_a = create_patient(client, ctx["headers"], name="Paciente A")
    patient_b = create_patient(client, ctx["headers"], name="Paciente B")
    room = client.post("/v1/rooms", json={"name": "Sala 1"}, headers=ctx["headers"]).json()

    start = datetime.datetime(2026, 9, 2, 10, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=50)

    first = client.post(
        "/v1/appointments",
        json={
            "patient_id": patient_a["id"],
            "professional_id": ctx["user"]["id"],
            "scheduled_start": _iso(start),
            "scheduled_end": _iso(end),
            "room_id": room["id"],
        },
        headers=ctx["headers"],
    )
    assert first.status_code == 201, first.text
    assert first.json()["room_name"] == "Sala 1"

    overlap_start = start + datetime.timedelta(minutes=20)
    overlap_end = overlap_start + datetime.timedelta(minutes=50)
    conflicting = client.post(
        "/v1/appointments",
        json={
            "patient_id": patient_b["id"],
            "professional_id": ctx["user"]["id"],
            "scheduled_start": _iso(overlap_start),
            "scheduled_end": _iso(overlap_end),
            "room_id": room["id"],
        },
        headers=ctx["headers"],
    )
    assert conflicting.status_code == 409

    non_overlapping = client.post(
        "/v1/appointments",
        json={
            "patient_id": patient_b["id"],
            "professional_id": ctx["user"]["id"],
            "scheduled_start": _iso(end),
            "scheduled_end": _iso(end + datetime.timedelta(minutes=50)),
            "room_id": room["id"],
        },
        headers=ctx["headers"],
    )
    assert non_overlapping.status_code == 201


def test_room_from_other_tenant_rejected(client):
    clinic_a = register_clinic(client, "Clinica A")
    clinic_b = register_clinic(client, "Clinica B")
    patient_b = create_patient(client, clinic_b["headers"])
    room_a = client.post("/v1/rooms", json={"name": "Sala A"}, headers=clinic_a["headers"]).json()

    start = datetime.datetime(2026, 9, 3, 10, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=50)
    response = client.post(
        "/v1/appointments",
        json={
            "patient_id": patient_b["id"],
            "professional_id": clinic_b["user"]["id"],
            "scheduled_start": _iso(start),
            "scheduled_end": _iso(end),
            "room_id": room_a["id"],
        },
        headers=clinic_b["headers"],
    )
    assert response.status_code == 404
