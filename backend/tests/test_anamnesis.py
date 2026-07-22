from tests.conftest import assign_professional, create_patient, invite_and_accept, register_clinic


def test_save_anamnesis_creates_then_updates(client):
    """RF-21 — cria na primeira vez, edita depois sem duplicar registros."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    first = client.put(
        f"/v1/patients/{patient['id']}/anamnesis",
        json={"chief_complaint": "Atraso de linguagem", "birth_history": "Parto a termo, sem intercorrências"},
        headers=ctx["headers"],
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["chief_complaint"] == "Atraso de linguagem"

    second = client.put(
        f"/v1/patients/{patient['id']}/anamnesis",
        json={"chief_complaint": "Atraso de linguagem e comunicação social", "family_history": "Tio paterno com TEA"},
        headers=ctx["headers"],
    )
    assert second.status_code == 200, second.text
    assert second.json()["id"] == body["id"]
    assert second.json()["chief_complaint"] == "Atraso de linguagem e comunicação social"
    assert second.json()["family_history"] == "Tio paterno com TEA"

    logs = client.get("/v1/audit-logs?entity_type=anamnesis", headers=ctx["headers"])
    actions = [entry["action"] for entry in logs.json()]
    assert actions.count("anamnesis_created") == 1
    assert actions.count("anamnesis_updated") == 1


def test_anamnesis_appears_in_timeline_as_single_founding_event(client):
    """RF-21 — critério de aceite: citada na timeline como evento fundacional."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    client.put(f"/v1/patients/{patient['id']}/anamnesis", json={"chief_complaint": "X"}, headers=ctx["headers"])
    client.put(f"/v1/patients/{patient['id']}/anamnesis", json={"chief_complaint": "Y"}, headers=ctx["headers"])

    timeline = client.get(f"/v1/patients/{patient['id']}/timeline", headers=ctx["headers"])
    entries = [e for e in timeline.json() if e["event_type"] == "anamnesis_registered"]
    assert len(entries) == 1


def test_at_cannot_access_anamnesis(client):
    """RF-21 — "acessível a quem tem permissão de leitura de dados clínicos completos" — bloqueia o AT."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    client.put(f"/v1/patients/{patient['id']}/anamnesis", json={"chief_complaint": "X"}, headers=ctx["headers"])

    at = invite_and_accept(client, ctx["headers"], role="at")
    response = client.get(f"/v1/patients/{patient['id']}/anamnesis", headers=at["headers"])
    assert response.status_code == 403


def test_professional_can_access_anamnesis(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    client.put(f"/v1/patients/{patient['id']}/anamnesis", json={"chief_complaint": "X"}, headers=ctx["headers"])

    professional = invite_and_accept(client, ctx["headers"], role="professional")
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"])
    response = client.get(f"/v1/patients/{patient['id']}/anamnesis", headers=professional["headers"])
    assert response.status_code == 200


def test_anamnesis_isolated_by_tenant(client):
    clinic_a = register_clinic(client, "Clinica Anamnese A")
    clinic_b = register_clinic(client, "Clinica Anamnese B")
    patient_a = create_patient(client, clinic_a["headers"], name="Paciente Anamnese A")

    forbidden = client.put(
        f"/v1/patients/{patient_a['id']}/anamnesis", json={"chief_complaint": "X"}, headers=clinic_b["headers"]
    )
    assert forbidden.status_code == 404
