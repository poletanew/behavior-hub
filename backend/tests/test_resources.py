from tests.conftest import invite_and_accept_professional, register_clinic, register_individual


def _upload_pdf(client, headers, title="Atividade de espera", visibility="private"):
    return client.post(
        "/v1/resources",
        data={"title": title, "category": "espera", "visibility": visibility},
        files={"file": ("atividade.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        headers=headers,
    )


def test_upload_list_and_view_resource(client, mock_s3):
    ctx = register_clinic(client)
    response = _upload_pdf(client, ctx["headers"], visibility="clinic_shared")
    assert response.status_code == 201, response.text
    resource = response.json()
    assert resource["resource_type"] == "pdf"
    assert resource["visibility"] == "clinic_shared"

    listing = client.get("/v1/resources", headers=ctx["headers"])
    assert len(listing.json()) == 1

    detail = client.get(f"/v1/resources/{resource['id']}", headers=ctx["headers"])
    assert detail.status_code == 200
    assert detail.json()["view_url"].startswith("http")


def test_rejects_unsupported_file_type(client, mock_s3):
    ctx = register_clinic(client)
    response = client.post(
        "/v1/resources",
        data={"title": "Script malicioso"},
        files={"file": ("script.exe", b"MZ...", "application/x-msdownload")},
        headers=ctx["headers"],
    )
    assert response.status_code == 415


def test_private_resource_not_visible_to_other_professional(client, mock_s3):
    """Seção 15 — recursos privados só aparecem para o autor; compartilhados aparecem para a clínica."""
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    private = _upload_pdf(client, ctx["headers"], title="Privado do admin", visibility="private").json()
    shared = _upload_pdf(client, ctx["headers"], title="Compartilhado", visibility="clinic_shared").json()

    listing = client.get("/v1/resources", headers=professional["headers"])
    titles = {r["title"] for r in listing.json()}
    assert titles == {"Compartilhado"}

    forbidden = client.get(f"/v1/resources/{private['id']}", headers=professional["headers"])
    assert forbidden.status_code == 404


def test_resources_isolated_by_tenant(client, mock_s3):
    clinic_a = register_clinic(client, "Clinica A")
    clinic_b = register_clinic(client, "Clinica B")
    resource = _upload_pdf(client, clinic_a["headers"], visibility="clinic_shared").json()

    forbidden = client.get(f"/v1/resources/{resource['id']}", headers=clinic_b["headers"])
    assert forbidden.status_code == 404

    listing_b = client.get("/v1/resources", headers=clinic_b["headers"])
    assert listing_b.json() == []


def test_individual_cannot_share_with_clinic(client, mock_s3):
    ctx = register_individual(client)
    response = _upload_pdf(client, ctx["headers"], visibility="clinic_shared")
    assert response.status_code == 400


def test_soft_delete_and_restore_resource(client, mock_s3):
    ctx = register_clinic(client)
    resource = _upload_pdf(client, ctx["headers"]).json()

    delete_response = client.delete(f"/v1/resources/{resource['id']}", headers=ctx["headers"])
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_at"] is not None

    listing = client.get("/v1/resources", headers=ctx["headers"])
    assert listing.json() == []

    restore_response = client.post(f"/v1/resources/{resource['id']}/restore", headers=ctx["headers"])
    assert restore_response.status_code == 200

    listing_after = client.get("/v1/resources", headers=ctx["headers"])
    assert len(listing_after.json()) == 1


def test_ai_draft_generates_editable_content_without_persisting(client):
    """RF-12 — "Criar recurso com IA" gera um rascunho que não persiste nada."""
    ctx = register_clinic(client)
    response = client.post(
        "/v1/resources/ai-draft",
        json={"kind": "historia_social", "theme": "Ir ao dentista", "age_range": "5-7 anos"},
        headers=ctx["headers"],
    )
    assert response.status_code == 200, response.text
    draft = response.json()
    assert "Ir ao dentista" in draft["title"]
    assert "Ir ao dentista" in draft["content_text"]

    listing = client.get("/v1/resources", headers=ctx["headers"])
    assert listing.json() == []


def test_ai_publish_creates_resource_with_ai_badge_fields(client, mock_s3):
    ctx = register_clinic(client)
    draft = client.post(
        "/v1/resources/ai-draft",
        json={"kind": "rotina_visual", "theme": "Escovar os dentes", "age_range": "3-5 anos"},
        headers=ctx["headers"],
    ).json()

    response = client.post(
        "/v1/resources/ai-publish",
        json={
            "kind": draft["kind"],
            "theme": draft["theme"],
            "age_range": draft["age_range"],
            "title": draft["title"],
            "description": draft["description"],
            "content_text": draft["content_text"],
            "visibility": "clinic_shared",
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 201, response.text
    resource = response.json()
    assert resource["ai_generated"] is True
    assert resource["ai_reviewed_at"] is not None
    assert resource["resource_type"] == "pdf"

    detail = client.get(f"/v1/resources/{resource['id']}", headers=ctx["headers"])
    assert detail.status_code == 200
    assert detail.json()["view_url"].startswith("http")


def test_ai_publish_allows_editing_draft_before_publishing(client, mock_s3):
    ctx = register_clinic(client)
    draft = client.post(
        "/v1/resources/ai-draft",
        json={"kind": "cartao_comunicacao", "theme": "Quero água", "age_range": "2-4 anos"},
        headers=ctx["headers"],
    ).json()

    response = client.post(
        "/v1/resources/ai-publish",
        json={
            "kind": draft["kind"],
            "theme": draft["theme"],
            "age_range": draft["age_range"],
            "title": "Título editado pelo profissional",
            "content_text": "Conteúdo editado pelo profissional antes de publicar.",
            "visibility": "private",
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 201, response.text
    assert response.json()["title"] == "Título editado pelo profissional"


def test_ai_publish_individual_cannot_share_with_clinic(client, mock_s3):
    ctx = register_individual(client)
    response = client.post(
        "/v1/resources/ai-publish",
        json={
            "kind": "historia_social",
            "theme": "Tema",
            "age_range": "5-7 anos",
            "title": "Título",
            "content_text": "Conteúdo",
            "visibility": "clinic_shared",
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 400
