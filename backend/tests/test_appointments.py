import datetime

from tests.conftest import (
    assign_professional,
    create_patient,
    invite_and_accept_professional,
    register_clinic,
    register_individual,
)


def _iso(dt: datetime.datetime) -> str:
    return dt.isoformat()


def _create_appointment(client, headers, patient_id, professional_id, start, end, **overrides):
    payload = {
        "patient_id": patient_id,
        "professional_id": professional_id,
        "scheduled_start": _iso(start),
        "scheduled_end": _iso(end),
    }
    payload.update(overrides)
    return client.post("/v1/appointments", json=payload, headers=headers)


def test_create_appointment_success(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    start = datetime.datetime(2026, 8, 3, 10, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=50)

    response = _create_appointment(client, ctx["headers"], patient["id"], ctx["user"]["id"], start, end)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["patient_name"] == patient["name"]


def test_conflict_detection_blocks_overlapping_appointment(client):
    ctx = register_clinic(client)
    patient_a = create_patient(client, ctx["headers"], name="Paciente A")
    patient_b = create_patient(client, ctx["headers"], name="Paciente B")
    start = datetime.datetime(2026, 8, 3, 14, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=50)

    first = _create_appointment(client, ctx["headers"], patient_a["id"], ctx["user"]["id"], start, end)
    assert first.status_code == 201

    overlap_start = start + datetime.timedelta(minutes=20)
    overlap_end = overlap_start + datetime.timedelta(minutes=50)
    conflicting = _create_appointment(
        client, ctx["headers"], patient_b["id"], ctx["user"]["id"], overlap_start, overlap_end
    )
    assert conflicting.status_code == 409

    non_overlapping = _create_appointment(client, ctx["headers"], patient_b["id"], ctx["user"]["id"], end, end + datetime.timedelta(minutes=50))
    assert non_overlapping.status_code == 201


def test_cancelled_appointment_frees_conflict_slot(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    start = datetime.datetime(2026, 8, 4, 9, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=30)

    first = _create_appointment(client, ctx["headers"], patient["id"], ctx["user"]["id"], start, end)
    appointment_id = first.json()["id"]

    cancel = client.post(
        f"/v1/appointments/{appointment_id}/cancel", json={"reason": "clinic", "notes": "reagendado"}, headers=ctx["headers"]
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
    assert cancel.json()["cancellation_reason"] == "clinic"

    second = _create_appointment(client, ctx["headers"], patient["id"], ctx["user"]["id"], start, end)
    assert second.status_code == 201


def test_confirm_and_no_show_flow(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    start = datetime.datetime(2026, 8, 5, 11, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=30)

    created = _create_appointment(client, ctx["headers"], patient["id"], ctx["user"]["id"], start, end)
    appointment_id = created.json()["id"]

    confirmed = client.post(f"/v1/appointments/{appointment_id}/confirm", headers=ctx["headers"])
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    no_show = client.post(
        f"/v1/appointments/{appointment_id}/no-show", json={"reason": "patient"}, headers=ctx["headers"]
    )
    assert no_show.status_code == 200
    assert no_show.json()["status"] == "no_show"

    # Already no-show: cannot cancel anymore.
    cancel_again = client.post(
        f"/v1/appointments/{appointment_id}/cancel", json={"reason": "clinic"}, headers=ctx["headers"]
    )
    assert cancel_again.status_code == 409


def test_consecutive_no_shows_notify_admin_and_supervisor(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    supervisor = invite_and_accept_professional(client, ctx["headers"])
    # Re-invite as supervisor role via direct helper to get supervisor type
    from tests.conftest import invite_and_accept

    supervisor = invite_and_accept(client, ctx["headers"], role="supervisor")

    base = datetime.datetime(2026, 8, 6, 9, 0, tzinfo=datetime.timezone.utc)
    ids = []
    for i in range(2):
        start = base + datetime.timedelta(days=i)
        end = start + datetime.timedelta(minutes=30)
        created = _create_appointment(client, ctx["headers"], patient["id"], ctx["user"]["id"], start, end)
        ids.append(created.json()["id"])

    for appointment_id in ids:
        response = client.post(
            f"/v1/appointments/{appointment_id}/no-show", json={"reason": "patient"}, headers=ctx["headers"]
        )
        assert response.status_code == 200

    admin_notifications = client.get("/v1/notifications", headers=ctx["headers"]).json()
    assert any(n["type"] == "attendance_alert" for n in admin_notifications)

    supervisor_notifications = client.get("/v1/notifications", headers=supervisor["headers"]).json()
    assert any(n["type"] == "attendance_alert" for n in supervisor_notifications)


def test_tenant_isolation(client):
    clinic_a = register_clinic(client, "Clinica A")
    clinic_b = register_clinic(client, "Clinica B")
    patient_a = create_patient(client, clinic_a["headers"], name="Paciente A")
    start = datetime.datetime(2026, 8, 7, 10, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=30)

    created = _create_appointment(client, clinic_a["headers"], patient_a["id"], clinic_a["user"]["id"], start, end)
    appointment_id = created.json()["id"]

    response = client.get(f"/v1/appointments?patient_id={patient_a['id']}", headers=clinic_b["headers"])
    assert response.status_code == 404  # patient not accessible cross-tenant

    list_b = client.get("/v1/appointments", headers=clinic_b["headers"])
    assert all(a["id"] != appointment_id for a in list_b.json())


def test_professional_sees_only_assigned_patient_appointments(client):
    ctx = register_clinic(client)
    patient_assigned = create_patient(client, ctx["headers"], name="Atribuido")
    patient_other = create_patient(client, ctx["headers"], name="Outro")
    professional = invite_and_accept_professional(client, ctx["headers"])
    assign_professional(client, ctx["headers"], patient_assigned["id"], professional["user"]["id"])

    start = datetime.datetime(2026, 8, 8, 10, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=30)
    _create_appointment(client, ctx["headers"], patient_assigned["id"], professional["user"]["id"], start, end)
    _create_appointment(
        client, ctx["headers"], patient_other["id"], ctx["user"]["id"], start + datetime.timedelta(hours=2), start + datetime.timedelta(hours=3)
    )

    visible = client.get("/v1/appointments", headers=professional["headers"]).json()
    patient_ids = {a["patient_id"] for a in visible}
    assert patient_assigned["id"] in patient_ids
    assert patient_other["id"] not in patient_ids


def test_mark_completed_via_session_creation_links_appointment(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    start = datetime.datetime(2026, 8, 9, 10, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=30)

    created = _create_appointment(client, ctx["headers"], patient["id"], ctx["user"]["id"], start, end)
    appointment_id = created.json()["id"]

    session_response = client.post(
        "/v1/sessions",
        json={
            "patient_id": patient["id"],
            "professional_id": ctx["user"]["id"],
            "occurred_at": _iso(start),
            "appointment_id": appointment_id,
        },
        headers=ctx["headers"],
    )
    assert session_response.status_code == 201, session_response.text
    session_id = session_response.json()["id"]

    appointment = client.get("/v1/appointments", headers=ctx["headers"]).json()
    match = next(a for a in appointment if a["id"] == appointment_id)
    assert match["status"] == "completed"
    assert match["session_id"] == session_id


def test_soft_delete_and_restore_via_deleted_data(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    start = datetime.datetime(2026, 8, 10, 10, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=30)

    created = _create_appointment(client, ctx["headers"], patient["id"], ctx["user"]["id"], start, end)
    appointment_id = created.json()["id"]

    delete_response = client.delete(f"/v1/appointments/{appointment_id}", headers=ctx["headers"])
    assert delete_response.status_code == 204

    deleted_items = client.get("/v1/deleted-data", headers=ctx["headers"]).json()
    match = next(i for i in deleted_items if i["entity_type"] == "appointment" and i["id"] == appointment_id)
    assert match["days_remaining"] in (59, 60)

    restore_response = client.post(f"/v1/deleted-data/appointment/{appointment_id}/restore", headers=ctx["headers"])
    assert restore_response.status_code == 200

    visible = client.get("/v1/appointments", headers=ctx["headers"]).json()
    assert any(a["id"] == appointment_id for a in visible)


def test_attendance_rate_calculation(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    base = datetime.datetime(2026, 8, 11, 9, 0, tzinfo=datetime.timezone.utc)

    completed_start = base
    completed_end = completed_start + datetime.timedelta(minutes=30)
    completed_appt = _create_appointment(
        client, ctx["headers"], patient["id"], ctx["user"]["id"], completed_start, completed_end
    ).json()
    client.post(
        "/v1/sessions",
        json={
            "patient_id": patient["id"],
            "professional_id": ctx["user"]["id"],
            "occurred_at": _iso(completed_start),
            "appointment_id": completed_appt["id"],
        },
        headers=ctx["headers"],
    )

    no_show_start = base + datetime.timedelta(days=1)
    no_show_end = no_show_start + datetime.timedelta(minutes=30)
    no_show_appt = _create_appointment(
        client, ctx["headers"], patient["id"], ctx["user"]["id"], no_show_start, no_show_end
    ).json()
    client.post(f"/v1/appointments/{no_show_appt['id']}/no-show", json={"reason": "patient"}, headers=ctx["headers"])

    rate_response = client.get(f"/v1/appointments/attendance-rate/{patient['id']}", headers=ctx["headers"])
    assert rate_response.status_code == 200
    body = rate_response.json()
    assert body["completed_count"] == 1
    assert body["no_show_count"] == 1
    assert body["attendance_rate_pct"] == 50.0


def test_ics_export(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    start = datetime.datetime(2026, 8, 12, 10, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=30)
    _create_appointment(client, ctx["headers"], patient["id"], ctx["user"]["id"], start, end)

    response = client.get("/v1/appointments/export.ics", headers=ctx["headers"])
    assert response.status_code == 200
    assert "text/calendar" in response.headers["content-type"]
    assert "BEGIN:VCALENDAR" in response.text
    assert "BEGIN:VEVENT" in response.text


def test_individual_account_can_schedule_own_appointments(client):
    ctx = register_individual(client)
    patient = create_patient(client, ctx["headers"])
    start = datetime.datetime(2026, 8, 13, 10, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=30)

    response = _create_appointment(client, ctx["headers"], patient["id"], ctx["user"]["id"], start, end)
    assert response.status_code == 201


def test_update_appointment_reschedule_respects_conflicts(client):
    ctx = register_clinic(client)
    patient_a = create_patient(client, ctx["headers"], name="A")
    patient_b = create_patient(client, ctx["headers"], name="B")
    start_a = datetime.datetime(2026, 8, 14, 9, 0, tzinfo=datetime.timezone.utc)
    end_a = start_a + datetime.timedelta(minutes=30)
    start_b = datetime.datetime(2026, 8, 14, 11, 0, tzinfo=datetime.timezone.utc)
    end_b = start_b + datetime.timedelta(minutes=30)

    appt_a = _create_appointment(client, ctx["headers"], patient_a["id"], ctx["user"]["id"], start_a, end_a).json()
    appt_b = _create_appointment(client, ctx["headers"], patient_b["id"], ctx["user"]["id"], start_b, end_b).json()

    conflict_update = client.patch(
        f"/v1/appointments/{appt_b['id']}",
        json={"scheduled_start": _iso(start_a), "scheduled_end": _iso(end_a)},
        headers=ctx["headers"],
    )
    assert conflict_update.status_code == 409

    ok_update = client.patch(
        f"/v1/appointments/{appt_b['id']}",
        json={"scheduled_start": _iso(end_a), "scheduled_end": _iso(end_a + datetime.timedelta(minutes=30))},
        headers=ctx["headers"],
    )
    assert ok_update.status_code == 200
