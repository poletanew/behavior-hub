from tests.conftest import (
    assign_professional,
    create_training,
    create_training_category,
    invite_and_accept,
    invite_and_accept_professional,
    register_clinic,
    register_individual,
)


def _create_patient(client, headers, name="Paciente Exemplo"):
    response = client.post("/v1/patients", json={"name": name, "birth_date": "2018-05-10"}, headers=headers)
    assert response.status_code == 201
    return response.json()


def _create_session_with_training(client, headers, patient_id, professional_id, training_id, occurred_at):
    response = client.post(
        "/v1/sessions",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "occurred_at": occurred_at,
            "training_ids": [training_id],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _add_trials(client, headers, session_training_id, results):
    for result in results:
        response = client.post(
            f"/v1/session-trainings/{session_training_id}/trials",
            json={"result": result, "prompt_level": "independent"},
            headers=headers,
        )
        assert response.status_code == 201, response.text


def test_professional_performance_forbidden_for_professional(client):
    """Addendum v3.0, RF-31 — só admin/supervisor veem o relatório de outro profissional."""
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    response = client.get(
        f"/v1/reports/professionals/{professional['user']['id']}/performance", headers=professional["headers"]
    )
    assert response.status_code == 403


def test_professional_performance_forbidden_for_individual_account(client):
    individual = register_individual(client)
    response = client.get(f"/v1/reports/professionals/{individual['user']['id']}/performance", headers=individual["headers"])
    assert response.status_code == 403


def test_professional_performance_computes_consistency_accuracy_and_variability(client, db_session):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])
    patient = _create_patient(client, ctx["headers"])
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"], permission="edit_sessions")
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    session_a = _create_session_with_training(
        client, professional["headers"], patient["id"], professional["user"]["id"], str(training.id), "2026-07-01T10:00:00Z"
    )
    _add_trials(
        client, professional["headers"], session_a["trainings"][0]["id"], ["correct", "correct", "correct", "correct"]
    )

    session_b = _create_session_with_training(
        client, professional["headers"], patient["id"], professional["user"]["id"], str(training.id), "2026-07-02T10:00:00Z"
    )
    _add_trials(
        client, professional["headers"], session_b["trainings"][0]["id"], ["correct", "correct", "incorrect", "incorrect"]
    )

    response = client.get(
        f"/v1/reports/professionals/{professional['user']['id']}/performance", headers=ctx["headers"]
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sessions_count"] == 2
    assert body["registration_consistency_pct"] == 100.0
    assert body["average_accuracy_pct"] == 75.0
    assert body["procedure_variability_pp"] == 25.0
    assert body["applier_efficiency_label"] == "baixa"


def test_professional_performance_flags_sessions_without_trials(client, db_session):
    """"Consistência de registro" cai quando há sessões sem nenhuma tentativa registrada."""
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])
    patient = _create_patient(client, ctx["headers"])
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"], permission="edit_sessions")
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    session_with_trials = _create_session_with_training(
        client, professional["headers"], patient["id"], professional["user"]["id"], str(training.id), "2026-07-01T10:00:00Z"
    )
    _add_trials(client, professional["headers"], session_with_trials["trainings"][0]["id"], ["correct"])

    _create_session_with_training(
        client, professional["headers"], patient["id"], professional["user"]["id"], str(training.id), "2026-07-02T10:00:00Z"
    )

    response = client.get(
        f"/v1/reports/professionals/{professional['user']['id']}/performance", headers=ctx["headers"]
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sessions_count"] == 2
    assert body["registration_consistency_pct"] == 50.0


def test_supervisor_can_view_professional_performance(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])
    supervisor = invite_and_accept(client, ctx["headers"], role="supervisor")

    response = client.get(
        f"/v1/reports/professionals/{professional['user']['id']}/performance", headers=supervisor["headers"]
    )
    assert response.status_code == 200, response.text
    assert response.json()["sessions_count"] == 0


def test_professional_performance_tenant_isolation(client):
    clinic_a = register_clinic(client, "Clinica A")
    clinic_b = register_clinic(client, "Clinica B")
    professional_b = invite_and_accept_professional(client, clinic_b["headers"])

    response = client.get(
        f"/v1/reports/professionals/{professional_b['user']['id']}/performance", headers=clinic_a["headers"]
    )
    assert response.status_code == 404


def test_professional_performance_export_pdf(client, db_session):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    response = client.get(
        f"/v1/reports/professionals/{professional['user']['id']}/performance/export.pdf", headers=ctx["headers"]
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
