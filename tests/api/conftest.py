from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from ccm_console.app import ConsoleApplication, create_app
from ccm_console.auth import DevelopmentHmacTokenVerifier, issue_development_token
from ccm_console.models import (
    AssessmentStatus,
    AssessmentView,
    CaseState,
    CaseView,
    CoverageStatus,
    EvidenceReferenceView,
    Principal,
    Role,
    Severity,
)
from ccm_console.repository import MemoryConsoleRepository

SECRET = "local-test-secret-only-and-never-a-production-key"
ISSUER = "ccm-console-test"
AUDIENCE = "ccm-console-api"
NOW_EPOCH = 1_800_000_000
HASH_A = "sha256:" + ("a" * 64)
HASH_B = "sha256:" + ("b" * 64)


@pytest.fixture()
def client() -> TestClient:
    repository = MemoryConsoleRepository(
        assessments=(
            (
                "tenant_alpha",
                AssessmentView(
                    assessment_id="assessment_alpha",
                    control_id="identity_mfa_coverage",
                    control_version="1.0.0",
                    status=AssessmentStatus.FAIL,
                    coverage=CoverageStatus.PARTIAL,
                    severity=Severity.HIGH,
                    source_manifest_hash=HASH_A,
                    assessed_at="2026-08-21T00:00:00Z",
                ),
            ),
            (
                "tenant_beta",
                AssessmentView(
                    assessment_id="assessment_beta",
                    control_id="storage_encryption",
                    control_version="1.0.0",
                    status=AssessmentStatus.PASS,
                    coverage=CoverageStatus.COMPLETE,
                    severity=Severity.LOW,
                    source_manifest_hash=HASH_B,
                    assessed_at="2026-08-21T00:00:00Z",
                ),
            ),
        ),
        evidence=(
            (
                "tenant_alpha",
                EvidenceReferenceView(
                    reference_id="reference_alpha",
                    evidence_id="evidence_alpha",
                    evidence_hash=HASH_A,
                    collector_id="collector_identity",
                    control_id="identity_mfa_coverage",
                    observed_at="2026-08-21T00:00:00Z",
                    availability=CoverageStatus.UNAVAILABLE,
                    source_manifest_hash=HASH_A,
                ),
            ),
        ),
        cases=(
            (
                "tenant_alpha",
                CaseView(
                    case_id="case_alpha",
                    control_id="identity_mfa_coverage",
                    control_version="1.0.0",
                    state=CaseState.ACTIVE,
                    severity=Severity.HIGH,
                    owner_team="cloud_security",
                    source_case_manifest_hash=HASH_A,
                    version=1,
                ),
            ),
            (
                "tenant_beta",
                CaseView(
                    case_id="case_beta",
                    control_id="storage_encryption",
                    control_version="1.0.0",
                    state=CaseState.CLOSED,
                    severity=Severity.LOW,
                    owner_team="platform_operations",
                    source_case_manifest_hash=HASH_B,
                    version=1,
                ),
            ),
        ),
    )
    verifier = DevelopmentHmacTokenVerifier(
        secret=SECRET,
        issuer=ISSUER,
        audience=AUDIENCE,
        now_epoch=lambda: NOW_EPOCH,
    )
    app = create_app(
        ConsoleApplication(
            repository=repository,
            verifier=verifier,
            now=lambda: "2026-08-22T00:00:00Z",
            correlation_id=lambda: "corr_test",
            allowed_origins=("http://localhost:3000",),
        )
    )
    return TestClient(app)


@pytest.fixture()
def token() -> Callable[[str, Role, bool], str]:
    def factory(tenant_id: str, role: Role, expired: bool = False) -> str:
        return issue_development_token(
            Principal(tenant_id=tenant_id, subject_id="subject_alex", role=role),
            secret=SECRET,
            issuer=ISSUER,
            audience=AUDIENCE,
            expires_at_epoch=NOW_EPOCH - 1 if expired else NOW_EPOCH + 3600,
        )

    return factory


def bearer(value: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {value}"}
