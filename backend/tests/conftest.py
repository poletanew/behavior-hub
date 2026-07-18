import os
import uuid

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://behavior_hub:behavior_hub@localhost:5432/behavior_hub_test",
)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import *  # noqa: F401,F403 register all models on Base.metadata

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
TestSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _prepare_database():
    Base.metadata.drop_all(engine)
    with engine.begin() as connection:
        # Seção 13.2 — pg_trgm é usado para similaridade de trigramas na detecção
        # de objetivos duplicados; a migração real já cria isso em produção.
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session():
    connection = engine.connect()
    trans = connection.begin()
    session = TestSessionLocal(bind=connection)

    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, transaction):
        if transaction.nested and not transaction._parent.nested:
            sess.begin_nested()

    yield session

    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def register_clinic(client, clinic_name: str = "Clinica Teste") -> dict:
    email = unique_email("admin")
    response = client.post(
        "/v1/auth/register/clinic",
        json={
            "clinic_name": clinic_name,
            "admin_name": "Admin Teste",
            "email": email,
            "password": "senha-super-segura-123",
            "accept_terms": True,
        },
    )
    assert response.status_code == 201, response.text
    user = response.json()
    login_response = client.post("/v1/auth/login", json={"email": email, "password": "senha-super-segura-123"})
    assert login_response.status_code == 200, login_response.text
    tokens = login_response.json()
    return {"user": user, "tokens": tokens, "email": email, "headers": auth_headers(tokens)}


def register_individual(client) -> dict:
    email = unique_email("individual")
    response = client.post(
        "/v1/auth/register/individual",
        json={
            "name": "Profissional Individual",
            "email": email,
            "password": "senha-super-segura-123",
            "specialty": "psicologo_infantil",
            "accept_terms": True,
        },
    )
    assert response.status_code == 201, response.text
    user = response.json()
    login_response = client.post("/v1/auth/login", json={"email": email, "password": "senha-super-segura-123"})
    tokens = login_response.json()
    return {"user": user, "tokens": tokens, "email": email, "headers": auth_headers(tokens)}


def auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def create_training_category(db_session, name: str = "Comunicação"):
    from app.models.training import TrainingCategory

    category = TrainingCategory(name=f"{name}-{uuid.uuid4().hex[:6]}", description="Categoria de teste")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


def create_training(db_session, category, title: str = "Aguardar por 30 segundos"):
    from app.models.enums import TrainingVisibility
    from app.models.training import Training

    training = Training(
        category_id=category.id,
        title=title,
        objective="Objetivo de teste",
        visibility=TrainingVisibility.SYSTEM,
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)
    return training


def create_patient(client, headers, name: str = "Paciente Exemplo") -> dict:
    response = client.post("/v1/patients", json={"name": name, "birth_date": "2018-05-10"}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def assign_professional(client, admin_headers, patient_id, professional_id, permission="edit_sessions"):
    response = client.post(
        f"/v1/patients/{patient_id}/assignments",
        json={"professional_id": professional_id, "permission": permission},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def mock_s3():
    """moto intercepts requests to standard AWS endpoints, not custom ones like
    MinIO's http://localhost:9000, so this fixture temporarily clears the
    endpoint_url override while the mock is active."""
    from moto import mock_aws

    from app.services import file_service

    original_endpoint = file_service.settings.S3_ENDPOINT_URL
    file_service.settings.S3_ENDPOINT_URL = None
    file_service._client = None
    with mock_aws():
        yield
    file_service.settings.S3_ENDPOINT_URL = original_endpoint
    file_service._client = None


def invite_and_accept_professional(client, admin_headers: dict, specialty: str = "fonoaudiologo") -> dict:
    email = unique_email("professional")
    invite_response = client.post(
        "/v1/invitations", json={"email": email, "specialty": specialty}, headers=admin_headers
    )
    assert invite_response.status_code == 201, invite_response.text
    raw_token = invite_response.json()["raw_token"]

    accept_response = client.post(
        f"/v1/invitations/{raw_token}/accept",
        json={"name": "Profissional Convidado", "password": "senha-super-segura-123", "accept_terms": True},
    )
    assert accept_response.status_code == 201, accept_response.text
    user = accept_response.json()

    login_response = client.post("/v1/auth/login", json={"email": email, "password": "senha-super-segura-123"})
    tokens = login_response.json()
    return {"user": user, "tokens": tokens, "email": email, "headers": auth_headers(tokens)}
