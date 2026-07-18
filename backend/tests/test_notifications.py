from tests.conftest import assign_professional, create_patient, invite_and_accept_professional, register_clinic


def _create_objective(client, headers, patient_id, **overrides):
    payload = {"area": "aba", "title": "Objetivo de teste"}
    payload.update(overrides)
    return client.post(f"/v1/patients/{patient_id}/treatment-plan/objectives", json=payload, headers=headers).json()


def test_comment_notifies_objective_author(client):
    """Seção 32.6 — comentários novos em objetivos do plano de tratamento notificam o autor."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    professional = invite_and_accept_professional(client, ctx["headers"])
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"], permission="full_access")

    objective = _create_objective(client, ctx["headers"], patient["id"])

    comment_response = client.post(
        f"/v1/objectives/{objective['id']}/comments", json={"body": "Comentário do profissional"}, headers=professional["headers"]
    )
    assert comment_response.status_code == 201

    notifications = client.get("/v1/notifications", headers=ctx["headers"])
    assert len(notifications.json()) == 1
    assert notifications.json()[0]["type"] == "comment"
    assert notifications.json()[0]["entity_id"] == objective["id"]


def test_self_comment_does_not_notify_self(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    objective = _create_objective(client, ctx["headers"], patient["id"])

    client.post(f"/v1/objectives/{objective['id']}/comments", json={"body": "Nota pessoal"}, headers=ctx["headers"])

    notifications = client.get("/v1/notifications", headers=ctx["headers"])
    assert notifications.json() == []


def test_mention_notifies_mentioned_professional(client):
    """Seção 32.13 — menção (@) dispara notificação direta ao profissional marcado."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    professional = invite_and_accept_professional(client, ctx["headers"])
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"])
    objective = _create_objective(client, ctx["headers"], patient["id"])

    client.post(
        f"/v1/objectives/{objective['id']}/comments",
        json={"body": "cc @colega", "mentioned_user_id": professional["user"]["id"]},
        headers=ctx["headers"],
    )

    notifications = client.get("/v1/notifications", headers=professional["headers"])
    types = [n["type"] for n in notifications.json()]
    assert "mention" in types


def test_mentioning_user_outside_tenant_is_ignored(client):
    """Nunca notificar alguém fora do tenant, mesmo que o id seja adivinhado."""
    clinic_a = register_clinic(client, "Clinica A")
    clinic_b = register_clinic(client, "Clinica B")
    patient = create_patient(client, clinic_a["headers"])
    objective = _create_objective(client, clinic_a["headers"], patient["id"])

    response = client.post(
        f"/v1/objectives/{objective['id']}/comments",
        json={"body": "tentativa de mencao cruzada", "mentioned_user_id": clinic_b["user"]["id"]},
        headers=clinic_a["headers"],
    )
    assert response.status_code == 201

    cross_tenant_notifications = client.get("/v1/notifications", headers=clinic_b["headers"])
    assert cross_tenant_notifications.json() == []


def test_mark_read_and_mark_all_read(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    professional = invite_and_accept_professional(client, ctx["headers"])
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"], permission="full_access")
    objective = _create_objective(client, ctx["headers"], patient["id"])

    client.post(
        f"/v1/objectives/{objective['id']}/comments", json={"body": "primeiro"}, headers=professional["headers"]
    )
    client.post(
        f"/v1/objectives/{objective['id']}/comments", json={"body": "segundo"}, headers=professional["headers"]
    )

    unread = client.get("/v1/notifications?unread_only=true", headers=ctx["headers"])
    assert len(unread.json()) == 2

    first_id = unread.json()[0]["id"]
    read_response = client.post(f"/v1/notifications/{first_id}/read", headers=ctx["headers"])
    assert read_response.status_code == 200
    assert read_response.json()["read_at"] is not None

    still_unread = client.get("/v1/notifications?unread_only=true", headers=ctx["headers"])
    assert len(still_unread.json()) == 1

    mark_all = client.post("/v1/notifications/read-all", headers=ctx["headers"])
    assert mark_all.json()["marked_read"] == 1

    none_unread = client.get("/v1/notifications?unread_only=true", headers=ctx["headers"])
    assert none_unread.json() == []


def test_cannot_mark_another_users_notification_as_read(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    professional = invite_and_accept_professional(client, ctx["headers"])
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"], permission="full_access")
    objective = _create_objective(client, ctx["headers"], patient["id"])

    client.post(f"/v1/objectives/{objective['id']}/comments", json={"body": "oi"}, headers=professional["headers"])
    notification_id = client.get("/v1/notifications", headers=ctx["headers"]).json()[0]["id"]

    forbidden = client.post(f"/v1/notifications/{notification_id}/read", headers=professional["headers"])
    assert forbidden.status_code == 404
