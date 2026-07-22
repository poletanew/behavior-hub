from tests.conftest import create_patient, create_training, create_training_category, register_clinic


def _create_session(client, headers, patient_id, professional_id, db_session):
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    response = client.post(
        "/v1/sessions",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "occurred_at": "2026-07-14T10:00:00Z",
            "training_ids": [str(training.id)],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_reinforcer_for_patient(client):
    """RF-19 — cadastro de reforçador por paciente."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    response = client.post(
        f"/v1/patients/{patient['id']}/reinforcers",
        json={"name": "Tempo de tela (tablet)", "effectiveness_notes": "Funciona bem após tarefas difíceis"},
        headers=ctx["headers"],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Tempo de tela (tablet)"
    assert body["usage_count"] == 0


def test_link_reinforcer_to_session_and_see_usage_count(client, db_session):
    """RF-19 — critério de aceite: vincular a uma sessão e ver quais foram mais usados."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    session = _create_session(client, ctx["headers"], patient["id"], ctx["user"]["id"], db_session)

    reinforcer = client.post(
        f"/v1/patients/{patient['id']}/reinforcers",
        json={"name": "Elogio verbal"},
        headers=ctx["headers"],
    ).json()

    link_response = client.post(
        f"/v1/sessions/{session['id']}/reinforcers",
        json={"reinforcer_id": reinforcer["id"], "effectiveness_note": "Muito eficaz"},
        headers=ctx["headers"],
    )
    assert link_response.status_code == 201, link_response.text
    assert link_response.json()["reinforcer_name"] == "Elogio verbal"

    session_reinforcers = client.get(f"/v1/sessions/{session['id']}/reinforcers", headers=ctx["headers"])
    assert len(session_reinforcers.json()) == 1

    reinforcers = client.get(f"/v1/patients/{patient['id']}/reinforcers", headers=ctx["headers"])
    body = next(r for r in reinforcers.json() if r["id"] == reinforcer["id"])
    assert body["usage_count"] == 1


def test_link_reinforcer_rejects_mismatched_patient(client, db_session):
    ctx = register_clinic(client)
    patient_a = create_patient(client, ctx["headers"], name="Paciente A")
    patient_b = create_patient(client, ctx["headers"], name="Paciente B")
    session_b = _create_session(client, ctx["headers"], patient_b["id"], ctx["user"]["id"], db_session)

    reinforcer_a = client.post(
        f"/v1/patients/{patient_a['id']}/reinforcers", json={"name": "Bolha de sabão"}, headers=ctx["headers"]
    ).json()

    response = client.post(
        f"/v1/sessions/{session_b['id']}/reinforcers",
        json={"reinforcer_id": reinforcer_a["id"]},
        headers=ctx["headers"],
    )
    assert response.status_code == 400


def test_reinforcers_isolated_by_tenant(client):
    clinic_a = register_clinic(client, "Clinica Reforcador A")
    clinic_b = register_clinic(client, "Clinica Reforcador B")
    patient_a = create_patient(client, clinic_a["headers"], name="Paciente Reforcador A")

    forbidden = client.post(
        f"/v1/patients/{patient_a['id']}/reinforcers", json={"name": "X"}, headers=clinic_b["headers"]
    )
    assert forbidden.status_code == 404
