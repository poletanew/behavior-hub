import datetime
import uuid

from app.models.enums import PromptLevel, TrialResult
from app.models.patient import Patient
from app.models.session import ClinicalSession, SessionTraining, Trial
from app.models.treatment_plan import Objective
from app.services import clinical_suggestion_service
from tests.conftest import create_patient, create_training, create_training_category, register_clinic


def _create_objective_with_training(client, headers, patient_id, training_id, **overrides):
    payload = {"area": "aba", "title": "Objetivo Sugestao", "training_ids": [str(training_id)]}
    payload.update(overrides)
    response = client.post(f"/v1/patients/{patient_id}/treatment-plan/objectives", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _add_session(db_session, patient_id, professional_id, training_id, occurred_at, trial_specs):
    session = ClinicalSession(patient_id=patient_id, professional_id=professional_id, occurred_at=occurred_at)
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


def _independent_trials(n=5):
    return [(TrialResult.CORRECT, PromptLevel.INDEPENDENT) for _ in range(n)]


def _high_accuracy_trials(n=5):
    return [(TrialResult.CORRECT, PromptLevel.VERBAL) for _ in range(n)]


def test_fading_suggestion_created_and_never_duplicated(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    base = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)
    for i in range(3):
        _add_session(db_session, patient["id"], ctx["user"]["id"], training.id, base + datetime.timedelta(days=i), _independent_trials(3))

    objective_model = db_session.get(Objective, uuid.UUID(objective["id"]))
    created = clinical_suggestion_service.recompute_suggestions_for_objective(db_session, objective_model)
    fading = next((s for s in created if s.suggestion_type.value == "fading"), None)
    assert fading is not None
    assert "reduzir o nível de ajuda" in fading.message

    again = clinical_suggestion_service.recompute_suggestions_for_objective(db_session, objective_model)
    assert all(s.suggestion_type.value != "fading" for s in again)

    listed = client.get(f"/v1/patients/{patient['id']}/suggestions", headers=ctx["headers"]).json()
    fading_entries = [s for s in listed if s["suggestion_type"] == "fading"]
    assert len(fading_entries) == 1


def test_mastery_ready_suggestion_triggers_at_threshold(client, db_session):
    """Seção 29.9 — "Objetivo pode ser considerado dominado com base no critério configurado"."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    base = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)
    for i in range(3):
        _add_session(db_session, patient["id"], ctx["user"]["id"], training.id, base + datetime.timedelta(days=i), _high_accuracy_trials(5))

    objective_model = db_session.get(Objective, uuid.UUID(objective["id"]))
    created = clinical_suggestion_service.recompute_suggestions_for_objective(db_session, objective_model)
    mastery = next((s for s in created if s.suggestion_type.value == "mastery_ready"), None)
    assert mastery is not None
    assert mastery.message == "Objetivo pode ser considerado dominado com base no critério configurado."


def test_mastery_ready_not_suggested_when_already_mastered(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)
    client.patch(f"/v1/objectives/{objective['id']}", json={"status": "mastered"}, headers=ctx["headers"])

    base = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)
    for i in range(3):
        _add_session(db_session, patient["id"], ctx["user"]["id"], training.id, base + datetime.timedelta(days=i), _high_accuracy_trials(5))

    objective_model = db_session.get(Objective, uuid.UUID(objective["id"]))
    created = clinical_suggestion_service.recompute_suggestions_for_objective(db_session, objective_model)
    assert all(s.suggestion_type.value != "mastery_ready" for s in created)


def test_new_program_suggestion_for_uncovered_category(client, db_session):
    """Seção 29.1/29.7 — sugerir novos programas com base em lacunas na área trabalhada."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    worked_category = create_training_category(db_session, name="Comunicacao")
    worked_training = create_training(db_session, worked_category, title="Pedir ajuda")
    _create_objective_with_training(client, ctx["headers"], patient["id"], worked_training.id)

    gap_category = create_training_category(db_session, name="Motor")
    gap_training = create_training(db_session, gap_category, title="Chutar bola")

    patient_model = db_session.get(Patient, uuid.UUID(patient["id"]))
    created = clinical_suggestion_service.recompute_new_program_suggestions(db_session, patient_model)
    new_program = next((s for s in created if s.suggestion_type.value == "new_program"), None)
    assert new_program is not None
    assert new_program.training_id == gap_training.id
    assert "Motor" in new_program.message

    again = clinical_suggestion_service.recompute_new_program_suggestions(db_session, patient_model)
    assert again == []


def test_new_program_no_suggestion_without_worked_baseline(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    create_training(db_session, category)

    patient_model = db_session.get(Patient, uuid.UUID(patient["id"]))
    created = clinical_suggestion_service.recompute_new_program_suggestions(db_session, patient_model)
    assert created == []


def test_approve_suggestion_marks_decided_without_mutating_objective(client, db_session):
    """Toda sugestão é uma recomendação editável — aprovar não altera dados
    clínicos automaticamente, apenas registra a decisão do profissional."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    base = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)
    for i in range(3):
        _add_session(db_session, patient["id"], ctx["user"]["id"], training.id, base + datetime.timedelta(days=i), _high_accuracy_trials(5))
    objective_model = db_session.get(Objective, uuid.UUID(objective["id"]))
    created = clinical_suggestion_service.recompute_suggestions_for_objective(db_session, objective_model)
    mastery = next(s for s in created if s.suggestion_type.value == "mastery_ready")

    response = client.post(f"/v1/suggestions/{mastery.id}/approve", headers=ctx["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["decided_at"] is not None

    unchanged = client.get(f"/v1/objectives/{objective['id']}", headers=ctx["headers"])
    if unchanged.status_code == 200:
        assert unchanged.json()["status"] != "mastered"

    conflict = client.post(f"/v1/suggestions/{mastery.id}/approve", headers=ctx["headers"])
    assert conflict.status_code == 409


def test_dismiss_suggestion(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = _create_objective_with_training(client, ctx["headers"], patient["id"], training.id)

    base = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)
    for i in range(3):
        _add_session(db_session, patient["id"], ctx["user"]["id"], training.id, base + datetime.timedelta(days=i), _high_accuracy_trials(5))
    objective_model = db_session.get(Objective, uuid.UUID(objective["id"]))
    created = clinical_suggestion_service.recompute_suggestions_for_objective(db_session, objective_model)
    mastery = next(s for s in created if s.suggestion_type.value == "mastery_ready")

    response = client.post(f"/v1/suggestions/{mastery.id}/dismiss", headers=ctx["headers"])
    assert response.status_code == 200
    assert response.json()["status"] == "dismissed"


def test_suggestions_tenant_isolation(client):
    clinic_a = register_clinic(client, "Clinica Sugestao A")
    clinic_b = register_clinic(client, "Clinica Sugestao B")
    patient_a = create_patient(client, clinic_a["headers"])

    response = client.get(f"/v1/patients/{patient_a['id']}/suggestions", headers=clinic_b["headers"])
    assert response.status_code == 404
