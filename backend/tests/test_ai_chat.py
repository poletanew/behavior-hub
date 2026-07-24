from tests.conftest import register_clinic


def test_chat_fails_gracefully_when_not_configured(client):
    ctx = register_clinic(client)
    response = client.post(
        "/v1/ai/chat",
        json={"messages": [{"role": "user", "content": "Olá"}]},
        headers=ctx["headers"],
    )
    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


def test_chat_requires_authentication(client):
    response = client.post("/v1/ai/chat", json={"messages": [{"role": "user", "content": "Olá"}]})
    assert response.status_code == 401
