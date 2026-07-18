from tests.conftest import create_training, create_training_category, register_clinic


def test_dashboard_widget_empty_then_populated_on_session_creation(client, db_session):
    """AC-12 — sem sessoes o widget fica vazio; ao criar sessao, ela aparece."""
    ctx = register_clinic(client)

    empty_dashboard = client.get("/v1/dashboard", headers=ctx["headers"])
    assert empty_dashboard.json()["recent_sessions"] == []

    patient_response = client.post(
        "/v1/patients", json={"name": "Paciente Dashboard", "birth_date": "2018-05-10"}, headers=ctx["headers"]
    )
    patient = patient_response.json()
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    session_response = client.post(
        "/v1/sessions",
        json={
            "patient_id": patient["id"],
            "professional_id": ctx["user"]["id"],
            "occurred_at": "2026-07-14T10:00:00Z",
            "training_ids": [str(training.id)],
        },
        headers=ctx["headers"],
    )
    assert session_response.status_code == 201

    populated_dashboard = client.get("/v1/dashboard", headers=ctx["headers"])
    body = populated_dashboard.json()
    assert body["active_patients_count"] == 1
    assert len(body["recent_sessions"]) == 1
    assert body["recent_sessions"][0]["id"] == session_response.json()["id"]
