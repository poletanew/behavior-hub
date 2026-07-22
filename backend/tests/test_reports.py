from tests.conftest import create_patient, create_training, create_training_category, register_clinic


def _seed_session_with_trials(client, headers, patient_id, professional_id, training_id, occurred_at):
    session_response = client.post(
        "/v1/sessions",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "occurred_at": occurred_at,
            "training_ids": [training_id],
        },
        headers=headers,
    )
    assert session_response.status_code == 201, session_response.text
    session_training_id = session_response.json()["trainings"][0]["id"]

    for result, prompt_level in [
        ("correct", "independent"),
        ("correct", "verbal"),
        ("incorrect", "gestural"),
    ]:
        client.post(
            f"/v1/session-trainings/{session_training_id}/trials",
            json={"result": result, "prompt_level": prompt_level},
            headers=headers,
        )
    return session_response.json()


def test_report_data_matches_prd_example(client, db_session):
    """AC-05/AC-06 — os gráficos de Reports usam a mesma fonte de tentativas e refletem 66,7%."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session, name="Autorregulação")
    training = create_training(db_session, category, title="Aguardar por 30 segundos")

    _seed_session_with_trials(
        client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id), "2026-07-10T10:00:00Z"
    )

    response = client.get(f"/v1/reports/patients/{patient['id']}", headers=ctx["headers"])
    assert response.status_code == 200
    data = response.json()

    assert data["total_trials"] == 3
    assert data["bar"][0]["accuracy_pct"] == 66.7
    assert data["line"][0]["points"][0]["accuracy_pct"] == 66.7
    assert data["pie"] == {"correct": 2, "incorrect": 1, "partial": 0, "no_response": 0}
    assert data["cumulative"][-1]["cumulative_correct"] == 2
    assert data["cumulative"][-1]["cumulative_total"] == 3


def test_behavior_frequency_chart_groups_by_behavior_text(client, db_session):
    """Addendum v3.0, RF-34 — frequência/duração de comportamentos-alvo ao longo
    do tempo, agrupadas pelo texto do comportamento registrado (RF-18)."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = client.post(
        "/v1/sessions",
        json={
            "patient_id": patient["id"],
            "professional_id": ctx["user"]["id"],
            "occurred_at": "2026-07-10T10:00:00Z",
            "training_ids": [str(training.id)],
        },
        headers=ctx["headers"],
    ).json()

    for frequency_count, duration_seconds in [(2, 30), (3, 45)]:
        client.post(
            f"/v1/patients/{patient['id']}/behavior-events",
            json={
                "session_id": session["id"],
                "antecedent": "Pediram para guardar o brinquedo",
                "behavior": "Gritou e jogou o brinquedo no chão",
                "consequence": "Terapeuta ofereceu escolha entre dois brinquedos",
                "frequency_count": frequency_count,
                "duration_seconds": duration_seconds,
            },
            headers=ctx["headers"],
        )

    response = client.get(f"/v1/reports/patients/{patient['id']}", headers=ctx["headers"])
    assert response.status_code == 200
    data = response.json()

    assert len(data["behavior_frequency"]) == 1
    series = data["behavior_frequency"][0]
    assert series["behavior"] == "Gritou e jogou o brinquedo no chão"
    assert series["total_events"] == 2
    assert len(series["points"]) == 1
    assert series["points"][0]["frequency_count"] == 5
    assert series["points"][0]["duration_seconds"] == 75


def test_reinforcer_usage_chart_counts_usages_in_period(client, db_session):
    """Addendum v3.0, RF-34 — frequência de uso de cada reforçador cadastrado (RF-19)."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = client.post(
        "/v1/sessions",
        json={
            "patient_id": patient["id"],
            "professional_id": ctx["user"]["id"],
            "occurred_at": "2026-07-10T10:00:00Z",
            "training_ids": [str(training.id)],
        },
        headers=ctx["headers"],
    ).json()

    reinforcer = client.post(
        f"/v1/patients/{patient['id']}/reinforcers",
        json={"name": "Elogio verbal"},
        headers=ctx["headers"],
    ).json()
    for _ in range(3):
        client.post(
            f"/v1/sessions/{session['id']}/reinforcers",
            json={"reinforcer_id": reinforcer["id"]},
            headers=ctx["headers"],
        )

    response = client.get(f"/v1/reports/patients/{patient['id']}", headers=ctx["headers"])
    assert response.status_code == 200
    data = response.json()

    assert len(data["reinforcer_usage"]) == 1
    assert data["reinforcer_usage"][0]["reinforcer_name"] == "Elogio verbal"
    assert data["reinforcer_usage"][0]["usage_count"] == 3


def test_radar_flags_insufficient_data_below_threshold(client, db_session):
    """Seção 14.3 — radar deve alertar sobre limitações estatísticas com poucas tentativas."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    _seed_session_with_trials(
        client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id), "2026-07-10T10:00:00Z"
    )

    data = client.get(f"/v1/reports/patients/{patient['id']}", headers=ctx["headers"]).json()
    assert data["radar"][0]["insufficient_data"] is True
    assert data["radar"][0]["sample_size"] == 3


def test_deleted_trials_are_excluded_from_report(client, db_session):
    """Seção 14.4 — tentativas excluídas por soft delete não entram nos cálculos ativos."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = _seed_session_with_trials(
        client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id), "2026-07-10T10:00:00Z"
    )
    session_training_id = session["trainings"][0]["id"]
    progress = client.get(f"/v1/session-trainings/{session_training_id}/progress", headers=ctx["headers"]).json()
    incorrect_trial_id = next(t["id"] for t in progress["trials"] if t["result"] == "incorrect")

    client.delete(f"/v1/trials/{incorrect_trial_id}", headers=ctx["headers"])

    data = client.get(f"/v1/reports/patients/{patient['id']}", headers=ctx["headers"]).json()
    assert data["total_trials"] == 2
    assert data["bar"][0]["accuracy_pct"] == 100.0


def test_generated_summary_never_contains_diagnostic_language(client, db_session):
    """Seção 14.5 — resumo nunca emite diagnóstico ou causalidade."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    _seed_session_with_trials(
        client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id), "2026-07-10T10:00:00Z"
    )

    response = client.post(
        f"/v1/reports/patients/{patient['id']}/summary/generate",
        json={"period_start": "2026-01-01", "period_end": "2026-12-31"},
        headers=ctx["headers"],
    )
    assert response.status_code == 201
    body = response.json()
    assert body["generated_by"] == "rule_based_draft"
    assert body["status"] == "draft"
    assert "diagn" in body["content"].lower()  # explicitly states it is NOT a diagnosis
    assert "66.7%" in body["content"]


def test_summary_can_be_edited_and_approved(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    _seed_session_with_trials(
        client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id), "2026-07-10T10:00:00Z"
    )
    summary = client.post(
        f"/v1/reports/patients/{patient['id']}/summary/generate",
        json={"period_start": "2026-01-01", "period_end": "2026-12-31"},
        headers=ctx["headers"],
    ).json()

    updated = client.patch(
        f"/v1/reports/summaries/{summary['id']}",
        json={"content": "Texto revisado pelo profissional.", "status": "approved"},
        headers=ctx["headers"],
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "approved"
    assert updated.json()["content"] == "Texto revisado pelo profissional."


def test_export_csv_and_pdf(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    _seed_session_with_trials(
        client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id), "2026-07-10T10:00:00Z"
    )

    csv_response = client.get(f"/v1/reports/patients/{patient['id']}/export.csv", headers=ctx["headers"])
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    assert "Tentativa" in csv_response.text

    pdf_response = client.get(f"/v1/reports/patients/{patient['id']}/export.pdf", headers=ctx["headers"])
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")


def test_reports_isolated_by_tenant(client, db_session):
    clinic_a = register_clinic(client, "Clinica A")
    clinic_b = register_clinic(client, "Clinica B")
    patient_a = create_patient(client, clinic_a["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    _seed_session_with_trials(
        client, clinic_a["headers"], patient_a["id"], clinic_a["user"]["id"], str(training.id), "2026-07-10T10:00:00Z"
    )

    forbidden = client.get(f"/v1/reports/patients/{patient_a['id']}", headers=clinic_b["headers"])
    assert forbidden.status_code == 404
