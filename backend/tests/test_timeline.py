import datetime

from tests.conftest import (
    assign_professional,
    create_patient,
    invite_and_accept_professional,
    register_clinic,
)


def test_timeline_empty_for_new_patient(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    response = client.get(f"/v1/patients/{patient['id']}/timeline", headers=ctx["headers"])
    assert response.status_code == 200
    assert response.json() == []


def test_timeline_includes_session_completed(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    occurred_at = datetime.datetime(2026, 6, 1, 10, 0, tzinfo=datetime.timezone.utc)
    session_response = client.post(
        "/v1/sessions",
        json={"patient_id": patient["id"], "professional_id": ctx["user"]["id"], "occurred_at": occurred_at.isoformat()},
        headers=ctx["headers"],
    )
    assert session_response.status_code == 201, session_response.text

    timeline = client.get(f"/v1/patients/{patient['id']}/timeline", headers=ctx["headers"]).json()
    session_events = [e for e in timeline if e["event_type"] == "session_completed"]
    assert len(session_events) == 1
    assert ctx["user"]["name"] in session_events[0]["label"]


def test_timeline_includes_objective_lifecycle_events(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    create_response = client.post(
        f"/v1/patients/{patient['id']}/treatment-plan/objectives",
        json={"area": "aba", "title": "Objetivo Timeline"},
        headers=ctx["headers"],
    )
    objective = create_response.json()

    client.patch(f"/v1/objectives/{objective['id']}", json={"priority": "high"}, headers=ctx["headers"])
    client.delete(f"/v1/objectives/{objective['id']}", headers=ctx["headers"])
    client.post(f"/v1/objectives/{objective['id']}/restore", headers=ctx["headers"])

    timeline = client.get(f"/v1/patients/{patient['id']}/timeline", headers=ctx["headers"]).json()
    event_types = [e["event_type"] for e in timeline if e["source_id"] == objective["id"]]
    assert "objective_created" in event_types
    assert "objective_updated" in event_types
    assert "objective_deleted" in event_types
    assert "objective_restored" in event_types


def test_timeline_objective_mastered_is_a_distinct_milestone(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    objective = client.post(
        f"/v1/patients/{patient['id']}/treatment-plan/objectives",
        json={"area": "aba", "title": "Objetivo Dominado"},
        headers=ctx["headers"],
    ).json()

    client.patch(f"/v1/objectives/{objective['id']}", json={"status": "mastered"}, headers=ctx["headers"])

    timeline = client.get(f"/v1/patients/{patient['id']}/timeline", headers=ctx["headers"]).json()
    milestone_events = [e for e in timeline if e["event_type"] == "objective_mastered"]
    assert len(milestone_events) == 1
    generic_update_events = [
        e for e in timeline if e["event_type"] == "objective_updated" and e["source_id"] == objective["id"]
    ]
    assert generic_update_events == []


def test_timeline_includes_professional_assignment_changes(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    professional = invite_and_accept_professional(client, ctx["headers"])

    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"])
    client.delete(
        f"/v1/patients/{patient['id']}/assignments/{professional['user']['id']}", headers=ctx["headers"]
    )

    timeline = client.get(f"/v1/patients/{patient['id']}/timeline", headers=ctx["headers"]).json()
    labels = [e["label"] for e in timeline]
    assert any("vinculado" in label and professional["user"]["name"] in label for label in labels)
    assert any("desvinculado" in label and professional["user"]["name"] in label for label in labels)


def test_timeline_includes_report_generated(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    response = client.post(
        f"/v1/reports/patients/{patient['id']}/summary/generate",
        json={"period_start": "2026-01-01", "period_end": "2026-06-01"},
        headers=ctx["headers"],
    )
    assert response.status_code == 201, response.text

    timeline = client.get(f"/v1/patients/{patient['id']}/timeline", headers=ctx["headers"]).json()
    report_events = [e for e in timeline if e["event_type"] == "report_generated"]
    assert len(report_events) == 1
    assert "versão 1" in report_events[0]["label"]


def test_timeline_is_chronologically_ordered_without_duplicates(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    client.post(
        f"/v1/patients/{patient['id']}/treatment-plan/objectives",
        json={"area": "aba", "title": "Objetivo A"},
        headers=ctx["headers"],
    )
    early = datetime.datetime(2026, 1, 1, 9, 0, tzinfo=datetime.timezone.utc)
    late = datetime.datetime(2026, 6, 1, 9, 0, tzinfo=datetime.timezone.utc)
    client.post(
        "/v1/sessions",
        json={"patient_id": patient["id"], "professional_id": ctx["user"]["id"], "occurred_at": late.isoformat()},
        headers=ctx["headers"],
    )
    client.post(
        "/v1/sessions",
        json={"patient_id": patient["id"], "professional_id": ctx["user"]["id"], "occurred_at": early.isoformat()},
        headers=ctx["headers"],
    )

    timeline = client.get(f"/v1/patients/{patient['id']}/timeline", headers=ctx["headers"]).json()
    timestamps = [e["occurred_at"] for e in timeline]
    assert timestamps == sorted(timestamps)

    ids = [e["id"] for e in timeline]
    assert len(ids) == len(set(ids))


def test_timeline_tenant_isolation(client):
    clinic_a = register_clinic(client, "Clinica Timeline A")
    clinic_b = register_clinic(client, "Clinica Timeline B")
    patient_a = create_patient(client, clinic_a["headers"], name="Paciente A")

    response = client.get(f"/v1/patients/{patient_a['id']}/timeline", headers=clinic_b["headers"])
    assert response.status_code == 404
