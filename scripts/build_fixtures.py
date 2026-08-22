"""Build synthetic, payload-blind ccm-console records for tests and frontend preview only."""

from __future__ import annotations

import json
from pathlib import Path

from ccm_console.models import (
    AssessmentStatus,
    AssessmentView,
    CaseState,
    CaseView,
    CoverageStatus,
    EvidenceReferenceView,
    Severity,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
HASH_A = "sha256:" + ("a" * 64)
HASH_B = "sha256:" + ("b" * 64)
HASH_C = "sha256:" + ("c" * 64)


def build() -> dict[str, object]:
    assessments = (
        AssessmentView(
            assessment_id="assessment_identity_mfa",
            control_id="identity_mfa_coverage",
            control_version="1.0.0",
            status=AssessmentStatus.PARTIAL,
            coverage=CoverageStatus.COMPLETE,
            severity=Severity.HIGH,
            source_manifest_hash=HASH_A,
            assessed_at="2026-08-21T00:00:00Z",
        ),
        AssessmentView(
            assessment_id="assessment_storage_encryption",
            control_id="storage_encryption",
            control_version="1.0.0",
            status=AssessmentStatus.PASS,
            coverage=CoverageStatus.COMPLETE,
            severity=Severity.MEDIUM,
            source_manifest_hash=HASH_B,
            assessed_at="2026-08-21T00:00:00Z",
        ),
        AssessmentView(
            assessment_id="assessment_logging_coverage",
            control_id="logging_coverage",
            control_version="1.0.0",
            status=AssessmentStatus.NOT_ASSESSED,
            coverage=CoverageStatus.UNAVAILABLE,
            severity=Severity.LOW,
            source_manifest_hash=HASH_C,
            assessed_at="2026-08-21T00:00:00Z",
        ),
    )
    evidence = (
        EvidenceReferenceView(
            reference_id="reference_identity_mfa",
            evidence_id="evidence_identity_mfa",
            evidence_hash=HASH_A,
            collector_id="collector_aws_identity",
            control_id="identity_mfa_coverage",
            observed_at="2026-08-21T00:00:00Z",
            availability=CoverageStatus.COMPLETE,
            source_manifest_hash=HASH_A,
        ),
        EvidenceReferenceView(
            reference_id="reference_storage_encryption",
            evidence_id="evidence_storage_encryption",
            evidence_hash=HASH_B,
            collector_id="collector_aws_storage",
            control_id="storage_encryption",
            observed_at="2026-08-21T00:00:00Z",
            availability=CoverageStatus.COMPLETE,
            source_manifest_hash=HASH_B,
        ),
        EvidenceReferenceView(
            reference_id="reference_logging_unavailable",
            evidence_id="evidence_logging_unavailable",
            evidence_hash=HASH_C,
            collector_id="collector_aws_logging",
            control_id="logging_coverage",
            observed_at="2026-08-21T00:00:00Z",
            availability=CoverageStatus.UNAVAILABLE,
            source_manifest_hash=HASH_C,
        ),
    )
    cases = (
        CaseView(
            case_id="case_identity_mfa",
            control_id="identity_mfa_coverage",
            control_version="1.0.0",
            state=CaseState.ACTIVE,
            severity=Severity.HIGH,
            owner_team="cloud_security",
            owner_subject_id="operator_alex",
            due_at="2026-08-30T00:00:00Z",
            source_case_manifest_hash=HASH_A,
            version=3,
        ),
        CaseView(
            case_id="case_logging_coverage",
            control_id="logging_coverage",
            control_version="1.0.0",
            state=CaseState.PENDING_CLOSURE,
            severity=Severity.MEDIUM,
            owner_team="platform_operations",
            due_at="2026-09-05T00:00:00Z",
            source_case_manifest_hash=HASH_C,
            version=2,
        ),
    )
    return {
        "tenant_id": "demo_tenant",
        "generated_at": "2026-08-22T00:00:00Z",
        "synthetic": True,
        "assessments": [item.model_dump(mode="json") for item in assessments],
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "cases": [item.model_dump(mode="json") for item in cases],
    }


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    output = json.dumps(build(), indent=2, ensure_ascii=False, sort_keys=True)
    (FIXTURES / "synthetic-console-view.json").write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
