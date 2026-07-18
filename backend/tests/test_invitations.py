from tests.conftest import invite_and_accept_professional, register_clinic


def test_invited_professional_is_linked_to_clinic_and_has_no_admin_access(client):
    """AC-09 — profissional convidado entra vinculado e nao ve ProfessionalRegistration
    (aqui: nao consegue criar/listar convites, que e a funcionalidade equivalente)."""
    clinic = register_clinic(client)
    professional = invite_and_accept_professional(client, clinic["headers"])

    assert professional["user"]["clinic_id"] == clinic["user"]["clinic_id"]
    assert professional["user"]["user_type"] == "professional"

    forbidden_create = client.post(
        "/v1/invitations", json={"email": "outra@example.com"}, headers=professional["headers"]
    )
    assert forbidden_create.status_code == 403

    forbidden_list = client.get("/v1/invitations", headers=professional["headers"])
    assert forbidden_list.status_code == 403


def test_invitation_cannot_be_used_twice(client):
    clinic = register_clinic(client)
    invite_response = client.post(
        "/v1/invitations", json={"email": "unique-invite@example.com"}, headers=clinic["headers"]
    )
    raw_token = invite_response.json()["raw_token"]

    first_accept = client.post(
        f"/v1/invitations/{raw_token}/accept",
        json={"name": "Primeiro", "password": "senha-super-segura-123", "accept_terms": True},
    )
    assert first_accept.status_code == 201

    second_accept = client.post(
        f"/v1/invitations/{raw_token}/accept",
        json={"name": "Segundo", "password": "senha-super-segura-123", "accept_terms": True},
    )
    assert second_accept.status_code == 404


def test_revoked_invitation_cannot_be_accepted(client):
    clinic = register_clinic(client)
    invite_response = client.post(
        "/v1/invitations", json={"email": "revoked@example.com"}, headers=clinic["headers"]
    )
    invitation_id = invite_response.json()["id"]
    raw_token = invite_response.json()["raw_token"]

    revoke_response = client.post(f"/v1/invitations/{invitation_id}/revoke", headers=clinic["headers"])
    assert revoke_response.status_code == 200

    accept_response = client.post(
        f"/v1/invitations/{raw_token}/accept",
        json={"name": "Alguem", "password": "senha-super-segura-123", "accept_terms": True},
    )
    assert accept_response.status_code == 404
