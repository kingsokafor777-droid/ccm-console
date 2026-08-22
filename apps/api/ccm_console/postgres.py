"""Parameterized asyncpg repository enforcing tenant predicates and RLS context per operation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

import asyncpg
from pydantic import BaseModel

from .models import AssessmentView, CaseView, EvidenceReferenceView, WorkUpdateView
from .repository import CaseConflictError, ConsoleRepository

ModelType = TypeVar("ModelType", bound=BaseModel)

_ASSESSMENT_COLUMNS = """
assessment_id, control_id, control_version, status, coverage, severity, source_manifest_hash,
to_char(assessed_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS assessed_at
"""
_EVIDENCE_COLUMNS = """
reference_id, evidence_id, evidence_hash, collector_id, control_id,
to_char(observed_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS observed_at,
availability, source_manifest_hash
"""
_CASE_COLUMNS = """
case_id, control_id, control_version, state, severity, owner_team, owner_subject_id,
CASE WHEN due_at IS NULL THEN NULL
ELSE to_char(due_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
END AS due_at,
source_case_manifest_hash, version
"""


def _model(model: type[ModelType], row: Mapping[str, Any]) -> ModelType:
    return model.model_validate(dict(row), strict=False)


class AsyncpgConsoleRepository(ConsoleRepository):
    """Runtime adapter; deployers supply PostgreSQL network, TLS, credentials, and migrations."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._pool: asyncpg.Pool | None = None

    async def startup(self) -> None:
        self._pool = await asyncpg.create_pool(
            dsn=self._database_url,
            min_size=1,
            max_size=10,
            command_timeout=10,
        )

    async def shutdown(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _pool_or_raise(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("database repository has not started")
        return self._pool

    async def _fetch(
        self,
        tenant_id: str,
        query: str,
        *arguments: object,
    ) -> list[asyncpg.Record]:
        async with self._pool_or_raise().acquire() as connection, connection.transaction():
            await connection.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)
            rows = await connection.fetch(query, tenant_id, *arguments)
            return cast(list[asyncpg.Record], rows)

    async def list_assessments(
        self,
        tenant_id: str,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[AssessmentView, ...]:
        rows = await self._fetch(
            tenant_id,
            f"""
            SELECT {_ASSESSMENT_COLUMNS} FROM ccm_assessment_views
            WHERE tenant_id = $1 AND assessment_id > COALESCE($2, '')
            ORDER BY assessment_id ASC LIMIT $3
            """,
            cursor,
            limit,
        )
        return tuple(_model(AssessmentView, row) for row in rows)

    async def list_evidence(
        self,
        tenant_id: str,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[EvidenceReferenceView, ...]:
        rows = await self._fetch(
            tenant_id,
            f"""
            SELECT {_EVIDENCE_COLUMNS} FROM ccm_evidence_reference_views
            WHERE tenant_id = $1 AND reference_id > COALESCE($2, '')
            ORDER BY reference_id ASC LIMIT $3
            """,
            cursor,
            limit,
        )
        return tuple(_model(EvidenceReferenceView, row) for row in rows)

    async def list_cases(
        self,
        tenant_id: str,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[CaseView, ...]:
        rows = await self._fetch(
            tenant_id,
            f"""
            SELECT {_CASE_COLUMNS} FROM ccm_casework_views
            WHERE tenant_id = $1 AND case_id > COALESCE($2, '')
            ORDER BY case_id ASC LIMIT $3
            """,
            cursor,
            limit,
        )
        return tuple(_model(CaseView, row) for row in rows)

    async def get_case(self, tenant_id: str, case_id: str) -> CaseView | None:
        rows = await self._fetch(
            tenant_id,
            f"SELECT {_CASE_COLUMNS} FROM ccm_casework_views WHERE tenant_id = $1 AND case_id = $2",
            case_id,
        )
        return None if not rows else _model(CaseView, rows[0])

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
        async with self._pool_or_raise().acquire() as connection, connection.transaction():
            await connection.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)
            row = await connection.fetchrow(
                """
                UPDATE ccm_casework_views
                SET version = version + 1
                WHERE tenant_id = $1 AND case_id = $2 AND version = $3
                RETURNING version
                """,
                tenant_id,
                case_id,
                expected_version,
            )
            if row is None:
                exists = await connection.fetchval(
                    "SELECT 1 FROM ccm_casework_views WHERE tenant_id = $1 AND case_id = $2",
                    tenant_id,
                    case_id,
                )
                if exists is None:
                    raise KeyError(case_id)
                raise CaseConflictError(case_id)
            version = int(row["version"])
            update_id = f"work_update_{case_id}_{version}"
            await connection.execute(
                """
                INSERT INTO ccm_console_work_updates
                  (
                    tenant_id, update_id, case_id, actor_subject_id, message,
                    created_at, case_version
                  )
                VALUES ($1, $2, $3, $4, $5, $6::timestamptz, $7)
                """,
                tenant_id,
                update_id,
                case_id,
                actor_subject_id,
                message,
                created_at,
                version,
            )
            return WorkUpdateView(
                update_id=update_id,
                case_id=case_id,
                actor_subject_id=actor_subject_id,
                message=message,
                created_at=created_at,
                case_version=version,
            )

    async def reassign_owner(
        self,
        tenant_id: str,
        case_id: str,
        *,
        expected_version: int,
        owner_team: str,
        owner_subject_id: str | None,
    ) -> CaseView:
        async with self._pool_or_raise().acquire() as connection, connection.transaction():
            await connection.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)
            row = await connection.fetchrow(
                f"""
                UPDATE ccm_casework_views
                SET owner_team = $4, owner_subject_id = $5, version = version + 1
                WHERE tenant_id = $1 AND case_id = $2 AND version = $3
                RETURNING {_CASE_COLUMNS}
                """,
                tenant_id,
                case_id,
                expected_version,
                owner_team,
                owner_subject_id,
            )
            if row is not None:
                return _model(CaseView, row)
            if (
                await connection.fetchval(
                    "SELECT 1 FROM ccm_casework_views WHERE tenant_id = $1 AND case_id = $2",
                    tenant_id,
                    case_id,
                )
                is None
            ):
                raise KeyError(case_id)
            raise CaseConflictError(case_id)
