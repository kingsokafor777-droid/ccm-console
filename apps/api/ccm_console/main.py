"""Environment-driven FastAPI runtime factory for a deployer-controlled ccm-console service."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI

from .app import ConsoleApplication, create_app
from .auth import DevelopmentHmacTokenVerifier
from .postgres import AsyncpgConsoleRepository


def _now_epoch() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _correlation_id() -> str:
    return f"corr_{uuid.uuid4().hex}"


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def create_production_app() -> FastAPI:
    """Build the app around a PostgreSQL adapter; external identity deployment remains required."""

    repository = AsyncpgConsoleRepository(_required("CCM_CONSOLE_DATABASE_URL"))
    verifier = DevelopmentHmacTokenVerifier(
        secret=_required("CCM_CONSOLE_JWT_SECRET"),
        issuer=_required("CCM_CONSOLE_JWT_ISSUER"),
        audience=_required("CCM_CONSOLE_JWT_AUDIENCE"),
        now_epoch=_now_epoch,
    )
    origins = tuple(
        value.strip()
        for value in _required("CCM_CONSOLE_ALLOWED_ORIGINS").split(",")
        if value.strip()
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await repository.startup()
        try:
            yield
        finally:
            await repository.shutdown()

    return create_app(
        ConsoleApplication(
            repository=repository,
            verifier=verifier,
            now=_now_text,
            correlation_id=_correlation_id,
            allowed_origins=origins,
        ),
        lifespan=lifespan,
    )


def run() -> None:
    uvicorn.run(create_production_app(), host="0.0.0.0", port=8000, proxy_headers=True)
