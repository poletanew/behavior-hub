from tests.conftest import create_training, create_training_category, register_clinic


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
