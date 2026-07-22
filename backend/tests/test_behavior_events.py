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


def test_create_behavior_event_independent_of_trials(client, db_session):
    """RF-18 — registrar um evento ABC independente das tentativas de treino."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    session = _create_session(client, ctx["headers"], patient["id"], ctx["user"]["id"], db_session)

    response = client.post(
        f"/v1/patients/{patient['id']}/behavior-events",
        json={
            "session_id": session["id"],
            "antecedent": "Pediram para guardar o brinquedo",
            "behavior": "Gritou e jogou o brinquedo no chão",
            "consequence": "Terapeuta ofereceu escolha entre dois brinquedos",
            "frequency_count": 2,
            "duration_seconds": 45,
            "intensity": "media",
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["patient_id"] == patient["id"]
    assert body["session_id"] == session["id"]
    assert body["intensity"] == "media"
    assert body["duration_seconds"] == 45


def test_behavior_event_appears_in_patient_timeline(client, db_session):
    """RF-18 — critério de aceite: aparece na timeline clínica do paciente (Seção 29.2)."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    session = _create_session(client, ctx["headers"], patient["id"], ctx["user"]["id"], db_session)

    client.post(
        f"/v1/patients/{patient['id']}/behavior-events",
        json={
            "session_id": session["id"],
            "antecedent": "Transição de atividade",
            "behavior": "Recusou-se a sair da sala",
            "consequence": "Contagem regressiva visual foi usada",
            "intensity": "baixa",
        },
        headers=ctx["headers"],
    )

    timeline = client.get(f"/v1/patients/{patient['id']}/timeline", headers=ctx["headers"])
    assert timeline.status_code == 200
    event_types = [e["event_type"] for e in timeline.json()]
    assert "behavior_event_recorded" in event_types


def test_list_behavior_events_by_session(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    session = _create_session(client, ctx["headers"], patient["id"], ctx["user"]["id"], db_session)

    client.post(
        f"/v1/patients/{patient['id']}/behavior-events",
        json={
            "session_id": session["id"],
            "antecedent": "A",
            "behavior": "B",
            "consequence": "C",
        },
        headers=ctx["headers"],
    )

    response = client.get(f"/v1/sessions/{session['id']}/behavior-events", headers=ctx["headers"])
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_behavior_event_rejects_session_from_another_patient(client, db_session):
    ctx = register_clinic(client)
    patient_a = create_patient(client, ctx["headers"], name="Paciente A")
    patient_b = create_patient(client, ctx["headers"], name="Paciente B")
    session_b = _create_session(client, ctx["headers"], patient_b["id"], ctx["user"]["id"], db_session)

    response = client.post(
        f"/v1/patients/{patient_a['id']}/behavior-events",
        json={"session_id": session_b["id"], "antecedent": "A", "behavior": "B", "consequence": "C"},
        headers=ctx["headers"],
    )
    assert response.status_code == 400


def test_behavior_events_isolated_by_tenant(client, db_session):
    clinic_a = register_clinic(client, "Clinica Behavior A")
    clinic_b = register_clinic(client, "Clinica Behavior B")
    patient_a = create_patient(client, clinic_a["headers"], name="Paciente Behavior A")
    session_a = _create_session(client, clinic_a["headers"], patient_a["id"], clinic_a["user"]["id"], db_session)

    forbidden = client.post(
        f"/v1/patients/{patient_a['id']}/behavior-events",
        json={"session_id": session_a["id"], "antecedent": "A", "behavior": "B", "consequence": "C"},
        headers=clinic_b["headers"],
    )
    assert forbidden.status_code == 404
