from __future__ import annotations

import asyncio
from typing import Any

import jwt
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from ccm_console import main
from ccm_console.auth import DevelopmentHmacTokenVerifier
from ccm_console.models import (
    AssessmentView,
    CaseState,
    CaseView,
    EvidenceReferenceView,
    Severity,
)
from ccm_console.postgres import AsyncpgConsoleRepository
from ccm_console.repository import CaseConflictError, MemoryConsoleRepository

SECRET = "adapter-test-secret-only-and-never-a-production-key"
ISSUER = "ccm-console-adapter-test"
AUDIENCE = "ccm-console-api"
HASH = "sha256:" + ("a" * 64)


class FakeTransaction:
    async def __aenter__(self) -> FakeTransaction:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


class FakeConnection:
    def __init__(
        self,
        *,
        rows: list[dict[str, Any]] | None = None,
        update_row: dict[str, Any] | None = None,
        exists: int | None = 1,
    ) -> None:
        self.rows = rows or []
        self.update_row = update_row
        self.exists = exists
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    async def execute(self, query: str, *arguments: object) -> str:
        self.executed.append((query, arguments))
        return "OK"

    async def fetch(self, _: str, *__: object) -> list[dict[str, Any]]:
        return self.rows

    async def fetchrow(self, _: str, *__: object) -> dict[str, Any] | None:
        return self.update_row

    async def fetchval(self, _: str, *__: object) -> int | None:
        return self.exists


class FakeAcquire:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> FakeConnection:
        return self.connection

    async def __aexit__(self, *_: object) -> None:
        return None


class FakePool:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self.closed = False

    def acquire(self) -> FakeAcquire:
        return FakeAcquire(self.connection)

    async def close(self) -> None:
        self.closed = True


def assessment_row() -> dict[str, Any]:
    return {
        "assessment_id": "assessment_alpha",
        "control_id": "identity_mfa_coverage",
        "control_version": "1.0.0",
        "status": "fail",
        "coverage": "partial",
        "severity": "high",
        "source_manifest_hash": HASH,
        "assessed_at": "2026-08-21T00:00:00Z",
    }


def evidence_row() -> dict[str, Any]:
    return {
        "reference_id": "reference_alpha",
        "evidence_id": "evidence_alpha",
        "evidence_hash": HASH,
        "collector_id": "collector_identity",
        "control_id": "identity_mfa_coverage",
        "observed_at": "2026-08-21T00:00:00Z",
        "availability": "complete",
        "source_manifest_hash": HASH,
    }


def case_row(version: int = 2) -> dict[str, Any]:
    return {
        "case_id": "case_alpha",
        "control_id": "identity_mfa_coverage",
        "control_version": "1.0.0",
        "state": "active",
        "severity": "high",
        "owner_team": "cloud_security",
        "owner_subject_id": None,
        "due_at": None,
        "source_case_manifest_hash": HASH,
        "version": version,
    }


def repository(connection: FakeConnection) -> AsyncpgConsoleRepository:
    result = AsyncpgConsoleRepository("postgresql://placeholder")
    result._pool = FakePool(connection)  # type: ignore[assignment]
    return result


def test_asyncpg_adapter_projects_safe_rows_and_sets_tenant_context() -> None:
    connection = FakeConnection(rows=[assessment_row()])
    result = asyncio.run(
        repository(connection).list_assessments("tenant_alpha", limit=10, cursor=None)
    )
    assert result[0].assessment_id == "assessment_alpha"
    assert connection.executed[0][1] == ("tenant_alpha",)
    connection.rows = [evidence_row()]
    evidence = asyncio.run(
        repository(connection).list_evidence("tenant_alpha", limit=10, cursor=None)
    )
    assert evidence[0].evidence_id == "evidence_alpha"
    connection.rows = [case_row()]
    cases = asyncio.run(repository(connection).list_cases("tenant_alpha", limit=10, cursor=None))
    assert cases[0].case_id == "case_alpha"
    single = asyncio.run(repository(connection).get_case("tenant_alpha", "case_alpha"))
    assert single is not None and single.version == 2
    connection.rows = []
    assert asyncio.run(repository(connection).get_case("tenant_alpha", "case_alpha")) is None


def test_asyncpg_adapter_updates_or_fails_closed_for_missing_and_stale_case() -> None:
    successful = FakeConnection(update_row={"version": 2})
    update = asyncio.run(
        repository(successful).append_update(
            "tenant_alpha",
            "case_alpha",
            actor_subject_id="subject_alex",
            expected_version=1,
            message="reviewed safe reference",
            created_at="2026-08-22T00:00:00Z",
        )
    )
    assert update.update_id == "work_update_case_alpha_2"
    assert any("INSERT INTO ccm_console_work_updates" in query for query, _ in successful.executed)
    with pytest.raises(KeyError):
        asyncio.run(
            repository(FakeConnection(update_row=None, exists=None)).append_update(
                "tenant_alpha",
                "case_alpha",
                actor_subject_id="subject_alex",
                expected_version=1,
                message="safe update",
                created_at="2026-08-22T00:00:00Z",
            )
        )
    with pytest.raises(CaseConflictError):
        asyncio.run(
            repository(FakeConnection(update_row=None, exists=1)).append_update(
                "tenant_alpha",
                "case_alpha",
                actor_subject_id="subject_alex",
                expected_version=1,
                message="safe update",
                created_at="2026-08-22T00:00:00Z",
            )
        )


def test_asyncpg_adapter_reassignment_and_lifecycle_without_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reassigned = asyncio.run(
        repository(FakeConnection(update_row=case_row(3))).reassign_owner(
            "tenant_alpha",
            "case_alpha",
            expected_version=2,
            owner_team="platform_operations",
            owner_subject_id=None,
        )
    )
    assert reassigned.version == 3
    with pytest.raises(KeyError):
        asyncio.run(
            repository(FakeConnection(update_row=None, exists=None)).reassign_owner(
                "tenant_alpha",
                "case_alpha",
                expected_version=2,
                owner_team="platform_operations",
                owner_subject_id=None,
            )
        )
    with pytest.raises(CaseConflictError):
        asyncio.run(
            repository(FakeConnection(update_row=None, exists=1)).reassign_owner(
                "tenant_alpha",
                "case_alpha",
                expected_version=2,
                owner_team="platform_operations",
                owner_subject_id=None,
            )
        )
    started_pool = FakePool(FakeConnection())

    async def create_pool(**_: object) -> FakePool:
        return started_pool

    monkeypatch.setattr("ccm_console.postgres.asyncpg.create_pool", create_pool)
    lifecycle = AsyncpgConsoleRepository("postgresql://placeholder")
    asyncio.run(lifecycle.startup())
    asyncio.run(lifecycle.shutdown())
    assert started_pool.closed
    with pytest.raises(RuntimeError):
        asyncio.run(lifecycle.get_case("tenant_alpha", "case_alpha"))


def test_memory_repository_missing_case_and_custom_update_identifier() -> None:
    case = CaseView(
        case_id="case_alpha",
        control_id="identity_mfa_coverage",
        control_version="1.0.0",
        state=CaseState.ACTIVE,
        severity=Severity.HIGH,
        owner_team="cloud_security",
        source_case_manifest_hash=HASH,
        version=1,
    )
    memory = MemoryConsoleRepository(
        cases=(("tenant_alpha", case),),
        update_id_factory=lambda _, __: "custom_update",
    )
    update = asyncio.run(
        memory.append_update(
            "tenant_alpha",
            "case_alpha",
            actor_subject_id="subject_alex",
            expected_version=1,
            message="safe update",
            created_at="2026-08-22T00:00:00Z",
        )
    )
    assert update.update_id == "custom_update"
    assert asyncio.run(memory.list_cases("tenant_alpha", limit=1, cursor="case_alpha")) == ()
    with pytest.raises(KeyError):
        asyncio.run(
            memory.append_update(
                "tenant_alpha",
                "case_missing",
                actor_subject_id="subject_alex",
                expected_version=1,
                message="safe update",
                created_at="2026-08-22T00:00:00Z",
            )
        )
    with pytest.raises(KeyError):
        asyncio.run(
            memory.reassign_owner(
                "tenant_alpha",
                "case_missing",
                expected_version=1,
                owner_team="platform_operations",
                owner_subject_id=None,
            )
        )


def test_development_verifier_rejects_malformed_claims_and_main_factory_uses_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = DevelopmentHmacTokenVerifier(
        secret=SECRET,
        issuer=ISSUER,
        audience=AUDIENCE,
        now_epoch=lambda: 100,
    )
    malformed = jwt.encode(
        {"iss": ISSUER, "aud": AUDIENCE, "sub": "subject_alex", "exp": 101},
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(Exception, match="invalid bearer token claims"):
        verifier.verify(malformed)
    for name in (
        "CCM_CONSOLE_DATABASE_URL",
        "CCM_CONSOLE_JWT_SECRET",
        "CCM_CONSOLE_JWT_ISSUER",
        "CCM_CONSOLE_JWT_AUDIENCE",
        "CCM_CONSOLE_ALLOWED_ORIGINS",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="CCM_CONSOLE_DATABASE_URL"):
        main.create_production_app()
    monkeypatch.setenv("CCM_CONSOLE_DATABASE_URL", "postgresql://placeholder")
    monkeypatch.setenv("CCM_CONSOLE_JWT_SECRET", SECRET)
    monkeypatch.setenv("CCM_CONSOLE_JWT_ISSUER", ISSUER)
    monkeypatch.setenv("CCM_CONSOLE_JWT_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("CCM_CONSOLE_ALLOWED_ORIGINS", "http://localhost:3000")
    app = main.create_production_app()
    assert app.title == "ccm-console API"
    captured: dict[str, object] = {}

    def run_stub(application: object, **kwargs: object) -> None:
        captured["application"] = application
        captured.update(kwargs)

    monkeypatch.setattr(main.uvicorn, "run", run_stub)
    main.run()
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 8000
    assert main._now_text().endswith("Z")
    assert main._now_epoch() > 0
    assert main._correlation_id().startswith("corr_")


def test_verifier_and_contracts_reject_malformed_tokens_and_hashes() -> None:
    with pytest.raises(ValueError, match="at least 32"):
        DevelopmentHmacTokenVerifier(
            secret="short",
            issuer=ISSUER,
            audience=AUDIENCE,
            now_epoch=lambda: 100,
        )
    verifier = DevelopmentHmacTokenVerifier(
        secret=SECRET,
        issuer=ISSUER,
        audience=AUDIENCE,
        now_epoch=lambda: 100,
    )
    with pytest.raises(HTTPException, match="invalid bearer token"):
        verifier.verify("not-a-token")
    with pytest.raises(ValidationError):
        AssessmentView.model_validate(
            {**assessment_row(), "source_manifest_hash": "bad"},
            strict=False,
        )
    with pytest.raises(ValidationError):
        EvidenceReferenceView.model_validate(
            {**evidence_row(), "evidence_hash": "bad"},
            strict=False,
        )
    with pytest.raises(ValidationError):
        CaseView.model_validate({**case_row(), "source_case_manifest_hash": "bad"}, strict=False)
