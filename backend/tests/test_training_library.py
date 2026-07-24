from tests.conftest import create_patient, create_training, create_training_category, register_clinic, register_individual


def test_list_categories_and_trainings(client, db_session):
    category = create_training_category(db_session, name="Comunicação")
    create_training(db_session, category, title="Mando por item preferido")

    ctx = register_clinic(client)
    categories = client.get("/v1/training-categories", headers=ctx["headers"])
    assert any(c["id"] == str(category.id) for c in categories.json())

    trainings = client.get(f"/v1/trainings?category_id={category.id}", headers=ctx["headers"])
    assert len(trainings.json()) == 1
    assert trainings.json()[0]["title"] == "Mando por item preferido"


def test_search_trainings_by_title(client, db_session):
    category = create_training_category(db_session)
    create_training(db_session, category, title="Aguardar por 30 segundos")
    create_training(db_session, category, title="Nomear objetos comuns")

    ctx = register_clinic(client)
    response = client.get("/v1/trainings?search=aguardar", headers=ctx["headers"])
    titles = [t["title"] for t in response.json()]
    assert titles == ["Aguardar por 30 segundos"]


def test_system_training_cannot_be_deleted(client, db_session):
    """Seção 12.1 — treinos de sistema sao protegidos contra exclusao."""
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    ctx = register_clinic(client)
    response = client.delete(f"/v1/trainings/{training.id}", headers=ctx["headers"])
    assert response.status_code == 403


def test_custom_training_creation_and_deletion(client, db_session):
    category = create_training_category(db_session)
    ctx = register_clinic(client)

    create_response = client.post(
        "/v1/trainings",
        json={
            "category_id": str(category.id),
            "title": "Treino personalizado da clinica",
            "objective": "Objetivo customizado",
        },
        headers=ctx["headers"],
    )
    assert create_response.status_code == 201
    training_id = create_response.json()["id"]
    assert create_response.json()["visibility"] == "clinic_shared"

    delete_response = client.delete(f"/v1/trainings/{training_id}", headers=ctx["headers"])
    assert delete_response.status_code == 204


def test_ai_fill_training_fails_gracefully_when_not_configured(client, db_session):
    """Seção 12.1 — "Preencher com IA" no Novo Treinamento: sem ANTHROPIC_API_KEY
    configurada, retorna erro claro em vez de simular uma resposta."""
    category = create_training_category(db_session)
    ctx = register_clinic(client)

    response = client.post(
        "/v1/trainings/ai-fill",
        json={"category_id": str(category.id), "title": "Aguardar por 30 segundos"},
        headers=ctx["headers"],
    )
    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


def test_ai_generated_training_can_be_created(client, db_session):
    """O rascunho da IA fica editável e o profissional decide se salva com o
    flag ai_generated marcado (mesmo padrão de Objective/Resource)."""
    category = create_training_category(db_session)
    ctx = register_clinic(client)

    response = client.post(
        "/v1/trainings",
        json={
            "category_id": str(category.id),
            "title": "Treino gerado com IA",
            "objective": "Objetivo sugerido pela IA",
            "ai_generated": True,
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 201
    assert response.json()["ai_generated"] is True


def test_link_training_to_patient_shows_as_prescribed(client, db_session):
    """Addendum v2.1, RF-10 — vincular treino cria treino "prescrito" pro paciente."""
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    response = client.post(
        f"/v1/trainings/{training.id}/link", json={"patient_id": patient["id"]}, headers=ctx["headers"]
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "prescribed"
    assert body["training_title"] == training.title

    links = client.get(f"/v1/patients/{patient['id']}/training-links", headers=ctx["headers"])
    assert links.status_code == 200
    assert len(links.json()) == 1
    assert links.json()[0]["status"] == "prescribed"


def test_link_training_to_patient_is_idempotent_per_pair(client, db_session):
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    first = client.post(f"/v1/trainings/{training.id}/link", json={"patient_id": patient["id"]}, headers=ctx["headers"])
    assert first.status_code == 201

    duplicate = client.post(f"/v1/trainings/{training.id}/link", json={"patient_id": patient["id"]}, headers=ctx["headers"])
    assert duplicate.status_code == 409


def test_unlink_training_from_patient(client, db_session):
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    link = client.post(
        f"/v1/trainings/{training.id}/link", json={"patient_id": patient["id"]}, headers=ctx["headers"]
    ).json()

    response = client.delete(f"/v1/training-patient-links/{link['id']}", headers=ctx["headers"])
    assert response.status_code == 204

    links = client.get(f"/v1/patients/{patient['id']}/training-links", headers=ctx["headers"])
    assert links.json() == []


def test_link_status_becomes_applied_after_first_session_using_it(client, db_session):
    """A sessão que de fato usa o treino prescrito muda o status pra "aplicado"."""
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    client.post(f"/v1/trainings/{training.id}/link", json={"patient_id": patient["id"]}, headers=ctx["headers"])

    session_response = client.post(
        "/v1/sessions",
        json={
            "patient_id": patient["id"],
            "professional_id": ctx["user"]["id"],
            "occurred_at": "2026-07-21T10:00:00Z",
            "training_ids": [str(training.id)],
        },
        headers=ctx["headers"],
    )
    assert session_response.status_code == 201, session_response.text

    links = client.get(f"/v1/patients/{patient['id']}/training-links", headers=ctx["headers"])
    assert links.json()[0]["status"] == "applied"


def test_cannot_link_training_to_patient_from_another_tenant(client, db_session):
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    ctx_a = register_clinic(client, clinic_name="Clinica A Link")
    ctx_b = register_clinic(client, clinic_name="Clinica B Link")
    patient_b = create_patient(client, ctx_b["headers"])

    response = client.post(
        f"/v1/trainings/{training.id}/link", json={"patient_id": patient_b["id"]}, headers=ctx_a["headers"]
    )
    assert response.status_code == 404


def test_individual_tenant_can_link_training_to_own_patient(client, db_session):
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    ctx = register_individual(client)
    patient = create_patient(client, ctx["headers"])

    response = client.post(
        f"/v1/trainings/{training.id}/link", json={"patient_id": patient["id"]}, headers=ctx["headers"]
    )
    assert response.status_code == 201
