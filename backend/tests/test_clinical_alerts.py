import datetime
import uuid

from app.models.clinic import Clinic
from app.models.enums import (
    ClinicalAlertType,
    ObjectiveStatus,
    PromptLevel,
    SubscriptionPlan,
    TrialResult,
)
from app.models.session import ClinicalSession, SessionTraining, Trial
from app.models.treatment_plan import Objective
from app.services import clinical_alert_service
from tests.conftest import (
    assign_professional,
    create_patient,
    create_training,
    create_training_category,
    invite_and_accept,
    register_clinic,
)


def _create_objective_with_training(client, headers, patient_id, training_id, **overrides):
    payload = {"area": "aba", "title": "Objetivo Alertas", "training_ids": [str(training_id)]}
    payload.update(overrides)
    response = client.post(f"/v1/patients/{patient_id}/treatment-plan/objectives", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _add_session(db_session, patient_id, professional_id, training_id, occurred_at, trial_specs):
    """trial_specs: list of (TrialResult, PromptLevel) tuples, one per trial."""
    session = ClinicalSession(
        patient_id=patient_id,
        professional_id=professional_id,
        occurred_at=occurred_at,
    )
    # Match tenant scope of the patient.
    from app.models.patient import Patient

    patient = db_session.get(Patient, patient_id)
    session.clinic_id = patient.clinic_id
    session.individual_owner_id = patient.individual_owner_id
    db_session.add(session)
    db_session.flush()

    session_training = SessionTraining(session_id=session.id, training_id=training_id, sequence=1)
    db_session.add(session_training)
    db_session.flush()

    now = datetime.datetime.now(datetime.timezone.utc)
    for idx, (result, prompt_level) in enumerate(trial_specs, start=1):
        db_session.add(
            Trial(
                session_training_id=session_training.id,
                attempt_number=idx,
                result=result,
                prompt_level=prompt_level,
                recorded_at=now,
            )
        )
    db_session.commit()


def _high_accuracy_trials(n=5):
    return [(TrialResult.CORRECT, PromptLevel.VERBAL) for _ in range(n)]


def _low_accuracy_trials(n=5, correct=1):
    return [(TrialResult.CORRECT, PromptLevel.VERBAL) if i < correct else (TrialResult.INCORRECT, PromptLevel.VERBAL) for i in range(n)]


def _independent_trials(n=5):
    return [(TrialResult.CORRECT, PromptLevel.INDEPENDENT) for _ in range(n)]


def test_regression_alert_matches_ac16_formula(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    base = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10)
    for i in range(3):
        _add_session(
            db_session, patient["id"], ctx["user"]["id"], training.id, base + datetime.timedelta(days=i), _high_accuracy_trials(5)
        )
    for i in range(3, 6):
        _add_session(
            db_session,
            patient["id"],
            ctx["user"]["id"],
            training.id,
            base + datetime.timedelta(days=i),
            _low_accuracy_trials(5, correct=1),
        )

    objective_model = db_session.get(Objective, uuid.UUID(objective["id"]))
    new_alerts = clinical_alert_service.recompute_alerts_for_objective(db_session, objective_model)

    regression = next((a for a in new_alerts if a.alert_type == ClinicalAlertType.REGRESSION), None)
    assert regression is not None, [a.alert_type for a in new_alerts]
    assert regression.detail["previous_avg_pct"] == 100.0
    assert regression.detail["recent_avg_pct"] == 20.0
    assert regression.detail["drop_pp"] == 80.0

    response = client.get(f"/v1/patients/{patient['id']}/alerts", headers=ctx["headers"])
    assert response.status_code == 200
    assert any(a["alert_type"] == "regression" for a in response.json())


def test_regression_alert_does_not_trigger_below_threshold(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    base = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10)
    # Only a 10pp drop (below the 20pp default threshold)
    for i in range(3):
        _add_session(db_session, patient["id"], ctx["user"]["id"], training.id, base + datetime.timedelta(days=i), _low_accuracy_trials(10, correct=8))
    for i in range(3, 6):
        _add_session(db_session, patient["id"], ctx["user"]["id"], training.id, base + datetime.timedelta(days=i), _low_accuracy_trials(10, correct=7))

    objective_model = db_session.get(Objective, uuid.UUID(objective["id"]))
    new_alerts = clinical_alert_service.recompute_alerts_for_objective(db_session, objective_model)
    assert all(a.alert_type != ClinicalAlertType.REGRESSION for a in new_alerts)


def test_stagnation_alert_triggers_when_accuracy_flat(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    base = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)
    for i in range(5):
        _add_session(db_session, patient["id"], ctx["user"]["id"], training.id, base + datetime.timedelta(days=i), _low_accuracy_trials(10, correct=5))

    objective_model = db_session.get(Objective, uuid.UUID(objective["id"]))
    new_alerts = clinical_alert_service.recompute_alerts_for_objective(db_session, objective_model)
    stagnation = next((a for a in new_alerts if a.alert_type == ClinicalAlertType.STAGNATION), None)
    assert stagnation is not None
    assert stagnation.detail["range_pp"] == 0.0


def test_mastered_objective_never_gets_stagnation_alert(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    client.patch(f"/v1/objectives/{objective['id']}", json={"status": "mastered"}, headers=ctx["headers"])

    base = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)
    for i in range(5):
        _add_session(db_session, patient["id"], ctx["user"]["id"], training.id, base + datetime.timedelta(days=i), _low_accuracy_trials(10, correct=5))

    objective_model = db_session.get(Objective, uuid.UUID(objective["id"]))
    new_alerts = clinical_alert_service.recompute_alerts_for_objective(db_session, objective_model)
    assert all(a.alert_type != ClinicalAlertType.STAGNATION for a in new_alerts)


def test_fading_candidate_alert_triggers_on_high_independence(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    base = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)
    for i in range(3):
        _add_session(db_session, patient["id"], ctx["user"]["id"], training.id, base + datetime.timedelta(days=i), _independent_trials(5))

    objective_model = db_session.get(Objective, uuid.UUID(objective["id"]))
    new_alerts = clinical_alert_service.recompute_alerts_for_objective(db_session, objective_model)
    fading = next((a for a in new_alerts if a.alert_type == ClinicalAlertType.FADING_CANDIDATE), None)
    assert fading is not None
    assert all(v == 100.0 for v in fading.detail["independence_values_pct"])


def test_no_collection_alert_triggers_and_resolves_on_new_trial(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    old_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=20)
    _add_session(db_session, patient["id"], ctx["user"]["id"], training.id, old_date, _high_accuracy_trials(3))

    objective_model = db_session.get(Objective, uuid.UUID(objective["id"]))
    new_alerts = clinical_alert_service.recompute_alerts_for_objective(db_session, objective_model)
    no_collection = next((a for a in new_alerts if a.alert_type == ClinicalAlertType.NO_COLLECTION), None)
    assert no_collection is not None
    assert no_collection.detail["days_since_last_trial"] > 14

    # A fresh trial today should resolve the no-collection alert.
    _add_session(
        db_session, patient["id"], ctx["user"]["id"], training.id, datetime.datetime.now(datetime.timezone.utc), _high_accuracy_trials(3)
    )
    clinical_alert_service.recompute_alerts_for_objective(db_session, objective_model)

    active = client.get(f"/v1/patients/{patient['id']}/alerts", headers=ctx["headers"]).json()
    assert all(a["alert_type"] != "no_collection" for a in active)


def test_alert_deduplication_no_duplicate_active_alert(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    old_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=20)
    _add_session(db_session, patient["id"], ctx["user"]["id"], training.id, old_date, _high_accuracy_trials(3))

    objective_model = db_session.get(Objective, uuid.UUID(objective["id"]))
    first = clinical_alert_service.recompute_alerts_for_objective(db_session, objective_model)
    assert len(first) == 1

    second = clinical_alert_service.recompute_alerts_for_objective(db_session, objective_model)
    assert len(second) == 0  # already active, not a new trigger

    active_alerts = client.get(f"/v1/patients/{patient['id']}/alerts", headers=ctx["headers"]).json()
    no_collection_alerts = [a for a in active_alerts if a["alert_type"] == "no_collection"]
    assert len(no_collection_alerts) == 1


def test_discontinued_objective_resolves_active_alerts(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    old_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=20)
    _add_session(db_session, patient["id"], ctx["user"]["id"], training.id, old_date, _high_accuracy_trials(3))

    objective_model = db_session.get(Objective, uuid.UUID(objective["id"]))
    clinical_alert_service.recompute_alerts_for_objective(db_session, objective_model)
    assert client.get(f"/v1/patients/{patient['id']}/alerts", headers=ctx["headers"]).json()

    client.patch(f"/v1/objectives/{objective['id']}", json={"status": "discontinued"}, headers=ctx["headers"])
    db_session.refresh(objective_model)
    clinical_alert_service.recompute_alerts_for_objective(db_session, objective_model)

    active_alerts = client.get(f"/v1/patients/{patient['id']}/alerts", headers=ctx["headers"]).json()
    assert active_alerts == []


def test_objective_without_linked_training_never_alerts(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    response = client.post(
        f"/v1/patients/{patient['id']}/treatment-plan/objectives",
        json={"area": "aba", "title": "Sem treino vinculado"},
        headers=ctx["headers"],
    )
    objective_model = db_session.get(Objective, uuid.UUID(response.json()["id"]))
    new_alerts = clinical_alert_service.recompute_alerts_for_objective(db_session, objective_model)
    assert new_alerts == []


def test_notification_sent_to_supervisor_and_assigned_professional(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    supervisor = invite_and_accept(client, ctx["headers"], role="supervisor")
    professional = invite_and_accept(client, ctx["headers"], role="professional", specialty="fonoaudiologo")
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"])

    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    old_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=20)
    _add_session(db_session, patient["id"], ctx["user"]["id"], training.id, old_date, _high_accuracy_trials(3))

    objective_model = db_session.get(Objective, uuid.UUID(objective["id"]))
    clinical_alert_service.recompute_alerts_for_objective(db_session, objective_model)

    admin_notifications = client.get("/v1/notifications", headers=ctx["headers"]).json()
    assert any(n["type"] == "clinical_alert" for n in admin_notifications)

    supervisor_notifications = client.get("/v1/notifications", headers=supervisor["headers"]).json()
    assert any(n["type"] == "clinical_alert" for n in supervisor_notifications)

    professional_notifications = client.get("/v1/notifications", headers=professional["headers"]).json()
    assert any(n["type"] == "clinical_alert" for n in professional_notifications)


def test_tenant_isolation_alerts_not_visible_cross_clinic(client, db_session):
    clinic_a = register_clinic(client, "Clinica Alertas A")
    clinic_b = register_clinic(client, "Clinica Alertas B")
    patient_a = create_patient(client, clinic_a["headers"], name="Paciente A")

    response = client.get(f"/v1/patients/{patient_a['id']}/alerts", headers=clinic_b["headers"])
    assert response.status_code == 404


def test_threshold_update_requires_enterprise_plan_and_admin(client, db_session):
    ctx = register_clinic(client)

    forbidden = client.patch("/v1/clinic/alert-thresholds", json={"no_collection_days": 21}, headers=ctx["headers"])
    assert forbidden.status_code == 403

    clinic = db_session.query(Clinic).filter(Clinic.id == ctx["user"]["clinic_id"]).first()
    clinic.subscription_plan = SubscriptionPlan.ENTERPRISE
    db_session.commit()

    professional = invite_and_accept(client, ctx["headers"], role="professional")
    forbidden_non_admin = client.patch(
        "/v1/clinic/alert-thresholds", json={"no_collection_days": 21}, headers=professional["headers"]
    )
    assert forbidden_non_admin.status_code == 403

    allowed = client.patch("/v1/clinic/alert-thresholds", json={"no_collection_days": 21}, headers=ctx["headers"])
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["no_collection_days"] == 21


def test_default_thresholds_match_prd_factory_defaults(client):
    ctx = register_clinic(client)
    response = client.get("/v1/clinic/permission-settings", headers=ctx["headers"])
    body = response.json()
    assert body["no_collection_days"] == 14
    assert body["regression_window_sessions"] == 3
    assert body["regression_drop_pp"] == 20
    assert body["stagnation_session_count"] == 5
    assert body["stagnation_band_pp"] == 5
    assert body["fading_session_count"] == 3
    assert body["fading_independence_pct"] == 80
