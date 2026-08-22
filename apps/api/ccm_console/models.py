"""Strict safe-view contracts for ccm-console's tenant-scoped API boundary."""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
STABLE_ID = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
StableId = Annotated[str, StringConstraints(pattern=STABLE_ID.pattern)]
UtcTime = Annotated[str, StringConstraints(pattern=UTC.pattern)]
SafeText = Annotated[str, StringConstraints(min_length=1, max_length=512)]


class StrictModel(BaseModel):
    """Stable public models: no coercion and no undeclared response properties."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Role(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class AssessmentStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    NOT_ASSESSED = "not_assessed"
    ERROR = "error"


class CoverageStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class CaseState(str, Enum):
    ACTIVE = "active"
    PENDING_CLOSURE = "pending_closure"
    CLOSED = "closed"
    REJECTED = "rejected"


class Principal(StrictModel):
    tenant_id: StableId
    subject_id: StableId
    role: Role


class AssessmentView(StrictModel):
    assessment_id: StableId
    control_id: StableId
    control_version: SafeText
    status: AssessmentStatus
    coverage: CoverageStatus
    severity: Severity
    source_manifest_hash: str
    assessed_at: UtcTime

    @field_validator("source_manifest_hash")
    @classmethod
    def _validate_source_hash(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("source manifest hash must be sha256:<64 lowercase hex>")
        return value


class EvidenceReferenceView(StrictModel):
    reference_id: StableId
    evidence_id: StableId
    evidence_hash: str
    collector_id: StableId
    control_id: StableId
    observed_at: UtcTime
    availability: CoverageStatus
    source_manifest_hash: str

    @field_validator("evidence_hash", "source_manifest_hash")
    @classmethod
    def _validate_hashes(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("hash must be sha256:<64 lowercase hex>")
        return value


class CaseView(StrictModel):
    case_id: StableId
    control_id: StableId
    control_version: SafeText
    state: CaseState
    severity: Severity
    owner_team: SafeText
    owner_subject_id: StableId | None = None
    due_at: UtcTime | None = None
    source_case_manifest_hash: str
    version: Annotated[int, Field(ge=1)]

    @field_validator("source_case_manifest_hash")
    @classmethod
    def _validate_case_hash(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("source case manifest hash must be sha256:<64 lowercase hex>")
        return value


class WorkUpdateCreate(StrictModel):
    expected_version: Annotated[int, Field(ge=1)]
    message: Annotated[str, StringConstraints(min_length=1, max_length=1000)]


class OwnerReassignment(StrictModel):
    expected_version: Annotated[int, Field(ge=1)]
    owner_team: SafeText
    owner_subject_id: StableId | None = None


class WorkUpdateView(StrictModel):
    update_id: StableId
    case_id: StableId
    actor_subject_id: StableId
    message: Annotated[str, StringConstraints(min_length=1, max_length=1000)]
    created_at: UtcTime
    case_version: Annotated[int, Field(ge=1)]


class Overview(StrictModel):
    assessment_count: Annotated[int, Field(ge=0)]
    case_count: Annotated[int, Field(ge=0)]
    open_case_count: Annotated[int, Field(ge=0)]
    failing_assessment_count: Annotated[int, Field(ge=0)]
    partial_coverage_count: Annotated[int, Field(ge=0)]
    unavailable_evidence_count: Annotated[int, Field(ge=0)]
    highest_open_severity: Severity | None = None
    generated_at: UtcTime


class AssessmentPage(StrictModel):
    items: tuple[AssessmentView, ...]
    next_cursor: StableId | None = None


class EvidencePage(StrictModel):
    items: tuple[EvidenceReferenceView, ...]
    next_cursor: StableId | None = None


class CasePage(StrictModel):
    items: tuple[CaseView, ...]
    next_cursor: StableId | None = None


class ApiError(StrictModel):
    code: SafeText
    correlation_id: SafeText
    detail: SafeText
