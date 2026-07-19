import datetime

from tests.conftest import (
    assign_professional,
    create_patient,
    invite_and_accept,
    invite_and_accept_professional,
    register_clinic,
    register_individual,
)


def _create_appointment(client, headers, patient_id, professional_id, start, end):
    response = client.post(
        "/v1/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "scheduled_start": start.isoformat(),
            "scheduled_end": end.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _complete_via_session(client, headers, patient_id, professional_id, appointment_id, occurred_at):
    response = client.post(
        "/v1/sessions",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "occurred_at": occurred_at.isoformat(),
            "appointment_id": appointment_id,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_manager_dashboard_forbidden_for_supervisor(client):
    ctx = register_clinic(client)
    supervisor = invite_and_accept(client, ctx["headers"], role="supervisor")

    response = client.get("/v1/clinic/manager-dashboard", headers=supervisor["headers"])
    assert response.status_code == 403


def test_manager_dashboard_forbidden_for_professional(client):
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])

    response = client.get("/v1/clinic/manager-dashboard", headers=professional["headers"])
    assert response.status_code == 403


def test_manager_dashboard_forbidden_for_individual_account(client):
    ctx = register_individual(client)

    response = client.get("/v1/clinic/manager-dashboard", headers=ctx["headers"])
    assert response.status_code == 403


def test_manager_dashboard_counts_active_patients_and_professionals(client):
    """Seção 29.5 — quantidade de pacientes ativos e profissionais ativos."""
    ctx = register_clinic(client)
    invite_and_accept_professional(client, ctx["headers"])
    invite_and_accept(client, ctx["headers"], role="supervisor")
    create_patient(client, ctx["headers"], name="Paciente Ativo 1")
    inactive_patient = create_patient(client, ctx["headers"], name="Paciente a Excluir")
    client.delete(f"/v1/patients/{inactive_patient['id']}", headers=ctx["headers"])

    data = client.get("/v1/clinic/manager-dashboard", headers=ctx["headers"]).json()
    assert data["active_patients_count"] == 1
    assert data["active_professionals_count"] == 2


def test_manager_dashboard_sessions_and_clinical_hours_in_period(client):
    """Seção 29.5 — sessões realizadas e horas clínicas registradas no período."""
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])
    patient = create_patient(client, ctx["headers"])
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"])

    start = datetime.datetime(2026, 6, 10, 9, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=30)
    appt = _create_appointment(client, professional["headers"], patient["id"], professional["user"]["id"], start, end)
    _complete_via_session(client, professional["headers"], patient["id"], professional["user"]["id"], appt["id"], start)

    # A session without a linked appointment still counts toward sessions_count
    # but contributes no duration, since ClinicalSession has no duration field.
    client.post(
        "/v1/sessions",
        json={
            "patient_id": patient["id"],
            "professional_id": professional["user"]["id"],
            "occurred_at": (start + datetime.timedelta(days=1)).isoformat(),
        },
        headers=professional["headers"],
    )

    data = client.get(
        "/v1/clinic/manager-dashboard?date_from=2026-06-01&date_to=2026-06-30", headers=ctx["headers"]
    ).json()
    assert data["sessions_count"] == 2
    assert data["clinical_hours"] == 0.5


def test_manager_dashboard_computes_occupancy_rate(client):
    """Seção 29.5 — indicador de ocupação: completas / (completas + faltas + canceladas)."""
    ctx = register_clinic(client)
    professional = invite_and_accept_professional(client, ctx["headers"])
    patient = create_patient(client, ctx["headers"])
    assign_professional(client, ctx["headers"], patient["id"], professional["user"]["id"])

    base = datetime.datetime(2026, 6, 10, 9, 0, tzinfo=datetime.timezone.utc)
    completed_appt = _create_appointment(
        client, professional["headers"], patient["id"], professional["user"]["id"], base, base + datetime.timedelta(minutes=30)
    )
    _complete_via_session(client, professional["headers"], patient["id"], professional["user"]["id"], completed_appt["id"], base)

    no_show_start = base + datetime.timedelta(days=1)
    no_show_appt = _create_appointment(
        client,
        professional["headers"],
        patient["id"],
        professional["user"]["id"],
        no_show_start,
        no_show_start + datetime.timedelta(minutes=30),
    )
    client.post(
        f"/v1/appointments/{no_show_appt['id']}/no-show", json={"reason": "patient"}, headers=professional["headers"]
    )

    data = client.get(
        "/v1/clinic/manager-dashboard?date_from=2026-06-01&date_to=2026-06-30", headers=ctx["headers"]
    ).json()
    assert data["occupancy_rate_pct"] == 50.0


def test_manager_dashboard_default_period_is_current_month(client):
    ctx = register_clinic(client)
    today = datetime.date.today()

    data = client.get("/v1/clinic/manager-dashboard", headers=ctx["headers"]).json()
    assert data["period_start"] == today.replace(day=1).isoformat()
    assert data["period_end"] == today.isoformat()


def test_manager_dashboard_tenant_isolation(client):
    clinic_a = register_clinic(client, "Clinica Gestor A")
    clinic_b = register_clinic(client, "Clinica Gestor B")
    create_patient(client, clinic_a["headers"], name="Paciente Clinica A")
    invite_and_accept_professional(client, clinic_a["headers"])

    data_b = client.get("/v1/clinic/manager-dashboard", headers=clinic_b["headers"]).json()
    assert data_b["active_patients_count"] == 0
    assert data_b["active_professionals_count"] == 0
