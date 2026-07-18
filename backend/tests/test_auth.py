from tests.conftest import register_clinic, register_individual, unique_email


def test_register_clinic_creates_admin_and_empty_account(client):
    """AC-01 — ao criar conta de clinica, todas as listas devem iniciar com zero dados."""
    ctx = register_clinic(client)
    assert ctx["user"]["user_type"] == "clinic_admin"
    assert ctx["user"]["clinic_id"] is not None

    patients_response = client.get("/v1/patients", headers=ctx["headers"])
    assert patients_response.status_code == 200
    assert patients_response.json() == []

    sessions_response = client.get("/v1/sessions", headers=ctx["headers"])
    assert sessions_response.status_code == 200
    assert sessions_response.json() == []

    dashboard_response = client.get("/v1/dashboard", headers=ctx["headers"])
    assert dashboard_response.status_code == 200
    body = dashboard_response.json()
    assert body["active_patients_count"] == 0
    assert body["sessions_today_count"] == 0
    assert body["recent_sessions"] == []


def test_register_individual_creates_tenant_without_clinic(client):
    """Seção 6.2 — cadastro profissional individual cria tenant sem clinic_id."""
    ctx = register_individual(client)
    assert ctx["user"]["user_type"] == "individual"
    assert ctx["user"]["clinic_id"] is None

    patients_response = client.get("/v1/patients", headers=ctx["headers"])
    assert patients_response.status_code == 200
    assert patients_response.json() == []


def test_duplicate_email_registration_is_rejected(client):
    email = unique_email("dup")
    payload = {
        "clinic_name": "Clinica A",
        "admin_name": "Admin A",
        "email": email,
        "password": "senha-super-segura-123",
        "accept_terms": True,
    }
    first = client.post("/v1/auth/register/clinic", json=payload)
    assert first.status_code == 201

    second = client.post("/v1/auth/register/clinic", json=payload)
    assert second.status_code == 409


def test_login_with_wrong_password_is_rejected(client):
    ctx = register_clinic(client)
    response = client.post("/v1/auth/login", json={"email": ctx["email"], "password": "wrong-password"})
    assert response.status_code == 401


def test_unauthenticated_request_is_rejected(client):
    response = client.get("/v1/patients")
    assert response.status_code == 401


def test_terms_must_be_accepted(client):
    response = client.post(
        "/v1/auth/register/clinic",
        json={
            "clinic_name": "Clinica Sem Termos",
            "admin_name": "Admin",
            "email": unique_email("noterms"),
            "password": "senha-super-segura-123",
            "accept_terms": False,
        },
    )
    assert response.status_code == 422
