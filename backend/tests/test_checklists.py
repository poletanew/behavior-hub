from tests.conftest import create_patient, register_clinic


def _create_template(client, headers, title="Rotina de Sono"):
    response = client.post(
        "/v1/checklist-templates",
        json={
            "title": title,
            "questions": [
                {"text": "Dorme sozinho?", "answer_type": "yes_no"},
                {"text": "Qualidade do sono (1-5)", "answer_type": "scale"},
                {"text": "Observações", "answer_type": "short_text"},
                {"text": "Acorda de madrugada?", "answer_type": "yes_no"},
                {"text": "Nível de agitação antes de dormir (1-5)", "answer_type": "scale"},
            ],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_reusable_checklist_template(client):
    """RF-22 — o profissional monta o checklist uma vez para reaplicar depois."""
    ctx = register_clinic(client)
    template = _create_template(client, ctx["headers"])
    assert len(template["questions"]) == 5
    assert all(q["id"] for q in template["questions"])

    listed = client.get("/v1/checklist-templates", headers=ctx["headers"])
    assert any(t["id"] == template["id"] for t in listed.json())


def test_apply_checklist_to_patient_and_see_tabulated_result(client):
    """RF-22 — critério de aceite: aplicar em um paciente e ver o resultado tabulado."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    template = _create_template(client, ctx["headers"])
    q = {question["text"]: question["id"] for question in template["questions"]}

    response = client.post(
        f"/v1/patients/{patient['id']}/checklist-responses",
        json={
            "template_id": template["id"],
            "answers": [
                {"question_id": q["Dorme sozinho?"], "value": True},
                {"question_id": q["Qualidade do sono (1-5)"], "value": 4},
                {"question_id": q["Observações"], "value": "Dorme bem na maioria das noites"},
                {"question_id": q["Acorda de madrugada?"], "value": False},
                {"question_id": q["Nível de agitação antes de dormir (1-5)"], "value": 2},
            ],
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 201, response.text
    detail = response.json()
    assert detail["template_title"] == "Rotina de Sono"
    assert len(detail["items"]) == 5
    scale_item = next(i for i in detail["items"] if i["question_text"] == "Qualidade do sono (1-5)")
    assert scale_item["value"] == 4

    listing = client.get(f"/v1/patients/{patient['id']}/checklist-responses", headers=ctx["headers"])
    assert len(listing.json()) == 1


def test_apply_checklist_rejects_invalid_answer_type(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    template = _create_template(client, ctx["headers"])
    scale_question_id = next(q["id"] for q in template["questions"] if q["answer_type"] == "scale")

    response = client.post(
        f"/v1/patients/{patient['id']}/checklist-responses",
        json={"template_id": template["id"], "answers": [{"question_id": scale_question_id, "value": 9}]},
        headers=ctx["headers"],
    )
    assert response.status_code in (400, 422)


def test_apply_checklist_requires_all_questions_answered(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    template = _create_template(client, ctx["headers"])
    only_question_id = template["questions"][0]["id"]

    response = client.post(
        f"/v1/patients/{patient['id']}/checklist-responses",
        json={"template_id": template["id"], "answers": [{"question_id": only_question_id, "value": True}]},
        headers=ctx["headers"],
    )
    assert response.status_code == 400


def test_checklist_templates_isolated_by_tenant(client):
    clinic_a = register_clinic(client, "Clinica Checklist A")
    clinic_b = register_clinic(client, "Clinica Checklist B")
    template_a = _create_template(client, clinic_a["headers"])

    listed_b = client.get("/v1/checklist-templates", headers=clinic_b["headers"])
    assert all(t["id"] != template_a["id"] for t in listed_b.json())
