from app.models.clinic import Clinic
from app.models.enums import SubscriptionPlan, SubscriptionStatus
from tests.conftest import create_training, create_training_category, register_clinic


def _make_paid(db_session, clinic_id, plan=SubscriptionPlan.BASIC):
    clinic = db_session.query(Clinic).filter(Clinic.id == clinic_id).first()
    clinic.subscription_plan = plan
    clinic.subscription_status = SubscriptionStatus.ACTIVE
    db_session.commit()
    return clinic


def _create_patient(client, headers, name="Paciente Exemplo"):
    response = client.post("/v1/patients", json={"name": name, "birth_date": "2018-05-10"}, headers=headers)
    assert response.status_code == 201
    return response.json()


def _create_session_with_training(client, headers, patient_id, professional_id, training_id, photo_url=None):
    payload = {
        "patient_id": patient_id,
        "professional_id": professional_id,
        "occurred_at": "2026-07-14T10:00:00Z",
        "notes": "Sessão de treino de espera e comunicação funcional",
        "training_ids": [training_id],
    }
    if photo_url is not None:
        payload["photo_url"] = photo_url
    response = client.post("/v1/sessions", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_trials_are_individualized_and_sequential(client, db_session):
    """AC-04 — adicionar tres tentativas exibe Tentativa 1, 2 e 3 com dados individuais (Seção 11.3)."""
    ctx = register_clinic(client)
    patient = _create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    session = _create_session_with_training(
        client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id)
    )
    session_training_id = session["trainings"][0]["id"]

    trial_1 = client.post(
        f"/v1/session-trainings/{session_training_id}/trials",
        json={"result": "correct", "prompt_level": "independent"},
        headers=ctx["headers"],
    )
    trial_2 = client.post(
        f"/v1/session-trainings/{session_training_id}/trials",
        json={"result": "correct", "prompt_level": "verbal"},
        headers=ctx["headers"],
    )
    trial_3 = client.post(
        f"/v1/session-trainings/{session_training_id}/trials",
        json={"result": "incorrect", "prompt_level": "gestural"},
        headers=ctx["headers"],
    )

    assert trial_1.json()["attempt_number"] == 1
    assert trial_2.json()["attempt_number"] == 2
    assert trial_3.json()["attempt_number"] == 3
    # Each trial keeps its own independent result/prompt_level data.
    assert trial_1.json()["result"] == "correct"
    assert trial_3.json()["result"] == "incorrect"


def test_accuracy_percentage_matches_prd_example(client, db_session):
    """AC-05 — duas corretas em tres tentativas validas resultam em 66,7% (Seção 14.4/33.1)."""
    ctx = register_clinic(client)
    patient = _create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = _create_session_with_training(
        client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id)
    )
    session_training_id = session["trainings"][0]["id"]

    for result, prompt_level in [
        ("correct", "independent"),
        ("correct", "verbal"),
        ("incorrect", "gestural"),
    ]:
        client.post(
            f"/v1/session-trainings/{session_training_id}/trials",
            json={"result": result, "prompt_level": prompt_level},
            headers=ctx["headers"],
        )

    progress = client.get(f"/v1/session-trainings/{session_training_id}/progress", headers=ctx["headers"])
    assert progress.status_code == 200
    body = progress.json()
    assert body["accuracy_pct"] == 66.7
    assert body["independence_pct"] == 33.3


def test_attempt_number_is_not_reused_after_delete(client, db_session):
    """Seção 11.3 — o botao Adicionar tentativa cria o proximo numero sequencial sem duplicar numeracao."""
    ctx = register_clinic(client)
    patient = _create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = _create_session_with_training(
        client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id)
    )
    session_training_id = session["trainings"][0]["id"]

    trial_1 = client.post(
        f"/v1/session-trainings/{session_training_id}/trials",
        json={"result": "correct", "prompt_level": "independent"},
        headers=ctx["headers"],
    ).json()
    client.post(
        f"/v1/session-trainings/{session_training_id}/trials",
        json={"result": "correct", "prompt_level": "independent"},
        headers=ctx["headers"],
    )

    delete_response = client.delete(f"/v1/trials/{trial_1['id']}", headers=ctx["headers"])
    assert delete_response.status_code == 204

    trial_3 = client.post(
        f"/v1/session-trainings/{session_training_id}/trials",
        json={"result": "partial", "prompt_level": "modeling"},
        headers=ctx["headers"],
    )
    assert trial_3.json()["attempt_number"] == 3

    progress = client.get(f"/v1/session-trainings/{session_training_id}/progress", headers=ctx["headers"])
    # Deleted trial 1 must not count towards active calculations (Seção 14.4).
    trials_returned = progress.json()["trials"]
    assert len(trials_returned) == 2


def test_clicking_patient_opens_only_that_patients_history(client, db_session):
    """AC-07 — clicar no paciente em Sessions abre apenas o historico daquele paciente."""
    ctx = register_clinic(client)
    patient_a = _create_patient(client, ctx["headers"], name="Paciente A")
    patient_b = _create_patient(client, ctx["headers"], name="Paciente B")
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    _create_session_with_training(client, ctx["headers"], patient_a["id"], ctx["user"]["id"], str(training.id))
    _create_session_with_training(client, ctx["headers"], patient_b["id"], ctx["user"]["id"], str(training.id))

    history_a = client.get(f"/v1/sessions?patient_id={patient_a['id']}", headers=ctx["headers"])
    assert len(history_a.json()) == 1
    assert history_a.json()[0]["patient_id"] == patient_a["id"]


def test_free_plan_blocks_session_photo_upload(client, db_session):
    """AC-03 — usuario Free nao consegue enviar foto nem por chamada direta de API."""
    ctx = register_clinic(client)
    patient = _create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)

    response = client.post(
        "/v1/sessions",
        json={
            "patient_id": patient["id"],
            "professional_id": ctx["user"]["id"],
            "occurred_at": "2026-07-14T10:00:00Z",
            "training_ids": [str(training.id)],
            "photo_url": "https://example.com/photo.jpg",
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 403


def test_deleted_patient_sessions_do_not_appear_in_history(client, db_session):
    """Seção 16.3 — sessoes de paciente excluido nao podem aparecer nas listas ativas."""
    ctx = register_clinic(client)
    patient = _create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    _create_session_with_training(client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id))

    client.delete(f"/v1/patients/{patient['id']}", headers=ctx["headers"])

    listing = client.get("/v1/sessions", headers=ctx["headers"])
    assert listing.json() == []

    restore_response = client.post(f"/v1/patients/{patient['id']}/restore", headers=ctx["headers"])
    assert restore_response.status_code == 200


def test_free_plan_blocks_session_media_upload(client, db_session, mock_s3):
    """Addendum v3.0, RF-20 — mesmo bloqueio de plano Free já usado para foto."""
    ctx = register_clinic(client)
    patient = _create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = _create_session_with_training(client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id))

    response = client.post(
        f"/v1/sessions/{session['id']}/media",
        files={"file": ("foto.jpg", b"fake-jpeg-bytes", "image/jpeg")},
        headers=ctx["headers"],
    )
    assert response.status_code == 403


def test_paid_plan_uploads_photo_to_session(client, db_session, mock_s3):
    """Addendum v3.0, RF-20 — "Foto" continua funcionando (upload real, não só URL)."""
    ctx = register_clinic(client)
    _make_paid(db_session, ctx["user"]["clinic_id"])
    patient = _create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = _create_session_with_training(client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id))

    response = client.post(
        f"/v1/sessions/{session['id']}/media",
        files={"file": ("foto.jpg", b"fake-jpeg-bytes", "image/jpeg")},
        headers=ctx["headers"],
    )
    assert response.status_code == 200, response.text
    assert response.json()["media_type"] == "photo"

    url_response = client.get(f"/v1/sessions/{session['id']}/media-url", headers=ctx["headers"])
    assert url_response.status_code == 200
    assert url_response.json()["media_type"] == "photo"
    assert url_response.json()["url"].startswith("http")


def test_paid_plan_uploads_short_video_to_session(client, db_session, mock_s3):
    """Addendum v3.0, RF-20 — "campo Foto vira Foto/Vídeo", upload de vídeo curto."""
    ctx = register_clinic(client)
    _make_paid(db_session, ctx["user"]["clinic_id"], plan=SubscriptionPlan.PREMIUM)
    patient = _create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = _create_session_with_training(client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id))

    response = client.post(
        f"/v1/sessions/{session['id']}/media",
        data={"duration_seconds": "20"},
        files={"file": ("clipe.mp4", b"fake-mp4-bytes", "video/mp4")},
        headers=ctx["headers"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["media_type"] == "video"
    assert body["media_duration_seconds"] == 20


def test_video_upload_rejects_duration_over_plan_limit(client, db_session, mock_s3):
    """RF-20 — "limite de duração ... configurável por plano"."""
    ctx = register_clinic(client)
    _make_paid(db_session, ctx["user"]["clinic_id"], plan=SubscriptionPlan.BASIC)
    patient = _create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    session = _create_session_with_training(client, ctx["headers"], patient["id"], ctx["user"]["id"], str(training.id))

    response = client.post(
        f"/v1/sessions/{session['id']}/media",
        data={"duration_seconds": "999"},
        files={"file": ("clipe.mp4", b"fake-mp4-bytes", "video/mp4")},
        headers=ctx["headers"],
    )
    assert response.status_code == 422

    listing_after_restore = client.get("/v1/sessions", headers=ctx["headers"])
    assert len(listing_after_restore.json()) == 1
