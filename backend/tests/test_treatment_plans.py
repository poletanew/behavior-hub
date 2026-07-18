from tests.conftest import assign_professional, create_patient, invite_and_accept_professional, register_clinic


def _create_objective(client, headers, patient_id, **overrides):
    payload = {
        "area": "aba",
        "title": "Aguardar por 30 segundos com comportamento seguro",
        "description": "Objetivo de teste",
        "criteria": "80% de respostas independentes em 3 sessões consecutivas",
        "strategies": "Aumento gradual do tempo",
        "priority": "high",
    }
    payload.update(overrides)
    return client.post(f"/v1/patients/{patient_id}/treatment-plan/objectives", json=payload, headers=headers)


def test_create_objective_and_get_plan(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    response = _create_objective(client, ctx["headers"], patient["id"])
    assert response.status_code == 201, response.text
    objective = response.json()
    assert objective["area"] == "aba"
    assert objective["status"] == "not_started"

    plan = client.get(f"/v1/patients/{patient['id']}/treatment-plan", headers=ctx["headers"])
    assert plan.status_code == 200
    assert len(plan.json()["objectives"]) == 1


def test_duplicate_objective_generates_alert_with_author_and_area(client):
    """AC-08 — objetivo semelhante gera alerta com autor e área (Seção 13.2)."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    first = _create_objective(client, ctx["headers"], patient["id"])
    assert first.status_code == 201

    duplicate = _create_objective(
        client, ctx["headers"], patient["id"], title="Aguardar 30 segundos com comportamento seguro"
    )
    assert duplicate.status_code == 409
    body = duplicate.json()["detail"]
    assert body["duplicate_candidates"][0]["area"] == "aba"
    assert body["duplicate_candidates"][0]["author_id"] == ctx["user"]["id"]


def test_duplicate_objective_can_be_forced(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    _create_objective(client, ctx["headers"], patient["id"])

    forced = _create_objective(
        client,
        ctx["headers"],
        patient["id"],
        title="Aguardar 30 segundos com comportamento seguro",
        force=True,
    )
    assert forced.status_code == 201

    plan = client.get(f"/v1/patients/{patient['id']}/treatment-plan", headers=ctx["headers"])
    assert len(plan.json()["objectives"]) == 2


def test_distinct_objectives_are_not_flagged_as_duplicates(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    _create_objective(client, ctx["headers"], patient["id"], title="Aguardar por 30 segundos")

    distinct = _create_objective(client, ctx["headers"], patient["id"], title="Compartilhar objeto a pedido")
    assert distinct.status_code == 201


def test_professional_with_edit_sessions_cannot_edit_objective(client):
    """Seção 13.3 — cada profissional edita objetivos da própria área ou com permissão explícita."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    professional = invite_and_accept_professional(client, ctx["headers"], specialty="fonoaudiologo")
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"], permission="edit_sessions")

    response = _create_objective(client, professional["headers"], patient["id"])
    assert response.status_code == 403


def test_professional_with_edit_area_plan_can_edit_matching_area(client):
    """Fonoaudiólogo (SPECIALTY_TO_AREA) só edita objetivos de Fonoaudiologia."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    professional = invite_and_accept_professional(client, ctx["headers"], specialty="fonoaudiologo")
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"], permission="edit_area_plan")

    matching_area = _create_objective(client, professional["headers"], patient["id"], area="fonoaudiologia")
    assert matching_area.status_code == 201, matching_area.text

    other_area = _create_objective(client, professional["headers"], patient["id"], area="aba", title="Outro objetivo")
    assert other_area.status_code == 403


def test_professional_with_full_access_can_edit_any_area(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    professional = invite_and_accept_professional(client, ctx["headers"], specialty="fonoaudiologo")
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"], permission="full_access")

    response = _create_objective(client, professional["headers"], patient["id"], area="aba")
    assert response.status_code == 201


def test_soft_delete_and_restore_objective(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    objective = _create_objective(client, ctx["headers"], patient["id"]).json()

    delete_response = client.delete(f"/v1/objectives/{objective['id']}", headers=ctx["headers"])
    assert delete_response.status_code == 204

    plan = client.get(f"/v1/patients/{patient['id']}/treatment-plan", headers=ctx["headers"])
    assert plan.json()["objectives"] == []

    restore_response = client.post(f"/v1/objectives/{objective['id']}/restore", headers=ctx["headers"])
    assert restore_response.status_code == 200

    plan_after = client.get(f"/v1/patients/{patient['id']}/treatment-plan", headers=ctx["headers"])
    assert len(plan_after.json()["objectives"]) == 1


def test_comments_and_history(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    objective = _create_objective(client, ctx["headers"], patient["id"]).json()

    comment_response = client.post(
        f"/v1/objectives/{objective['id']}/comments", json={"body": "Progresso consistente"}, headers=ctx["headers"]
    )
    assert comment_response.status_code == 201

    comments = client.get(f"/v1/objectives/{objective['id']}/comments", headers=ctx["headers"])
    assert len(comments.json()) == 1
    assert comments.json()[0]["body"] == "Progresso consistente"

    client.patch(f"/v1/objectives/{objective['id']}", json={"status": "in_progress"}, headers=ctx["headers"])

    history = client.get(f"/v1/objectives/{objective['id']}/history", headers=ctx["headers"])
    actions = [entry["action"] for entry in history.json()]
    assert "objective_created" in actions
    assert "objective_updated" in actions


def test_filters_by_area_and_status(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    aba_response = _create_objective(client, ctx["headers"], patient["id"], area="aba", title="Tolerância à espera")
    assert aba_response.status_code == 201, aba_response.text
    fono_response = _create_objective(
        client, ctx["headers"], patient["id"], area="fonoaudiologia", title="Expandir repertório verbal"
    )
    assert fono_response.status_code == 201, fono_response.text

    filtered = client.get(
        f"/v1/patients/{patient['id']}/treatment-plan?area=fonoaudiologia", headers=ctx["headers"]
    )
    titles = [o["title"] for o in filtered.json()["objectives"]]
    assert titles == ["Expandir repertório verbal"]


def test_treatment_plan_isolated_by_tenant(client):
    """Seção 17 — o plano de tratamento segue o mesmo isolamento de tenant do paciente."""
    clinic_a = register_clinic(client, "Clinica A")
    clinic_b = register_clinic(client, "Clinica B")
    patient_a = create_patient(client, clinic_a["headers"])
    _create_objective(client, clinic_a["headers"], patient_a["id"])

    forbidden = client.get(f"/v1/patients/{patient_a['id']}/treatment-plan", headers=clinic_b["headers"])
    assert forbidden.status_code == 404
