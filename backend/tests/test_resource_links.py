from tests.conftest import (
    create_patient,
    create_training,
    create_training_category,
    invite_and_accept_professional,
    register_clinic,
)


def _upload_pdf(client, headers, title="Historia social", visibility="clinic_shared"):
    response = client.post(
        "/v1/resources",
        data={"title": title, "category": "espera", "visibility": visibility},
        files={"file": ("atividade.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_objective_with_training(client, headers, patient_id, training_id, **overrides):
    payload = {"area": "aba", "title": "Objetivo Biblioteca", "training_ids": [str(training_id)]}
    payload.update(overrides)
    response = client.post(f"/v1/patients/{patient_id}/treatment-plan/objectives", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_link_to_training(client, mock_s3, db_session):
    ctx = register_clinic(client)
    resource = _upload_pdf(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    response = client.post(
        "/v1/resource-links",
        json={"resource_id": resource["id"], "training_id": str(training.id), "relevance_score": 5},
        headers=ctx["headers"],
    )
    assert response.status_code == 201, response.text
    assert response.json()["relevance_score"] == 5

    listed = client.get(f"/v1/trainings/{training.id}/resource-links", headers=ctx["headers"]).json()
    assert len(listed) == 1
    assert listed[0]["resource_title"] == resource["title"]


def test_create_link_to_objective(client, mock_s3, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)
    resource = _upload_pdf(client, ctx["headers"])

    response = client.post(
        "/v1/resource-links",
        json={"resource_id": resource["id"], "objective_id": objective["id"]},
        headers=ctx["headers"],
    )
    assert response.status_code == 201, response.text

    listed = client.get(f"/v1/objectives/{objective['id']}/resource-links", headers=ctx["headers"]).json()
    assert len(listed) == 1
    assert listed[0]["objective_id"] == objective["id"]


def test_objective_recommendations_aggregate_via_linked_training(client, mock_s3, db_session):
    """Seção 29.7 — um recurso tagueado no treino do objetivo também é
    recomendado para o objetivo, sem precisar de um vínculo direto."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)
    resource = _upload_pdf(client, ctx["headers"])

    client.post(
        "/v1/resource-links",
        json={"resource_id": resource["id"], "training_id": str(training.id)},
        headers=ctx["headers"],
    )

    listed = client.get(f"/v1/objectives/{objective['id']}/resource-links", headers=ctx["headers"]).json()
    assert len(listed) == 1
    assert listed[0]["training_id"] == str(training.id)


def test_duplicate_link_conflicts(client, mock_s3, db_session):
    ctx = register_clinic(client)
    resource = _upload_pdf(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    payload = {"resource_id": resource["id"], "training_id": str(training.id)}
    first = client.post("/v1/resource-links", json=payload, headers=ctx["headers"])
    assert first.status_code == 201

    second = client.post("/v1/resource-links", json=payload, headers=ctx["headers"])
    assert second.status_code == 409


def test_link_requires_exactly_one_target(client, mock_s3, db_session):
    ctx = register_clinic(client)
    resource = _upload_pdf(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    patient = create_patient(client, ctx["headers"])
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    neither = client.post("/v1/resource-links", json={"resource_id": resource["id"]}, headers=ctx["headers"])
    assert neither.status_code == 422

    both = client.post(
        "/v1/resource-links",
        json={"resource_id": resource["id"], "training_id": str(training.id), "objective_id": objective["id"]},
        headers=ctx["headers"],
    )
    assert both.status_code == 422


def test_link_relevance_score_bounds(client, mock_s3, db_session):
    ctx = register_clinic(client)
    resource = _upload_pdf(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    too_low = client.post(
        "/v1/resource-links",
        json={"resource_id": resource["id"], "training_id": str(training.id), "relevance_score": 0},
        headers=ctx["headers"],
    )
    assert too_low.status_code == 422

    too_high = client.post(
        "/v1/resource-links",
        json={"resource_id": resource["id"], "training_id": str(training.id), "relevance_score": 6},
        headers=ctx["headers"],
    )
    assert too_high.status_code == 422


def test_delete_link_permission(client, mock_s3, db_session):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])
    resource = _upload_pdf(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    link = client.post(
        "/v1/resource-links",
        json={"resource_id": resource["id"], "training_id": str(training.id)},
        headers=ctx["headers"],
    ).json()

    forbidden = client.delete(f"/v1/resource-links/{link['id']}", headers=professional["headers"])
    assert forbidden.status_code == 403

    allowed = client.delete(f"/v1/resource-links/{link['id']}", headers=ctx["headers"])
    assert allowed.status_code == 204


def test_private_resource_link_hidden_from_other_professional(client, mock_s3, db_session):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])
    resource = _upload_pdf(client, ctx["headers"], visibility="private")
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    client.post(
        "/v1/resource-links",
        json={"resource_id": resource["id"], "training_id": str(training.id)},
        headers=ctx["headers"],
    )

    hidden = client.get(f"/v1/trainings/{training.id}/resource-links", headers=professional["headers"]).json()
    assert hidden == []

    visible = client.get(f"/v1/trainings/{training.id}/resource-links", headers=ctx["headers"]).json()
    assert len(visible) == 1


def test_resource_links_tenant_isolation(client, mock_s3, db_session):
    clinic_a = register_clinic(client, "Clinica Biblioteca A")
    clinic_b = register_clinic(client, "Clinica Biblioteca B")
    resource_a = _upload_pdf(client, clinic_a["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    link = client.post(
        "/v1/resource-links",
        json={"resource_id": resource_a["id"], "training_id": str(training.id)},
        headers=clinic_a["headers"],
    )
    assert link.status_code == 201

    forbidden = client.post(
        "/v1/resource-links",
        json={"resource_id": resource_a["id"], "training_id": str(training.id), "relevance_score": 2},
        headers=clinic_b["headers"],
    )
    assert forbidden.status_code == 404
