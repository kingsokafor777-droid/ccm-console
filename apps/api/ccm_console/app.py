"""FastAPI tenant/RBAC boundary for safe CCM console projections and coordination updates."""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import TokenVerifier, require_role
from .models import (
    ApiError,
    AssessmentPage,
    AssessmentStatus,
    CasePage,
    CaseView,
    CoverageStatus,
    EvidencePage,
    Overview,
    OwnerReassignment,
    Principal,
    Role,
    WorkUpdateCreate,
    WorkUpdateView,
)
from .repository import CaseConflictError, ConsoleRepository, is_open_case, severity_rank

MAX_PAGE_SIZE = 100
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class ConsoleApplication:
    repository: ConsoleRepository
    verifier: TokenVerifier
    now: Callable[[], str]
    correlation_id: Callable[[], str]
    allowed_origins: tuple[str, ...] = ()


def _next_cursor(items: tuple[object, ...], cursor: str | None, limit: int) -> str | None:
    if len(items) != limit:
        return None
    last = items[-1]
    for attr in ("assessment_id", "reference_id", "case_id"):
        value = getattr(last, attr, None)
        if isinstance(value, str) and value != cursor:
            return value
    return None


def _error(request: Request, code: str, detail: str, status_code: int) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    return JSONResponse(
        status_code=status_code,
        content=ApiError(
            code=code,
            correlation_id=correlation_id,
            detail=detail,
        ).model_dump(mode="json"),
    )


def create_app(
    configuration: ConsoleApplication,
    *,
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager[None]] | None = None,
) -> FastAPI:
    """Create an API app around injected identity, repository, clock, and correlation boundaries."""

    app = FastAPI(
        title="ccm-console API",
        version="0.1.2",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(configuration.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    )

    @app.middleware("http")
    async def attach_correlation_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        supplied = request.headers.get("X-Correlation-ID")
        request.state.correlation_id = supplied or configuration.correlation_id()
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        return response

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "request rejected"
        code = "unauthorized" if exc.status_code == status.HTTP_401_UNAUTHORIZED else "forbidden"
        if exc.status_code not in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
            code = "request_rejected"
        return _error(request, code, detail, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, _: RequestValidationError) -> JSONResponse:
        return _error(
            request,
            "invalid_request",
            "request validation failed",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    async def current_principal(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    ) -> Principal:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return configuration.verifier.verify(credentials.credentials)

    def authorized(*roles: Role) -> Callable[..., object]:
        async def dependency(
            principal: Annotated[Principal, Depends(current_principal)],
        ) -> Principal:
            return require_role(principal, *roles)

        return dependency

    viewer = authorized(Role.VIEWER, Role.OPERATOR, Role.REVIEWER, Role.ADMIN)
    operator = authorized(Role.OPERATOR, Role.REVIEWER, Role.ADMIN)
    reviewer = authorized(Role.REVIEWER, Role.ADMIN)

    @app.get("/healthz", response_model=dict[str, str], tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ready", "storage": "not_checked"}

    @app.get("/v1/overview", response_model=Overview, tags=["console"])
    async def overview(principal: Annotated[Principal, Depends(viewer)]) -> Overview:
        assessments = await configuration.repository.list_assessments(
            principal.tenant_id,
            limit=MAX_PAGE_SIZE,
            cursor=None,
        )
        evidence = await configuration.repository.list_evidence(
            principal.tenant_id,
            limit=MAX_PAGE_SIZE,
            cursor=None,
        )
        cases = await configuration.repository.list_cases(
            principal.tenant_id,
            limit=MAX_PAGE_SIZE,
            cursor=None,
        )
        open_cases = tuple(case for case in cases if is_open_case(case))
        highest = max(open_cases, key=lambda case: severity_rank(case.severity.value), default=None)
        return Overview(
            assessment_count=len(assessments),
            case_count=len(cases),
            open_case_count=len(open_cases),
            failing_assessment_count=sum(
                item.status == AssessmentStatus.FAIL for item in assessments
            ),
            partial_coverage_count=sum(
                item.coverage == CoverageStatus.PARTIAL for item in assessments
            ),
            unavailable_evidence_count=sum(
                item.availability == CoverageStatus.UNAVAILABLE for item in evidence
            ),
            highest_open_severity=None if highest is None else highest.severity,
            generated_at=configuration.now(),
        )

    @app.get("/v1/assessments", response_model=AssessmentPage, tags=["assessments"])
    async def list_assessments(
        principal: Annotated[Principal, Depends(viewer)],
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 50,
        cursor: str | None = None,
    ) -> AssessmentPage:
        items = await configuration.repository.list_assessments(
            principal.tenant_id,
            limit=limit,
            cursor=cursor,
        )
        return AssessmentPage(items=items, next_cursor=_next_cursor(items, cursor, limit))

    @app.get("/v1/evidence", response_model=EvidencePage, tags=["evidence"])
    async def list_evidence(
        principal: Annotated[Principal, Depends(viewer)],
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 50,
        cursor: str | None = None,
    ) -> EvidencePage:
        items = await configuration.repository.list_evidence(
            principal.tenant_id,
            limit=limit,
            cursor=cursor,
        )
        return EvidencePage(items=items, next_cursor=_next_cursor(items, cursor, limit))

    @app.get("/v1/cases", response_model=CasePage, tags=["casework"])
    async def list_cases(
        principal: Annotated[Principal, Depends(viewer)],
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 50,
        cursor: str | None = None,
    ) -> CasePage:
        items = await configuration.repository.list_cases(
            principal.tenant_id,
            limit=limit,
            cursor=cursor,
        )
        return CasePage(items=items, next_cursor=_next_cursor(items, cursor, limit))

    @app.get("/v1/cases/{case_id}", response_model=CaseView, tags=["casework"])
    async def get_case(
        case_id: str,
        principal: Annotated[Principal, Depends(viewer)],
    ) -> CaseView:
        case = await configuration.repository.get_case(principal.tenant_id, case_id)
        if case is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="case not found")
        return case

    @app.post(
        "/v1/cases/{case_id}/updates",
        response_model=WorkUpdateView,
        status_code=status.HTTP_201_CREATED,
        tags=["casework"],
    )
    async def append_update(
        case_id: str,
        command: WorkUpdateCreate,
        principal: Annotated[Principal, Depends(operator)],
    ) -> WorkUpdateView:
        try:
            return await configuration.repository.append_update(
                principal.tenant_id,
                case_id,
                actor_subject_id=principal.subject_id,
                expected_version=command.expected_version,
                message=command.message,
                created_at=configuration.now(),
            )
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="case not found",
            ) from exc
        except CaseConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="stale case version",
            ) from exc

    @app.patch("/v1/cases/{case_id}/owner", response_model=CaseView, tags=["casework"])
    async def reassign_owner(
        case_id: str,
        command: OwnerReassignment,
        principal: Annotated[Principal, Depends(reviewer)],
    ) -> CaseView:
        try:
            return await configuration.repository.reassign_owner(
                principal.tenant_id,
                case_id,
                expected_version=command.expected_version,
                owner_team=command.owner_team,
                owner_subject_id=command.owner_subject_id,
            )
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="case not found",
            ) from exc
        except CaseConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="stale case version",
            ) from exc

    return app
