from app.models.user import User
from tests.conftest import create_patient, invite_and_accept, invite_and_accept_professional, register_clinic


def _assign(client, admin_headers, patient_id, professional_id):
    response = client.post(
        f"/v1/patients/{patient_id}/assignments",
        json={"professional_id": professional_id},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response


def test_invite_and_accept_at_role_sets_supervisor(client, db_session):
    """Addendum v2.1, RF-11 — o AT criado via convite fica vinculado ao
    supervisor/admin que gerou o convite."""
    ctx = register_clinic(client)
    at = invite_and_accept(client, ctx["headers"], role="at")
    assert at["user"]["user_type"] == "at"

    at_row = db_session.query(User).filter(User.id == at["user"]["id"]).first()
    assert str(at_row.supervisor_id) == ctx["user"]["id"]


def test_supervisor_can_assign_at_to_patient(client):
    ctx = register_clinic(client)
    supervisor = invite_and_accept(client, ctx["headers"], role="supervisor")
    at = invite_and_accept(client, ctx["headers"], role="at")
    patient = create_patient(client, ctx["headers"])

    response = client.post(
        f"/v1/patients/{patient['id']}/assignments",
        json={"professional_id": at["user"]["id"]},
        headers=supervisor["headers"],
    )
    assert response.status_code == 201, response.text


def test_professional_cannot_assign_patients(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])
    at = invite_and_accept(client, ctx["headers"], role="at")
    patient = create_patient(client, ctx["headers"])

    response = client.post(
        f"/v1/patients/{patient['id']}/assignments",
        json={"professional_id": at["user"]["id"]},
        headers=professional["headers"],
    )
    assert response.status_code == 403


def test_at_sees_only_assigned_patients(client):
    ctx = register_clinic(client)
    at = invite_and_accept(client, ctx["headers"], role="at")
    assigned = create_patient(client, ctx["headers"], name="Paciente Atribuido")
    not_assigned = create_patient(client, ctx["headers"], name="Paciente Nao Atribuido")
    _assign(client, ctx["headers"], assigned["id"], at["user"]["id"])

    response = client.get("/v1/at-portal/patients", headers=at["headers"])
    assert response.status_code == 200
    names = {p["name"] for p in response.json()}
    assert names == {"Paciente Atribuido"}
    assert not_assigned["id"] not in [p["id"] for p in response.json()]


def test_at_cannot_access_general_patient_endpoints(client):
    ctx = register_clinic(client)
    at = invite_and_accept(client, ctx["headers"], role="at")
    patient = create_patient(client, ctx["headers"])
    _assign(client, ctx["headers"], patient["id"], at["user"]["id"])

    list_response = client.get("/v1/patients", headers=at["headers"])
    assert list_response.status_code == 403

    detail_response = client.get(f"/v1/patients/{patient['id']}", headers=at["headers"])
    assert detail_response.status_code == 403


def test_at_cannot_access_treatment_plan_or_reports(client):
    ctx = register_clinic(client)
    at = invite_and_accept(client, ctx["headers"], role="at")
    patient = create_patient(client, ctx["headers"])
    _assign(client, ctx["headers"], patient["id"], at["user"]["id"])

    plan_response = client.get(f"/v1/patients/{patient['id']}/treatment-plan", headers=at["headers"])
    assert plan_response.status_code == 403

    reports_response = client.get(f"/v1/reports/patients/{patient['id']}", headers=at["headers"])
    assert reports_response.status_code == 403


def test_at_sees_prescribed_training_and_can_apply_and_register_trial(client, db_session):
    from tests.conftest import create_training, create_training_category

    ctx = register_clinic(client)
    at = invite_and_accept(client, ctx["headers"], role="at")
    patient = create_patient(client, ctx["headers"])
    _assign(client, ctx["headers"], patient["id"], at["user"]["id"])

    category = create_training_category(db_session)
    training = create_training(db_session, category)

    link_response = client.post(
        f"/v1/trainings/{training.id}/link", json={"patient_id": patient["id"]}, headers=ctx["headers"]
    )
    assert link_response.status_code == 201

    trainings_response = client.get(
        f"/v1/at-portal/patients/{patient['id']}/trainings", headers=at["headers"]
    )
    assert trainings_response.status_code == 200
    assert trainings_response.json()[0]["status"] == "prescribed"

    apply_response = client.post(
        f"/v1/at-portal/patients/{patient['id']}/apply",
        json={"training_id": str(training.id), "occurred_at": "2026-07-21T10:00:00Z"},
        headers=at["headers"],
    )
    assert apply_response.status_code == 201, apply_response.text
    session_training_id = apply_response.json()["trainings"][0]["id"]

    trial_response = client.post(
        f"/v1/session-trainings/{session_training_id}/trials",
        json={"result": "correct", "prompt_level": "independent"},
        headers=at["headers"],
    )
    assert trial_response.status_code == 201, trial_response.text

    trainings_after = client.get(
        f"/v1/at-portal/patients/{patient['id']}/trainings", headers=at["headers"]
    ).json()
    assert trainings_after[0]["status"] == "applied"


def test_at_cannot_apply_training_not_linked_to_patient(client, db_session):
    from tests.conftest import create_training, create_training_category

    ctx = register_clinic(client)
    at = invite_and_accept(client, ctx["headers"], role="at")
    patient = create_patient(client, ctx["headers"])
    _assign(client, ctx["headers"], patient["id"], at["user"]["id"])

    category = create_training_category(db_session)
    training = create_training(db_session, category)

    response = client.post(
        f"/v1/at-portal/patients/{patient['id']}/apply",
        json={"training_id": str(training.id), "occurred_at": "2026-07-21T10:00:00Z"},
        headers=at["headers"],
    )
    assert response.status_code == 403


def test_at_cannot_access_unassigned_patient_via_portal(client):
    ctx = register_clinic(client)
    at = invite_and_accept(client, ctx["headers"], role="at")
    patient = create_patient(client, ctx["headers"])

    response = client.get(f"/v1/at-portal/patients/{patient['id']}/trainings", headers=at["headers"])
    assert response.status_code == 404


def test_aba_admin_lists_ats_and_their_patients(client):
    ctx = register_clinic(client)
    at = invite_and_accept(client, ctx["headers"], role="at")
    patient = create_patient(client, ctx["headers"])
    _assign(client, ctx["headers"], patient["id"], at["user"]["id"])

    ats_response = client.get("/v1/aba/ats", headers=ctx["headers"])
    assert ats_response.status_code == 200
    at_summary = next(a for a in ats_response.json() if a["id"] == at["user"]["id"])
    assert at_summary["assigned_patient_count"] == 1

    patients_response = client.get(f"/v1/aba/ats/{at['user']['id']}/patients", headers=ctx["headers"])
    assert patients_response.status_code == 200
    assert patients_response.json()[0]["id"] == patient["id"]


def test_aba_admin_review_shows_at_trials(client, db_session):
    from tests.conftest import create_training, create_training_category

    ctx = register_clinic(client)
    at = invite_and_accept(client, ctx["headers"], role="at")
    patient = create_patient(client, ctx["headers"])
    _assign(client, ctx["headers"], patient["id"], at["user"]["id"])

    category = create_training_category(db_session)
    training = create_training(db_session, category)
    client.post(f"/v1/trainings/{training.id}/link", json={"patient_id": patient["id"]}, headers=ctx["headers"])

    apply_response = client.post(
        f"/v1/at-portal/patients/{patient['id']}/apply",
        json={"training_id": str(training.id), "occurred_at": "2026-07-21T10:00:00Z"},
        headers=at["headers"],
    )
    session_training_id = apply_response.json()["trainings"][0]["id"]
    client.post(
        f"/v1/session-trainings/{session_training_id}/trials",
        json={"result": "correct", "prompt_level": "independent"},
        headers=at["headers"],
    )

    review_response = client.get("/v1/aba/trials", headers=ctx["headers"])
    assert review_response.status_code == 200
    entry = review_response.json()[0]
    assert entry["at_user_id"] == at["user"]["id"]
    assert entry["patient_id"] == patient["id"]
    assert entry["training_id"] == str(training.id)


def test_professional_cannot_access_aba_admin_endpoints(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    response = client.get("/v1/aba/ats", headers=professional["headers"])
    assert response.status_code == 403


def test_at_cannot_use_aba_admin_endpoints(client):
    ctx = register_clinic(client)
    at = invite_and_accept(client, ctx["headers"], role="at")

    response = client.get("/v1/aba/ats", headers=at["headers"])
    assert response.status_code == 403
