import datetime

from tests.conftest import (
    auth_headers,
    create_patient,
    create_training,
    create_training_category,
    invite_and_accept,
    invite_and_accept_professional,
    register_clinic,
    unique_email,
)


def _invite_family(client, admin_headers, patient_id):
    return invite_and_accept(client, admin_headers, role="family", patient_id=patient_id)


def _enable_all(client, admin_headers, access_id):
    payload = {
        "can_view_evolution_charts": True,
        "can_view_upcoming_appointments": True,
        "can_view_team_guidance": True,
        "can_view_home_materials": True,
        "can_use_messaging": True,
    }
    response = client.patch(f"/v1/family-accesses/{access_id}", json=payload, headers=admin_headers)
    assert response.status_code == 200, response.text
    return response.json()


def _get_access_id(client, admin_headers, patient_id):
    listed = client.get(f"/v1/patients/{patient_id}/family-accesses", headers=admin_headers).json()
    assert len(listed) == 1
    return listed[0]["id"]


def test_family_invitation_requires_patient_id(client):
    ctx = register_clinic(client)
    email = unique_email("family")
    response = client.post(
        "/v1/invitations", json={"email": email, "role": "family"}, headers=ctx["headers"]
    )
    assert response.status_code == 422


def test_non_family_invitation_rejects_patient_id(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    email = unique_email("professional")
    response = client.post(
        "/v1/invitations",
        json={"email": email, "role": "professional", "patient_id": patient["id"]},
        headers=ctx["headers"],
    )
    assert response.status_code == 422


def test_accept_family_invitation_creates_access_with_whitelist_off(client, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    family = _invite_family(client, ctx["headers"], patient["id"])

    assert family["user"]["user_type"] == "family"

    access_id = _get_access_id(client, ctx["headers"], patient["id"])
    access = client.get(f"/v1/patients/{patient['id']}/family-accesses", headers=ctx["headers"]).json()[0]
    assert access["id"] == access_id
    assert access["consent_given_at"] is not None
    for field in (
        "can_view_evolution_charts",
        "can_view_upcoming_appointments",
        "can_view_team_guidance",
        "can_view_home_materials",
        "can_use_messaging",
    ):
        assert access[field] is False


def test_family_account_blocked_from_normal_patient_routes(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    family = _invite_family(client, ctx["headers"], patient["id"])

    listed = client.get("/v1/patients", headers=family["headers"])
    assert listed.status_code == 403

    direct = client.get(f"/v1/patients/{patient['id']}", headers=family["headers"])
    assert direct.status_code == 403


def test_family_portal_evolution_gated_by_whitelist(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    family = _invite_family(client, ctx["headers"], patient["id"])
    access_id = _get_access_id(client, ctx["headers"], patient["id"])

    before = client.get(f"/v1/family-portal/patients/{patient['id']}/evolution", headers=family["headers"])
    assert before.status_code == 403

    _enable_all(client, ctx["headers"], access_id)

    after = client.get(f"/v1/family-portal/patients/{patient['id']}/evolution", headers=family["headers"])
    assert after.status_code == 200
    body = after.json()
    assert "line" in body and "radar" in body and "cumulative" in body


def test_family_portal_my_accesses_lists_only_shared_categories(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    family = _invite_family(client, ctx["headers"], patient["id"])
    access_id = _get_access_id(client, ctx["headers"], patient["id"])

    client.patch(
        f"/v1/family-accesses/{access_id}",
        json={"can_view_upcoming_appointments": True},
        headers=ctx["headers"],
    )

    my_accesses = client.get("/v1/family-portal/my-accesses", headers=family["headers"]).json()
    assert len(my_accesses) == 1
    assert my_accesses[0]["patient_id"] == patient["id"]
    assert my_accesses[0]["can_view_upcoming_appointments"] is True
    assert my_accesses[0]["can_view_evolution_charts"] is False


def test_family_portal_upcoming_appointments(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    family = _invite_family(client, ctx["headers"], patient["id"])
    access_id = _get_access_id(client, ctx["headers"], patient["id"])
    _enable_all(client, ctx["headers"], access_id)

    admin_id = ctx["user"]["id"]
    future_start = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2)).isoformat()
    future_end = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2, hours=1)).isoformat()
    created = client.post(
        "/v1/appointments",
        json={
            "patient_id": patient["id"],
            "professional_id": admin_id,
            "scheduled_start": future_start,
            "scheduled_end": future_end,
        },
        headers=ctx["headers"],
    )
    assert created.status_code == 201, created.text

    appointments = client.get(
        f"/v1/family-portal/patients/{patient['id']}/appointments", headers=family["headers"]
    ).json()
    assert len(appointments) == 1
    assert appointments[0]["status"] == "scheduled"


def test_family_portal_guidance_only_shows_approved_summaries(client, db_session):
    from app.models.enums import ReportSummaryStatus
    from app.models.report_summary import ReportSummary

    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    family = _invite_family(client, ctx["headers"], patient["id"])
    access_id = _get_access_id(client, ctx["headers"], patient["id"])
    _enable_all(client, ctx["headers"], access_id)

    draft = ReportSummary(
        patient_id=patient["id"],
        period_start=datetime.date(2026, 1, 1),
        period_end=datetime.date(2026, 1, 31),
        content="Rascunho não deve aparecer",
        status=ReportSummaryStatus.DRAFT,
        data_snapshot={},
    )
    approved = ReportSummary(
        patient_id=patient["id"],
        period_start=datetime.date(2026, 2, 1),
        period_end=datetime.date(2026, 2, 28),
        content="Orientação aprovada",
        status=ReportSummaryStatus.APPROVED,
        data_snapshot={},
    )
    db_session.add_all([draft, approved])
    db_session.commit()

    guidance = client.get(
        f"/v1/family-portal/patients/{patient['id']}/guidance", headers=family["headers"]
    ).json()
    assert len(guidance) == 1
    assert guidance[0]["content"] == "Orientação aprovada"


def test_family_portal_home_materials_aggregates_via_objective_training(client, mock_s3, db_session):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    family = _invite_family(client, ctx["headers"], patient["id"])
    access_id = _get_access_id(client, ctx["headers"], patient["id"])
    _enable_all(client, ctx["headers"], access_id)

    category = create_training_category(db_session)
    training = create_training(db_session, category)
    objective = client.post(
        f"/v1/patients/{patient['id']}/treatment-plan/objectives",
        json={"area": "aba", "title": "Objetivo Family", "training_ids": [str(training.id)]},
        headers=ctx["headers"],
    ).json()

    resource = client.post(
        "/v1/resources",
        data={"title": "Historia social", "category": "espera", "visibility": "clinic_shared"},
        files={"file": ("atividade.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        headers=ctx["headers"],
    ).json()
    client.post(
        "/v1/resource-links",
        json={"resource_id": resource["id"], "training_id": str(training.id)},
        headers=ctx["headers"],
    )

    materials = client.get(
        f"/v1/family-portal/patients/{patient['id']}/materials", headers=family["headers"]
    ).json()
    assert len(materials) == 1
    assert materials[0]["resource_title"] == "Historia social"

    _ = objective  # objective creation is what makes the training-link aggregation reachable


def test_family_portal_messaging_both_directions(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    family = _invite_family(client, ctx["headers"], patient["id"])
    access_id = _get_access_id(client, ctx["headers"], patient["id"])
    _enable_all(client, ctx["headers"], access_id)

    sent = client.post(
        f"/v1/family-portal/patients/{patient['id']}/messages",
        json={"body": "Olá, tenho uma dúvida"},
        headers=family["headers"],
    )
    assert sent.status_code == 201, sent.text

    staff_reply = client.post(
        f"/v1/patients/{patient['id']}/family-messages",
        json={"body": "Olá! Vamos conversar na próxima sessão"},
        headers=ctx["headers"],
    )
    assert staff_reply.status_code == 201, staff_reply.text

    from_family = client.get(
        f"/v1/family-portal/patients/{patient['id']}/messages", headers=family["headers"]
    ).json()
    assert len(from_family) == 2

    from_staff = client.get(f"/v1/patients/{patient['id']}/family-messages", headers=ctx["headers"]).json()
    assert len(from_staff) == 2


def test_revoke_family_access_bumps_token_version_and_blocks_immediately(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    family = _invite_family(client, ctx["headers"], patient["id"])
    access_id = _get_access_id(client, ctx["headers"], patient["id"])
    _enable_all(client, ctx["headers"], access_id)

    still_valid = client.get("/v1/family-portal/my-accesses", headers=family["headers"])
    assert still_valid.status_code == 200

    revoked = client.post(f"/v1/family-accesses/{access_id}/revoke", headers=ctx["headers"])
    assert revoked.status_code == 200
    assert revoked.json()["revoked_at"] is not None

    old_token_now_rejected = client.get("/v1/family-portal/my-accesses", headers=family["headers"])
    assert old_token_now_rejected.status_code == 401

    relogin = client.post(
        "/v1/auth/login", json={"email": family["email"], "password": "senha-super-segura-123"}
    )
    assert relogin.status_code == 200
    new_headers = auth_headers(relogin.json())

    still_blocked = client.get(
        f"/v1/family-portal/patients/{patient['id']}/evolution", headers=new_headers
    )
    assert still_blocked.status_code == 404


def test_professional_can_invite_family_only_for_accessible_patient(client):
    ctx = register_clinic(client)
    other_clinic = register_clinic(client, "Outra Clinica")
    other_patient = create_patient(client, other_clinic["headers"])

    email = unique_email("family")
    response = client.post(
        "/v1/invitations",
        json={"email": email, "role": "family", "patient_id": other_patient["id"]},
        headers=ctx["headers"],
    )
    assert response.status_code == 404


def test_family_access_management_tenant_isolation(client):
    ctx = register_clinic(client)
    other_clinic = register_clinic(client, "Outra Clinica Family")
    patient = create_patient(client, ctx["headers"])
    _invite_family(client, ctx["headers"], patient["id"])

    forbidden = client.get(f"/v1/patients/{patient['id']}/family-accesses", headers=other_clinic["headers"])
    assert forbidden.status_code == 404


def test_individual_tenant_can_invite_family(client):
    from tests.conftest import register_individual

    individual = register_individual(client)
    patient = create_patient(client, individual["headers"])
    family = _invite_family(client, individual["headers"], patient["id"])

    access_id = _get_access_id(client, individual["headers"], patient["id"])
    _enable_all(client, individual["headers"], access_id)

    evolution = client.get(
        f"/v1/family-portal/patients/{patient['id']}/evolution", headers=family["headers"]
    )
    assert evolution.status_code == 200
