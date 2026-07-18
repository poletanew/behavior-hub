import datetime

from tests.conftest import create_patient, create_training, create_training_category, register_clinic


def _create_session(client, headers, patient_id, professional_id, training_id, occurred_at):
    response = client.post(
        "/v1/sessions",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "occurred_at": occurred_at.isoformat(),
            "training_ids": [training_id],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["trainings"][0]["id"]


def _add_trials(client, headers, session_training_id, count):
    for _ in range(count):
        response = client.post(
            f"/v1/session-trainings/{session_training_id}/trials",
            json={"result": "correct", "prompt_level": "independent"},
            headers=headers,
        )
        assert response.status_code == 201, response.text


def test_heatmap_empty_when_no_trials(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    data = client.get(f"/v1/reports/patients/{patient['id']}", headers=ctx["headers"]).json()
    assert data["heatmap"] == []


def test_heatmap_reflects_trial_distribution_by_area(client, db_session):
    """AC-17 — o heatmap reflete a distribuição real de tentativas por área."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    now = datetime.datetime.now(datetime.timezone.utc)

    category_a = create_training_category(db_session, name="Comunicacao")
    training_a = create_training(db_session, category_a, title="Pedir ajuda")
    st_a = _create_session(client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training_a.id), now)
    _add_trials(client, ctx["headers"], st_a, 8)

    category_b = create_training_category(db_session, name="Social")
    training_b = create_training(db_session, category_b, title="Cumprimentar")
    st_b = _create_session(client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training_b.id), now)
    _add_trials(client, ctx["headers"], st_b, 4)

    category_c = create_training_category(db_session, name="Autonomia")
    training_c = create_training(db_session, category_c, title="Vestir-se")
    st_c = _create_session(client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training_c.id), now)
    _add_trials(client, ctx["headers"], st_c, 2)

    category_d = create_training_category(db_session, name="Motor")
    training_d = create_training(db_session, category_d, title="Chutar bola")
    st_d = _create_session(client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training_d.id), now)
    _add_trials(client, ctx["headers"], st_d, 1)

    data = client.get(f"/v1/reports/patients/{patient['id']}", headers=ctx["headers"]).json()
    heatmap = {point["area"]: point for point in data["heatmap"]}

    assert heatmap[category_a.name]["trial_count"] == 8
    assert heatmap[category_a.name]["intensity_pct"] == 100.0
    assert heatmap[category_a.name]["intensity_label"] == "muito_alta"

    assert heatmap[category_b.name]["trial_count"] == 4
    assert heatmap[category_b.name]["intensity_pct"] == 50.0
    assert heatmap[category_b.name]["intensity_label"] == "alta"

    assert heatmap[category_c.name]["trial_count"] == 2
    assert heatmap[category_c.name]["intensity_pct"] == 25.0
    assert heatmap[category_c.name]["intensity_label"] == "media"

    assert heatmap[category_d.name]["trial_count"] == 1
    assert heatmap[category_d.name]["intensity_pct"] == 12.5
    assert heatmap[category_d.name]["intensity_label"] == "baixa"


def test_heatmap_excludes_trials_older_than_30_days(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    old_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=45)

    category = create_training_category(db_session, name="Comunicacao")
    training = create_training(db_session, category)
    session_training_id = _create_session(
        client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id), old_date
    )
    _add_trials(client, ctx["headers"], session_training_id, 3)

    data = client.get(f"/v1/reports/patients/{patient['id']}", headers=ctx["headers"]).json()
    assert data["heatmap"] == []


def test_heatmap_recomputes_after_new_trial(client, db_session):
    """AC-17 — recalculado ao salvar nova tentativa (sempre derivado ao vivo dos dados)."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    now = datetime.datetime.now(datetime.timezone.utc)

    category = create_training_category(db_session, name="Comunicacao")
    training = create_training(db_session, category)
    session_training_id = _create_session(
        client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id), now
    )
    _add_trials(client, ctx["headers"], session_training_id, 2)

    before = client.get(f"/v1/reports/patients/{patient['id']}", headers=ctx["headers"]).json()
    assert before["heatmap"][0]["trial_count"] == 2

    _add_trials(client, ctx["headers"], session_training_id, 1)

    after = client.get(f"/v1/reports/patients/{patient['id']}", headers=ctx["headers"]).json()
    assert after["heatmap"][0]["trial_count"] == 3


def test_heatmap_ignores_report_date_filters(client, db_session):
    """O heatmap sempre usa os últimos 30 dias corridos, independente do filtro de período do Report."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    now = datetime.datetime.now(datetime.timezone.utc)

    category = create_training_category(db_session, name="Comunicacao")
    training = create_training(db_session, category)
    session_training_id = _create_session(
        client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id), now
    )
    _add_trials(client, ctx["headers"], session_training_id, 2)

    far_past = (now - datetime.timedelta(days=400)).date().isoformat()
    data = client.get(
        f"/v1/reports/patients/{patient['id']}?date_from={far_past}&date_to={far_past}",
        headers=ctx["headers"],
    ).json()
    assert data["total_trials"] == 0
    assert data["heatmap"][0]["trial_count"] == 2
