import io

from tests.conftest import invite_and_accept_professional, register_clinic


def _csv_file(content: str, filename: str = "pacientes.csv"):
    return {"file": (filename, io.BytesIO(content.encode("utf-8")), "text/csv")}


VALID_CSV = (
    "nome,data de nascimento,responsavel,diagnostico\n"
    "Joao Silva,2018-01-01,Maria Silva,TEA\n"
    "Ana Souza,15/03/2019,Carlos Souza,\n"
    "Pedro Lima,,Rita Lima,Atraso de fala\n"
)


def test_preview_detects_portuguese_columns_and_flags_invalid_rows(client):
    ctx = register_clinic(client)

    response = client.post(
        "/v1/patients/import/preview", files=_csv_file(VALID_CSV), headers=ctx["headers"]
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["detected_columns"]["name"] == "nome"
    assert body["detected_columns"]["birth_date"] == "data de nascimento"
    assert body["detected_columns"]["guardian_name"] == "responsavel"
    assert body["detected_columns"]["diagnosis"] == "diagnostico"
    assert body["missing_required_columns"] == []
    assert body["total_rows"] == 3

    rows = {row["name"]: row for row in body["rows"]}
    assert rows["Joao Silva"]["valid"] is True
    assert rows["Ana Souza"]["valid"] is True
    assert rows["Ana Souza"]["birth_date"] == "15/03/2019"
    assert rows["Pedro Lima"]["valid"] is False
    assert rows["Pedro Lima"]["error"] == "Data de nascimento ausente"


def test_preview_reports_missing_required_columns(client):
    ctx = register_clinic(client)
    csv_content = "coluna_irrelevante\nvalor\n"

    response = client.post(
        "/v1/patients/import/preview", files=_csv_file(csv_content), headers=ctx["headers"]
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body["missing_required_columns"]) == {"name", "birth_date"}
    assert body["rows"] == []


def test_commit_imports_valid_rows_and_rejects_invalid_ones(client):
    ctx = register_clinic(client)

    response = client.post(
        "/v1/patients/import/commit", files=_csv_file(VALID_CSV), headers=ctx["headers"]
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["imported_count"] == 2
    assert len(body["rejected"]) == 1
    assert body["rejected"][0]["name"] == "Pedro Lima"
    assert body["rejected"][0]["reason"] == "Data de nascimento ausente"

    patients = client.get("/v1/patients", headers=ctx["headers"]).json()
    names = {p["name"] for p in patients}
    assert "Joao Silva" in names
    assert "Ana Souza" in names
    assert "Pedro Lima" not in names


def test_commit_rejects_invalid_date_format(client):
    ctx = register_clinic(client)
    csv_content = "nome,data de nascimento\nJoana Reis,31-12-2020-extra\n"

    response = client.post(
        "/v1/patients/import/commit", files=_csv_file(csv_content), headers=ctx["headers"]
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported_count"] == 0
    assert body["rejected"][0]["reason"].startswith("Data de nascimento em formato inv")


def test_commit_fails_when_required_columns_missing(client):
    ctx = register_clinic(client)
    csv_content = "coluna_qualquer\nvalor\n"

    response = client.post(
        "/v1/patients/import/commit", files=_csv_file(csv_content), headers=ctx["headers"]
    )
    assert response.status_code == 400


def test_professional_cannot_import_patients_by_default(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    preview = client.post(
        "/v1/patients/import/preview", files=_csv_file(VALID_CSV), headers=professional["headers"]
    )
    assert preview.status_code == 403

    commit = client.post(
        "/v1/patients/import/commit", files=_csv_file(VALID_CSV), headers=professional["headers"]
    )
    assert commit.status_code == 403


def test_professional_can_import_patients_when_enabled(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    client.patch(
        "/v1/clinic/permission-settings",
        json={"professionals_can_create_patients": True},
        headers=ctx["headers"],
    )

    response = client.post(
        "/v1/patients/import/commit", files=_csv_file(VALID_CSV), headers=professional["headers"]
    )
    assert response.status_code == 200, response.text
    assert response.json()["imported_count"] == 2
