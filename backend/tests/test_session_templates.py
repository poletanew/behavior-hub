from tests.conftest import create_patient, create_training, create_training_category, register_clinic


def _create_session(client, headers, patient_id, professional_id, training_id, occurred_at="2026-07-10T10:00:00Z"):
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


def test_save_session_as_template_and_list(client, db_session):
    """Seção 32.4 — salvar um modelo de atendimento a partir de uma sessão existente."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = _create_session(client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id))

    template_response = client.post(
        f"/v1/sessions/{session['id']}/save-as-template", json={"name": "Rotina padrão"}, headers=ctx["headers"]
    )
    assert template_response.status_code == 201
    template = template_response.json()
    assert template["patient_id"] == patient["id"]
    assert len(template["trainings"]) == 1
    assert template["trainings"][0]["training_id"] == str(training.id)

    listing = client.get(f"/v1/session-templates?patient_id={patient['id']}", headers=ctx["headers"])
    assert len(listing.json()) == 1


def test_create_session_from_template(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = _create_session(client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id))
    template = client.post(
        f"/v1/sessions/{session['id']}/save-as-template", json={"name": "Rotina"}, headers=ctx["headers"]
    ).json()

    new_session = client.post(
        f"/v1/sessions/from-template/{template['id']}",
        json={
            "patient_id": patient["id"],
            "professional_id": ctx["user"]["id"],
            "occurred_at": "2026-07-17T10:00:00Z",
        },
        headers=ctx["headers"],
    )
    assert new_session.status_code == 201
    assert len(new_session.json()["trainings"]) == 1
    assert new_session.json()["trainings"][0]["training_id"] == str(training.id)


def test_patient_specific_template_cannot_be_used_for_another_patient(client, db_session):
    ctx = register_clinic(client)
    patient_a = create_patient(client, ctx["headers"], name="Paciente A")
    patient_b = create_patient(client, ctx["headers"], name="Paciente B")
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = _create_session(client, ctx["headers"], patient_a["id"], ctx["user"]["id"], str(training.id))
    template = client.post(
        f"/v1/sessions/{session['id']}/save-as-template", json={"name": "Rotina A"}, headers=ctx["headers"]
    ).json()

    response = client.post(
        f"/v1/sessions/from-template/{template['id']}",
        json={
            "patient_id": patient_b["id"],
            "professional_id": ctx["user"]["id"],
            "occurred_at": "2026-07-17T10:00:00Z",
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 400


def test_generic_clinic_template_usable_for_any_patient(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    generic_template = client.post(
        "/v1/session-templates",
        json={"name": "Modelo genérico", "training_ids": [str(training.id)]},
        headers=ctx["headers"],
    )
    assert generic_template.status_code == 201
    template_id = generic_template.json()["id"]

    new_session = client.post(
        f"/v1/sessions/from-template/{template_id}",
        json={
            "patient_id": patient["id"],
            "professional_id": ctx["user"]["id"],
            "occurred_at": "2026-07-17T10:00:00Z",
        },
        headers=ctx["headers"],
    )
    assert new_session.status_code == 201


def test_duplicate_session_copies_trainings_for_new_date(client, db_session):
    """Seção 32.4 — duplicar a sessão anterior do mesmo paciente como ponto de partida."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = _create_session(client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id))

    duplicate = client.post(
        f"/v1/sessions/{session['id']}/duplicate", json={"occurred_at": "2026-07-18T10:00:00Z"}, headers=ctx["headers"]
    )
    assert duplicate.status_code == 201
    body = duplicate.json()
    assert body["id"] != session["id"]
    assert body["occurred_at"].startswith("2026-07-18")
    assert len(body["trainings"]) == 1
    assert body["trainings"][0]["training_id"] == str(training.id)

    history = client.get(f"/v1/sessions?patient_id={patient['id']}", headers=ctx["headers"])
    assert len(history.json()) == 2


def test_templates_isolated_by_tenant(client, db_session):
    clinic_a = register_clinic(client, "Clinica A")
    clinic_b = register_clinic(client, "Clinica B")
    patient_a = create_patient(client, clinic_a["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = _create_session(client, clinic_a["headers"], patient_a["id"], clinic_a["user"]["id"], str(training.id))
    client.post(f"/v1/sessions/{session['id']}/save-as-template", json={"name": "Rotina"}, headers=clinic_a["headers"])

    listing_b = client.get("/v1/session-templates", headers=clinic_b["headers"])
    assert listing_b.json() == []


def test_delete_template(client, db_session):
    ctx = register_clinic(client)
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    template = client.post(
        "/v1/session-templates", json={"name": "Descartável", "training_ids": [str(training.id)]}, headers=ctx["headers"]
    ).json()

    delete_response = client.delete(f"/v1/session-templates/{template['id']}", headers=ctx["headers"])
    assert delete_response.status_code == 204

    listing = client.get("/v1/session-templates", headers=ctx["headers"])
    assert listing.json() == []
