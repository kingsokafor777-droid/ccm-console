# ccm-console architecture and security contract

## 1. Deployment posture

ccm-console is a **repository-delivered full-stack application**, not a deployed service.
The source includes a FastAPI API contract, an RLS-ready PostgreSQL migration, a Next.js
client, deterministic synthetic fixtures, and local test harnesses. It does not start a
database in tests, run a worker, schedule escalations, or require a persistent Manus
runtime. A deployer selects and operates the runtime, database, identity provider, TLS,
secrets, monitoring, backups, and incident response.

## 2. Trust boundaries

| Boundary | Input | Enforcement | Residual responsibility |
|---|---|---|---|
| Browser to API | Bearer token and typed request | CORS allowlist, request-size bounds, bearer-token verification, tenant/role dependency, response models. | Deploy TLS, CSP, secure cookies if used, rate limits, and an external identity provider. |
| API to PostgreSQL | Tenant ID and parameterized commands | `SET LOCAL app.tenant_id`, RLS policies, explicit selected columns, bounded pagination, application role checks. | Deploy a least-privilege role, migration process, backup/recovery, connection TLS, and tenant onboarding policy. |
| Console to CCM records | Versioned safe assessment/evidence/case projections | Hash fields and source-manifest references are displayed as supplied; raw payload columns do not exist in the console schema. | Verify source artifacts through ccm-core/ledger/assessor/casework/audit-export contracts. |
| Workbench mutation | Case ID, expected version, structured update | Operator/reviewer role checks, tenant predicate, optimistic version check, append-only update audit row. | Route authoritative remediation, exception, and closure transitions through ccm-casework under approved organizational controls. |

## 3. RBAC matrix

| Role | Overview / evidence | Case view | Add work update | Reassign owner | Tenant administration |
|---|---:|---:|---:|---:|---:|
| `viewer` | Yes | Yes | No | No | No |
| `operator` | Yes | Yes | Yes | No | No |
| `reviewer` | Yes | Yes | Yes | Yes | No |
| `admin` | Yes | Yes | Yes | Yes | Not exposed in v0.1.0 |

The role is a policy claim, not an approver-authority proof. Any caller without a valid
tenant claim receives a deny response. The API never accepts a tenant ID from a request
body or path as an authorization substitute; its tenant predicate comes from the verified
identity context.

## 4. Data model

The migration creates tenant-scoped **read-model** tables for assessments, evidence
references, cases, and workbench updates. Each contains safe identifiers, status fields,
timestamps, hash references, and source-manifest links only. No raw cloud responses,
attachments, credentials, access tokens, screenshots, or evidence bodies are stored.

`ccm_casework_views` mirrors supplied casework state for viewing. Console work updates are
coordination records, not `ccm-casework` action events; they neither approve an exception
nor verify closure. `expected_version` prevents a stale workbench client from overwriting
the currently viewed case state.

## 5. API contract

| Route | Minimum role | Contract |
|---|---|---|
| `GET /healthz` | Public | Bounded service readiness metadata only; no database claim. |
| `GET /v1/overview` | `viewer` | Tenant-scoped transparent count rollup. |
| `GET /v1/assessments` | `viewer` | Bounded list of supplied assessment projections. |
| `GET /v1/evidence` | `viewer` | Bounded list of payload-blind evidence references. |
| `GET /v1/cases` and `GET /v1/cases/{id}` | `viewer` | Tenant-scoped workbench case projection. |
| `POST /v1/cases/{id}/updates` | `operator` | Structured coordination update; no exception decision, case closure, or remediation execution. |
| `PATCH /v1/cases/{id}/owner` | `reviewer` | Reassigns the coordination owner only, subject to optimistic version. |

All pagination has a fixed maximum. Query ordering is stable. API errors use generic
messages, include a correlation ID, and do not echo tokens, raw payloads, database
connection details, or unbounded validation traces.

## 6. Failure rules

The API fails closed for missing/malformed/expired token claims, unknown roles, tenant
mismatch, forbidden function, unknown case, invalid page bounds, stale version, and
database-unavailable repository. A missing assessment/evidence/case returns an explicit
absence—not a pass or a closure. The dashboard renders neutral coverage and data-source
states rather than infering technical control effectiveness.

## 7. Minimal test cases

The suite validates cross-tenant denial, viewer/operator/reviewer function separation,
object-level case isolation, bounded pagination, stale-version conflict, safe response
shape, expired/malformed tokens, deterministic overview sorting/counts, and frontend
rendering of unavailable evidence/partial coverage states. Tests use a fixed clock, an
in-memory repository, synthetic references, and no PostgreSQL server or network.

## 8. Non-negotiable rules

1. No raw evidence payload, credential, cloud API response, customer data, or real identity fixture enters the repository.
2. No route may query or mutate another tenant’s data, even when a client-controlled ID matches an existing record.
3. No console workbench operation may assert compliance, authorize risk, approve an exception, verify closure, or execute remediation.
4. The production deployment must replace the local HMAC token adapter with a vetted external OIDC/JWT verification configuration.
5. PostgreSQL RLS and application tenant filtering are defense-in-depth; neither is a substitute for external identity governance.
