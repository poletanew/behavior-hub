import datetime
import io

from reportlab.pdfgen import canvas

from tests.conftest import (
    assign_professional,
    create_patient,
    invite_and_accept,
    invite_and_accept_professional,
    register_clinic,
)


def _pdf_with_text(*lines: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 750
    for line in lines:
        c.drawString(100, y, line)
        y -= 20
    c.showPage()
    c.save()
    return buf.getvalue()


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


def _upload_attachment(client, headers, patient_id, area="aba", filename="avaliacao.pdf"):
    return client.post(
        f"/v1/patients/{patient_id}/treatment-plan/attachments",
        data={"area": area},
        files={"file": (filename, b"%PDF-1.4 fake content", "application/pdf")},
        headers=headers,
    )


def test_upload_attachment_scoped_to_its_area(client, mock_s3):
    """RF-04 — importar um PDF em uma área não o torna visível nem editável nas demais."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    response = _upload_attachment(client, ctx["headers"], patient["id"], area="aba")
    assert response.status_code == 201, response.text
    attachment = response.json()
    assert attachment["area"] == "aba"
    assert attachment["original_filename"] == "avaliacao.pdf"
    assert attachment["uploaded_by_name"] == ctx["user"]["name"]

    plan = client.get(f"/v1/patients/{patient['id']}/treatment-plan", headers=ctx["headers"])
    attachments = plan.json()["attachments"]
    assert len(attachments) == 1
    assert attachments[0]["area"] == "aba"

    aba_only = [a for a in attachments if a["area"] == "aba"]
    other_areas = [a for a in attachments if a["area"] != "aba"]
    assert len(aba_only) == 1
    assert len(other_areas) == 0


def test_attachment_opens_via_signed_view_url(client, mock_s3):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    attachment = _upload_attachment(client, ctx["headers"], patient["id"]).json()

    detail = client.get(f"/v1/treatment-plan/attachments/{attachment['id']}", headers=ctx["headers"])
    assert detail.status_code == 200
    assert detail.json()["view_url"].startswith("http")


def test_attachment_rejects_non_pdf(client, mock_s3):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    response = client.post(
        f"/v1/patients/{patient['id']}/treatment-plan/attachments",
        data={"area": "aba"},
        files={"file": ("script.exe", b"MZ...", "application/x-msdownload")},
        headers=ctx["headers"],
    )
    assert response.status_code == 415


def test_professional_without_area_permission_cannot_upload_attachment(client, mock_s3):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    professional = invite_and_accept_professional(client, ctx["headers"], specialty="fonoaudiologo")
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"])

    response = _upload_attachment(client, professional["headers"], patient["id"], area="aba")
    assert response.status_code == 403


def test_at_cannot_access_treatment_plan_attachments(client, mock_s3):
    """RF-11 — o AT não tem acesso ao Plano de Tratamento, nem aos seus anexos."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    attachment = _upload_attachment(client, ctx["headers"], patient["id"]).json()
    at = invite_and_accept(client, ctx["headers"], role="at")

    forbidden_plan = client.get(f"/v1/patients/{patient['id']}/treatment-plan", headers=at["headers"])
    assert forbidden_plan.status_code == 403

    forbidden_attachment = client.get(f"/v1/treatment-plan/attachments/{attachment['id']}", headers=at["headers"])
    assert forbidden_attachment.status_code == 403


def _upload_pdf_bytes(client, headers, patient_id, data: bytes, area="aba", filename="doc.pdf"):
    return client.post(
        f"/v1/patients/{patient_id}/treatment-plan/attachments",
        data={"area": area},
        files={"file": (filename, data, "application/pdf")},
        headers=headers,
    )


def test_ai_fill_maps_pdf_text_to_objective_fields(client, mock_s3):
    """RF-05 — "Preencher com IA": extrai o texto do PDF já anexado (RF-04) e sugere
    um rascunho editável dos 4 campos, sem publicar nada automaticamente."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    pdf_bytes = _pdf_with_text(
        "Avaliacao de linguagem expressiva",
        "Criterio de dominio: 80% de acertos em 3 sessoes",
        "Estrategia: uso de dicas visuais e reforco positivo",
    )
    attachment = _upload_pdf_bytes(client, ctx["headers"], patient["id"], pdf_bytes).json()

    response = client.post(
        f"/v1/patients/{patient['id']}/treatment-plan/objectives/ai-fill",
        json={"attachment_id": attachment["id"]},
        headers=ctx["headers"],
    )
    assert response.status_code == 200, response.text
    draft = response.json()
    assert draft["source_document_id"] == attachment["id"]
    assert draft["title"] == "Avaliacao de linguagem expressiva"
    assert "80%" in draft["criteria"]
    assert "positivo" in draft["strategies"].lower() or "estrategia" in draft["strategies"].lower()
    assert draft["extraction_note"] is None


def test_ai_fill_flags_pdf_with_no_extractable_text(client, mock_s3):
    """PDF de página em branco (sem texto) — caminho de fallback do "Ponto técnico
    de atenção" do addendum (ex.: documento escaneado sem OCR)."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    blank_pdf = _pdf_with_text()
    attachment = _upload_pdf_bytes(client, ctx["headers"], patient["id"], blank_pdf).json()

    response = client.post(
        f"/v1/patients/{patient['id']}/treatment-plan/objectives/ai-fill",
        json={"attachment_id": attachment["id"]},
        headers=ctx["headers"],
    )
    assert response.status_code == 200, response.text
    draft = response.json()
    assert draft["extraction_note"] is not None
    assert draft["description"] == ""


def test_creating_objective_from_ai_draft_marks_reviewed_at_save(client, mock_s3):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    pdf_bytes = _pdf_with_text("Objetivo sugerido", "Criterio de dominio: 90%", "Estrategia: modelagem")
    attachment = _upload_pdf_bytes(client, ctx["headers"], patient["id"], pdf_bytes).json()

    response = _create_objective(
        client,
        ctx["headers"],
        patient["id"],
        title="Objetivo sugerido",
        ai_generated=True,
        ai_source_document_id=attachment["id"],
    )
    assert response.status_code == 201, response.text
    objective = response.json()
    assert objective["ai_generated"] is True
    assert objective["ai_source_document_id"] == attachment["id"]
    assert objective["ai_reviewed_at"] is not None


def test_non_ai_objective_has_no_ai_fields(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    objective = _create_objective(client, ctx["headers"], patient["id"]).json()
    assert objective["ai_generated"] is False
    assert objective["ai_source_document_id"] is None
    assert objective["ai_reviewed_at"] is None


def test_ai_fill_requires_area_edit_permission(client, mock_s3):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    pdf_bytes = _pdf_with_text("Documento")
    attachment = _upload_pdf_bytes(client, ctx["headers"], patient["id"], pdf_bytes, area="aba").json()

    professional = invite_and_accept_professional(client, ctx["headers"], specialty="fonoaudiologo")
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"])

    response = client.post(
        f"/v1/patients/{patient['id']}/treatment-plan/objectives/ai-fill",
        json={"attachment_id": attachment["id"]},
        headers=professional["headers"],
    )
    assert response.status_code == 403


def test_ai_fill_works_for_specialties_without_a_dedicated_area(client, mock_s3):
    """Addendum v3.0, RF-37 — a Seção 7.2 do PRD lista 12 especialidades, mas só 7
    tinham entrada em SPECIALTY_TO_AREA; as outras 5 (sem área dedicada na grade)
    nunca conseguiam usar "Preencher com IA" em nenhuma área. Testa 3 delas
    (Musicoterapeuta, Arteterapeuta, Neuropediatra), todas mapeadas para a área
    'outra' — mesmo mecanismo de IA (RF-05), mesma revisão humana obrigatória."""
    for specialty in ["musicoterapeuta", "arteterapeuta", "neuropediatra"]:
        ctx = register_clinic(client)
        patient = create_patient(client, ctx["headers"])
        pdf_bytes = _pdf_with_text("Registro multidisciplinar", "Criterio de dominio: 70%")
        attachment = _upload_pdf_bytes(client, ctx["headers"], patient["id"], pdf_bytes, area="outra").json()

        professional = invite_and_accept_professional(client, ctx["headers"], specialty=specialty)
        assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"], permission="edit_area_plan")

        response = client.post(
            f"/v1/patients/{patient['id']}/treatment-plan/objectives/ai-fill",
            json={"attachment_id": attachment["id"]},
            headers=professional["headers"],
        )
        assert response.status_code == 200, f"{specialty}: {response.text}"
        draft = response.json()
        assert draft["title"] == "Registro multidisciplinar"

        created = client.post(
            f"/v1/patients/{patient['id']}/treatment-plan/objectives",
            json={
                "area": "outra",
                "title": draft["title"],
                "description": draft["description"],
                "criteria": draft["criteria"],
                "strategies": draft["strategies"],
                "priority": "medium",
                "ai_generated": True,
                "ai_source_document_id": attachment["id"],
            },
            headers=professional["headers"],
        )
        assert created.status_code == 201, f"{specialty}: {created.text}"
        # Seção 12.1 — salvar É a confirmação de revisão humana obrigatória.
        assert created.json()["ai_reviewed_at"] is not None


def test_marking_objective_mastered_auto_schedules_maintenance_check(client):
    """Addendum v3.0, RF-24 — objetivo dominado gera automaticamente um
    lembrete de reteste de manutenção 30 dias à frente."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    objective = _create_objective(client, ctx["headers"], patient["id"]).json()
    assert objective["maintenance_check_date"] is None
    assert objective["maintenance_due"] is False

    mastered = client.patch(
        f"/v1/objectives/{objective['id']}", json={"status": "mastered"}, headers=ctx["headers"]
    )
    assert mastered.status_code == 200, mastered.text
    body = mastered.json()
    expected = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    assert body["maintenance_check_date"] == expected


def test_recording_generalization_contexts_accumulates_entries(client):
    """Addendum v3.0, RF-24 — campos simples para marcar onde já foi testado
    (clínica, casa, escola) e o resultado em cada um."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    objective = _create_objective(client, ctx["headers"], patient["id"]).json()

    for context in ("clinica", "casa", "escola"):
        response = client.post(
            f"/v1/objectives/{objective['id']}/generalization-contexts",
            json={"context": context, "tested_at": "2026-07-01", "result": "Generalizou com sucesso"},
            headers=ctx["headers"],
        )
        assert response.status_code == 200, response.text

    final = client.get(f"/v1/objectives/{objective['id']}", headers=ctx["headers"])
    contexts = final.json()["generalization_contexts"]
    assert [c["context"] for c in contexts] == ["clinica", "casa", "escola"]
    assert all(c["result"] == "Generalizou com sucesso" for c in contexts)


def test_maintenance_check_requires_mastered_status_and_reschedules(client):
    """Addendum v3.0, RF-24 — reteste de manutenção só se aplica a objetivos
    dominados, e reagenda o próximo lembrete."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    objective = _create_objective(client, ctx["headers"], patient["id"]).json()

    not_mastered = client.post(
        f"/v1/objectives/{objective['id']}/maintenance-checks",
        json={"result": "mantida"},
        headers=ctx["headers"],
    )
    assert not_mastered.status_code == 400

    client.patch(f"/v1/objectives/{objective['id']}", json={"status": "mastered"}, headers=ctx["headers"])

    checked = client.post(
        f"/v1/objectives/{objective['id']}/maintenance-checks",
        json={"result": "mantida", "notes": "Manteve o repertório"},
        headers=ctx["headers"],
    )
    assert checked.status_code == 200, checked.text
    expected = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    assert checked.json()["maintenance_check_date"] == expected

    history = client.get(f"/v1/objectives/{objective['id']}/history", headers=ctx["headers"])
    actions = [entry["action"] for entry in history.json()]
    assert "objective_maintenance_checked" in actions


def test_add_applier_requires_area_permission(client):
    """Addendum v3.0, RF-25 — só quem edita a área do objetivo pode marcar aplicadores."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    objective = _create_objective(client, ctx["headers"], patient["id"]).json()
    professional = invite_and_accept_professional(client, ctx["headers"], specialty="fonoaudiologo")
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"])

    response = client.post(
        f"/v1/objectives/{objective['id']}/appliers",
        json={"applier_type": "professional", "applier_user_id": ctx["user"]["id"]},
        headers=professional["headers"],
    )
    assert response.status_code == 403


def test_add_professional_applier(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    objective = _create_objective(client, ctx["headers"], patient["id"]).json()
    professional = invite_and_accept_professional(client, ctx["headers"], specialty="fonoaudiologo")
    assign_professional(
        client, ctx["headers"], patient["id"], professional["user"]["id"], permission="edit_area_plan"
    )

    response = client.post(
        f"/v1/objectives/{objective['id']}/appliers",
        json={"applier_type": "professional", "applier_user_id": professional["user"]["id"]},
        headers=ctx["headers"],
    )
    assert response.status_code == 201, response.text
    assert response.json()["applier_name"] == professional["user"]["name"]

    listed = client.get(f"/v1/objectives/{objective['id']}/appliers", headers=ctx["headers"])
    assert len(listed.json()) == 1

    duplicate = client.post(
        f"/v1/objectives/{objective['id']}/appliers",
        json={"applier_type": "professional", "applier_user_id": professional["user"]["id"]},
        headers=ctx["headers"],
    )
    assert duplicate.status_code == 409


def test_reorder_objectives_within_area(client):
    """Addendum v3.0, RF-28 — arrastar e soltar para reordenar prioridade dos
    objetivos de uma área do Plano de Tratamento."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    first = _create_objective(client, ctx["headers"], patient["id"], title="Primeiro").json()
    second = _create_objective(client, ctx["headers"], patient["id"], title="Segundo").json()
    third = _create_objective(client, ctx["headers"], patient["id"], title="Terceiro").json()

    plan = client.get(f"/v1/patients/{patient['id']}/treatment-plan", headers=ctx["headers"]).json()
    assert [o["title"] for o in plan["objectives"]] == ["Primeiro", "Segundo", "Terceiro"]

    reordered = client.post(
        f"/v1/patients/{patient['id']}/treatment-plan/objectives/reorder",
        json={"area": "aba", "ordered_ids": [third["id"], first["id"], second["id"]]},
        headers=ctx["headers"],
    )
    assert reordered.status_code == 200, reordered.text
    assert [o["title"] for o in reordered.json()] == ["Terceiro", "Primeiro", "Segundo"]

    plan_after = client.get(f"/v1/patients/{patient['id']}/treatment-plan", headers=ctx["headers"]).json()
    assert [o["title"] for o in plan_after["objectives"]] == ["Terceiro", "Primeiro", "Segundo"]


def test_reorder_objectives_requires_area_permission(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    objective = _create_objective(client, ctx["headers"], patient["id"]).json()
    professional = invite_and_accept_professional(client, ctx["headers"], specialty="fonoaudiologo")
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"])

    response = client.post(
        f"/v1/patients/{patient['id']}/treatment-plan/objectives/reorder",
        json={"area": "aba", "ordered_ids": [objective["id"]]},
        headers=professional["headers"],
    )
    assert response.status_code == 403


def test_reorder_objectives_rejects_incomplete_list(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    first = _create_objective(client, ctx["headers"], patient["id"], title="Primeiro").json()
    _create_objective(client, ctx["headers"], patient["id"], title="Segundo")

    response = client.post(
        f"/v1/patients/{patient['id']}/treatment-plan/objectives/reorder",
        json={"area": "aba", "ordered_ids": [first["id"]]},
        headers=ctx["headers"],
    )
    assert response.status_code == 400
