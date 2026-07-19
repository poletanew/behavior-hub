from tests.conftest import create_patient, register_clinic


def test_list_protocol_definitions(client):
    ctx = register_clinic(client)
    response = client.get("/v1/assessment-protocols", headers=ctx["headers"])
    assert response.status_code == 200
    protocols = {p["protocol"] for p in response.json()}
    assert protocols == {"vb_mapp", "ablls_r"}
    vb_mapp = next(p for p in response.json() if p["protocol"] == "vb_mapp")
    assert vb_mapp["requires_license"] is True
    assert sum(d["max_value"] for d in vb_mapp["domains"]) == 170
    assert len(vb_mapp["domains"]) == 16


def test_create_assessment_computes_normalized_pct(client):
    """Seção 30.1.1 — normalized_pct = raw_value / max_value x 100."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    response = client.post(
        f"/v1/patients/{patient['id']}/assessments",
        json={
            "protocol": "vb_mapp",
            "applied_date": "2026-01-15",
            "domain_scores": [
                {"domain_code": "mando", "raw_value": 9},
                {"domain_code": "tato", "raw_value": 15},
            ],
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    mando = next(d for d in body["raw_scores"] if d["domain_code"] == "mando")
    assert mando["max_value"] == 15
    assert mando["normalized_pct"] == 60.0
    tato = next(d for d in body["raw_scores"] if d["domain_code"] == "tato")
    assert tato["normalized_pct"] == 100.0


def test_create_assessment_rejects_unknown_domain_code(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    response = client.post(
        f"/v1/patients/{patient['id']}/assessments",
        json={
            "protocol": "vb_mapp",
            "applied_date": "2026-01-15",
            "domain_scores": [{"domain_code": "nao_existe", "raw_value": 5}],
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 400


def test_create_assessment_requires_max_value_when_no_default(client):
    """ABLLS-R não tem max_value padrão (Seção 30.1.1) — o profissional deve informar."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    missing = client.post(
        f"/v1/patients/{patient['id']}/assessments",
        json={
            "protocol": "ablls_r",
            "applied_date": "2026-01-15",
            "domain_scores": [{"domain_code": "a", "raw_value": 10}],
        },
        headers=ctx["headers"],
    )
    assert missing.status_code == 400

    provided = client.post(
        f"/v1/patients/{patient['id']}/assessments",
        json={
            "protocol": "ablls_r",
            "applied_date": "2026-01-15",
            "domain_scores": [{"domain_code": "a", "raw_value": 10, "max_value": 20}],
        },
        headers=ctx["headers"],
    )
    assert provided.status_code == 201, provided.text
    assert provided.json()["raw_scores"][0]["normalized_pct"] == 50.0


def test_create_assessment_rejects_raw_value_exceeding_max(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    response = client.post(
        f"/v1/patients/{patient['id']}/assessments",
        json={
            "protocol": "vb_mapp",
            "applied_date": "2026-01-15",
            "domain_scores": [{"domain_code": "mando", "raw_value": 20}],
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 400


def test_duplicate_assessment_same_protocol_and_date_conflicts(client):
    """Seção 27.3 — unicidade de protocol + applied_date + patient_id."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    payload = {
        "protocol": "vb_mapp",
        "applied_date": "2026-01-15",
        "domain_scores": [{"domain_code": "mando", "raw_value": 9}],
    }
    first = client.post(f"/v1/patients/{patient['id']}/assessments", json=payload, headers=ctx["headers"])
    assert first.status_code == 201

    second = client.post(f"/v1/patients/{patient['id']}/assessments", json=payload, headers=ctx["headers"])
    assert second.status_code == 409


def test_list_assessments_ordered_by_applied_date(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    for applied_date in ["2026-07-01", "2026-01-01", "2026-04-01"]:
        client.post(
            f"/v1/patients/{patient['id']}/assessments",
            json={"protocol": "vb_mapp", "applied_date": applied_date, "domain_scores": [{"domain_code": "mando", "raw_value": 5}]},
            headers=ctx["headers"],
        )

    listed = client.get(f"/v1/patients/{patient['id']}/assessments", headers=ctx["headers"]).json()
    dates = [a["applied_date"] for a in listed]
    assert dates == sorted(dates)


def test_compare_assessments_computes_gain_per_domain(client):
    """Seção 30.2/AC-19 — ganho absoluto e percentual por domínio usando normalized_pct."""
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])

    first = client.post(
        f"/v1/patients/{patient['id']}/assessments",
        json={
            "protocol": "vb_mapp",
            "applied_date": "2026-01-01",
            "domain_scores": [{"domain_code": "mando", "raw_value": 3}],
        },
        headers=ctx["headers"],
    ).json()
    second = client.post(
        f"/v1/patients/{patient['id']}/assessments",
        json={
            "protocol": "vb_mapp",
            "applied_date": "2026-07-01",
            "domain_scores": [{"domain_code": "mando", "raw_value": 9}],
        },
        headers=ctx["headers"],
    ).json()

    response = client.get(
        f"/v1/patients/{patient['id']}/assessments/compare",
        params={"protocol": "vb_mapp", "assessment_ids": [first["id"], second["id"]]},
        headers=ctx["headers"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    mando = next(d for d in body["domains"] if d["domain_code"] == "mando")
    assert mando["earliest_pct"] == 20.0
    assert mando["latest_pct"] == 60.0
    assert mando["gain_absolute_pp"] == 40.0
    assert mando["gain_relative_pct"] == 200.0
    assert "diagn" not in body["interpretive_summary"].lower() or "não constitui diagnóstico" in body["interpretive_summary"]


def test_compare_requires_at_least_two_assessments(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    only = client.post(
        f"/v1/patients/{patient['id']}/assessments",
        json={"protocol": "vb_mapp", "applied_date": "2026-01-01", "domain_scores": [{"domain_code": "mando", "raw_value": 3}]},
        headers=ctx["headers"],
    ).json()

    response = client.get(
        f"/v1/patients/{patient['id']}/assessments/compare",
        params={"protocol": "vb_mapp", "assessment_ids": [only["id"]]},
        headers=ctx["headers"],
    )
    assert response.status_code == 400


def test_soft_delete_and_restore_via_deleted_data(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    assessment = client.post(
        f"/v1/patients/{patient['id']}/assessments",
        json={"protocol": "vb_mapp", "applied_date": "2026-01-01", "domain_scores": [{"domain_code": "mando", "raw_value": 3}]},
        headers=ctx["headers"],
    ).json()

    delete_response = client.delete(f"/v1/assessments/{assessment['id']}", headers=ctx["headers"])
    assert delete_response.status_code == 204

    deleted_items = client.get("/v1/deleted-data", headers=ctx["headers"]).json()
    match = next(i for i in deleted_items if i["entity_type"] == "assessment" and i["id"] == assessment["id"])
    assert match["days_remaining"] in (59, 60)

    restore_response = client.post(f"/v1/deleted-data/assessment/{assessment['id']}/restore", headers=ctx["headers"])
    assert restore_response.status_code == 200

    visible = client.get(f"/v1/patients/{patient['id']}/assessments", headers=ctx["headers"]).json()
    assert any(a["id"] == assessment["id"] for a in visible)


def test_assessment_appears_in_timeline(client):
    ctx = register_clinic(client)
    patient = create_patient(client, ctx["headers"])
    client.post(
        f"/v1/patients/{patient['id']}/assessments",
        json={"protocol": "vb_mapp", "applied_date": "2026-03-10", "domain_scores": [{"domain_code": "mando", "raw_value": 3}]},
        headers=ctx["headers"],
    )

    timeline = client.get(f"/v1/patients/{patient['id']}/timeline", headers=ctx["headers"]).json()
    assessment_events = [e for e in timeline if e["event_type"] == "assessment_applied"]
    assert len(assessment_events) == 1
    assert "VB-MAPP" in assessment_events[0]["label"]


def test_assessments_tenant_isolation(client):
    clinic_a = register_clinic(client, "Clinica Avaliacao A")
    clinic_b = register_clinic(client, "Clinica Avaliacao B")
    patient_a = create_patient(client, clinic_a["headers"])
    assessment = client.post(
        f"/v1/patients/{patient_a['id']}/assessments",
        json={"protocol": "vb_mapp", "applied_date": "2026-01-01", "domain_scores": [{"domain_code": "mando", "raw_value": 3}]},
        headers=clinic_a["headers"],
    ).json()

    forbidden_list = client.get(f"/v1/patients/{patient_a['id']}/assessments", headers=clinic_b["headers"])
    assert forbidden_list.status_code == 404

    forbidden_get = client.get(f"/v1/assessments/{assessment['id']}", headers=clinic_b["headers"])
    assert forbidden_get.status_code == 404
