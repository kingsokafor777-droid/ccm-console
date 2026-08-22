from __future__ import annotations

from fastapi.testclient import TestClient

from ccm_console.models import Role

from .conftest import bearer


def test_health_is_explicitly_storage_neutral(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "storage": "not_checked"}


def test_overview_requires_valid_unexpired_bearer_token(client: TestClient, token) -> None:
    missing = client.get("/v1/overview")
    assert missing.status_code == 401
    expired = client.get("/v1/overview", headers=bearer(token("tenant_alpha", Role.VIEWER, True)))
    assert expired.status_code == 401
    assert expired.json()["detail"] == "expired bearer token"


def test_overview_is_tenant_scoped_and_does_not_infer_pass(client: TestClient, token) -> None:
    response = client.get("/v1/overview", headers=bearer(token("tenant_alpha", Role.VIEWER)))
    assert response.status_code == 200
    assert response.json() == {
        "assessment_count": 1,
        "case_count": 1,
        "open_case_count": 1,
        "failing_assessment_count": 1,
        "partial_coverage_count": 1,
        "unavailable_evidence_count": 1,
        "highest_open_severity": "high",
        "generated_at": "2026-08-22T00:00:00Z",
    }
    beta = client.get("/v1/overview", headers=bearer(token("tenant_beta", Role.VIEWER)))
    assert beta.status_code == 200
    assert beta.json()["assessment_count"] == 1
    assert beta.json()["failing_assessment_count"] == 0


def test_evidence_is_payload_blind_and_pagination_is_bounded(client: TestClient, token) -> None:
    headers = bearer(token("tenant_alpha", Role.VIEWER))
    response = client.get("/v1/evidence?limit=1", headers=headers)
    assert response.status_code == 200
    evidence = response.json()["items"][0]
    assert set(evidence) == {
        "reference_id",
        "evidence_id",
        "evidence_hash",
        "collector_id",
        "control_id",
        "observed_at",
        "availability",
        "source_manifest_hash",
    }
    invalid = client.get("/v1/evidence?limit=101", headers=headers)
    assert invalid.status_code == 422
    assert invalid.json()["detail"] == "request validation failed"


def test_assessment_and_case_lists_use_bounded_tenant_scoped_routes(
    client: TestClient,
    token,
) -> None:
    headers = bearer(token("tenant_alpha", Role.VIEWER))
    assessments = client.get("/v1/assessments?limit=1", headers=headers)
    assert assessments.status_code == 200
    assert assessments.json()["items"][0]["assessment_id"] == "assessment_alpha"
    cases = client.get("/v1/cases?limit=1", headers=headers)
    assert cases.status_code == 200
    assert cases.json()["items"][0]["case_id"] == "case_alpha"


def test_case_object_access_is_tenant_scoped(client: TestClient, token) -> None:
    response = client.get(
        "/v1/cases/case_beta",
        headers=bearer(token("tenant_alpha", Role.VIEWER)),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "case not found"


def test_workbench_roles_and_optimistic_concurrency(client: TestClient, token) -> None:
    viewer = bearer(token("tenant_alpha", Role.VIEWER))
    forbidden = client.post(
        "/v1/cases/case_alpha/updates",
        headers=viewer,
        json={"expected_version": 1, "message": "reviewed evidence reference"},
    )
    assert forbidden.status_code == 403
    operator = bearer(token("tenant_alpha", Role.OPERATOR))
    created = client.post(
        "/v1/cases/case_alpha/updates",
        headers=operator,
        json={"expected_version": 1, "message": "reviewed evidence reference"},
    )
    assert created.status_code == 201
    assert created.json()["case_version"] == 2
    stale = client.post(
        "/v1/cases/case_alpha/updates",
        headers=operator,
        json={"expected_version": 1, "message": "stale update"},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"] == "stale case version"
    missing = client.post(
        "/v1/cases/case_missing/updates",
        headers=operator,
        json={"expected_version": 1, "message": "safe update"},
    )
    assert missing.status_code == 404


def test_owner_reassignment_requires_reviewer_and_uses_correlation_id(
    client: TestClient,
    token,
) -> None:
    operator = bearer(token("tenant_alpha", Role.OPERATOR))
    forbidden = client.patch(
        "/v1/cases/case_alpha/owner",
        headers=operator,
        json={"expected_version": 1, "owner_team": "platform_operations"},
    )
    assert forbidden.status_code == 403
    reviewer = bearer(token("tenant_alpha", Role.REVIEWER))
    response = client.patch(
        "/v1/cases/case_alpha/owner",
        headers={**reviewer, "X-Correlation-ID": "corr_supplied"},
        json={"expected_version": 1, "owner_team": "platform_operations"},
    )
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "corr_supplied"
    assert response.json()["owner_team"] == "platform_operations"
    assert response.json()["version"] == 2
    missing = client.patch(
        "/v1/cases/case_missing/owner",
        headers=reviewer,
        json={"expected_version": 1, "owner_team": "platform_operations"},
    )
    assert missing.status_code == 404
