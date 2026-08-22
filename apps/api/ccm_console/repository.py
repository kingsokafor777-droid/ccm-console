"""Tenant-scoped repository ports and deterministic in-memory adapter for ccm-console."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar

from .models import AssessmentView, CaseState, CaseView, EvidenceReferenceView, WorkUpdateView

T = TypeVar("T")


class CaseConflictError(ValueError):
    """Raised where an optimistic case version is stale."""


class ConsoleRepository(Protocol):
    async def list_assessments(
        self,
        tenant_id: str,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[AssessmentView, ...]: ...

    async def list_evidence(
        self,
        tenant_id: str,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[EvidenceReferenceView, ...]: ...

    async def list_cases(
        self,
        tenant_id: str,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[CaseView, ...]: ...

    async def get_case(self, tenant_id: str, case_id: str) -> CaseView | None: ...

    async def append_update(
        self,
        tenant_id: str,
        case_id: str,
        *,
        actor_subject_id: str,
        expected_version: int,
        message: str,
        created_at: str,
    ) -> WorkUpdateView: ...

    async def reassign_owner(
        self,
        tenant_id: str,
        case_id: str,
        *,
        expected_version: int,
        owner_team: str,
        owner_subject_id: str | None,
    ) -> CaseView: ...


class MemoryConsoleRepository:
    """Deterministic, tenant-filtered adapter for tests and local synthetic demonstrations."""

    def __init__(
        self,
        *,
        assessments: tuple[tuple[str, AssessmentView], ...] = (),
        evidence: tuple[tuple[str, EvidenceReferenceView], ...] = (),
        cases: tuple[tuple[str, CaseView], ...] = (),
        update_id_factory: Callable[[str, int], str] | None = None,
    ) -> None:
        self._assessments = assessments
        self._evidence = evidence
        self._cases: dict[tuple[str, str], CaseView] = {
            (tenant_id, case.case_id): case for tenant_id, case in cases
        }
        self._updates: list[tuple[str, WorkUpdateView]] = []
        self._update_id_factory = update_id_factory or (
            lambda case_id, version: f"work_update_{case_id}_{version}"
        )

    @staticmethod
    def _page(
        rows: tuple[tuple[str, T], ...],
        tenant_id: str,
        cursor: str | None,
        limit: int,
        key: Callable[[T], str],
    ) -> tuple[T, ...]:
        filtered = sorted((item for owner, item in rows if owner == tenant_id), key=key)
        if cursor is not None:
            filtered = [item for item in filtered if key(item) > cursor]
        return tuple(filtered[:limit])

    async def list_assessments(
        self,
        tenant_id: str,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[AssessmentView, ...]:
        return self._page(
            self._assessments,
            tenant_id,
            cursor,
            limit,
            lambda item: item.assessment_id,
        )

    async def list_evidence(
        self,
        tenant_id: str,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[EvidenceReferenceView, ...]:
        return self._page(
            self._evidence,
            tenant_id,
            cursor,
            limit,
            lambda item: item.reference_id,
        )

    async def list_cases(
        self,
        tenant_id: str,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[CaseView, ...]:
        rows = tuple((tenant_id, case) for (tenant_id, _), case in self._cases.items())
        return self._page(
            rows,
            tenant_id,
            cursor,
            limit,
            lambda item: item.case_id,
        )

    async def get_case(self, tenant_id: str, case_id: str) -> CaseView | None:
        return self._cases.get((tenant_id, case_id))

    async def append_update(
        self,
        tenant_id: str,
        case_id: str,
        *,
        actor_subject_id: str,
        expected_version: int,
        message: str,
        created_at: str,
    ) -> WorkUpdateView:
        case = await self.get_case(tenant_id, case_id)
        if case is None:
            raise KeyError(case_id)
        if case.version != expected_version:
            raise CaseConflictError(case_id)
        next_case = case.model_copy(update={"version": case.version + 1})
        self._cases[(tenant_id, case_id)] = next_case
        update = WorkUpdateView(
            update_id=self._update_id_factory(case_id, next_case.version),
            case_id=case_id,
            actor_subject_id=actor_subject_id,
            message=message,
            created_at=created_at,
            case_version=next_case.version,
        )
        self._updates.append((tenant_id, update))
        return update

    async def reassign_owner(
        self,
        tenant_id: str,
        case_id: str,
        *,
        expected_version: int,
        owner_team: str,
        owner_subject_id: str | None,
    ) -> CaseView:
        case = await self.get_case(tenant_id, case_id)
        if case is None:
            raise KeyError(case_id)
        if case.version != expected_version:
            raise CaseConflictError(case_id)
        next_case = case.model_copy(
            update={
                "owner_team": owner_team,
                "owner_subject_id": owner_subject_id,
                "version": case.version + 1,
            }
        )
        self._cases[(tenant_id, case_id)] = next_case
        return next_case


def severity_rank(value: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1, "informational": 0}[value]


def is_open_case(case: CaseView) -> bool:
    return case.state in {CaseState.ACTIVE, CaseState.PENDING_CLOSURE}
