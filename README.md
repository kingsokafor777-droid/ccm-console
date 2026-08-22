# ccm-console

`ccm-console` is the **product-facing boundary** for the Continuous Control Monitoring
(CCM) program. It provides a tenant-scoped FastAPI API, PostgreSQL read/workbench model,
and a Next.js/React executive interface for technical assessment posture, evidence
references, and remediation work coordination.

> **Scope boundary:** ccm-console is an application boundary and review workbench. It
> does not collect cloud data, retain raw evidence bodies, authenticate external identity
> providers by itself, validate approver authority, authorize risk, execute remediation,
> schedule escalation, issue audit opinions, certify compliance, or determine framework
> conformance.

NIST frames continuous monitoring as visibility into assets, threats, vulnerabilities,
and control effectiveness for timely risk response, while the RMF places monitoring,
assessment, and authorization in an organizational process.[1][2] ccm-console renders
supplied technical records and operator work coordination; it does not replace those
organizational decisions. OWASP highlights object-level and function-level authorization
as distinct API risks, so every tenant-bearing access path is designed to require both a
verified tenant claim and a role decision.[3]

## Product surfaces

| Surface | What it provides | What it does not imply |
|---|---|---|
| **Executive overview** | Transparent counts for supplied assessments, evidence coverage, severity, and case state. | Enterprise risk acceptance or compliance status. |
| **Evidence explorer** | Tenant-scoped reference metadata, hashes, collection provenance, and source links. | Access to raw evidence payloads, screenshots, credentials, or source systems. |
| **Remediation workbench** | Assigned owner, due-date, priority, lifecycle view, and append-only console work updates. | Closure verification, exception authorization, or remediation execution. |
| **API boundary** | FastAPI/OpenAPI contracts, PostgreSQL RLS-ready queries, bounded filters/pagination, correlation IDs, and role checks. | A complete identity provider or database deployment. |

## Architecture

```text
OIDC / trusted identity provider
          │ signed identity claims
          ▼
FastAPI API ── tenant + role dependency ── PostgreSQL CCM read/workbench schema
          │                                      │
          └── JSON contracts ── Next.js / React ──┘
```

The runtime design requires an external identity deployment strategy. The source includes
a deterministic HMAC token adapter **only for local development and tests**. A production
deployer must configure validated OIDC/JWT verification, TLS, secrets management, a
least-privilege database role, RLS policy, backups, observability, rate limits, CORS
origins, and database migrations. This repository contains no production database,
cloud account, identity tenant, or hosted-service claim.

## Local development

```bash
python -m pip install -e . -r requirements-dev.txt
pnpm --dir apps/web install --frozen-lockfile

PYTHONPATH=apps/api python scripts/build_fixtures.py
make quality
make package-check
```

Copy `.env.example` to `.env` only for local development and replace placeholder values
outside version control. The integration suite uses an in-memory repository and a fixed
clock; it neither starts PostgreSQL nor requires a network connection. The migration is
provided for deployers to review and apply through their own controlled PostgreSQL change
process.

## Release posture

The repository requires strict Python and TypeScript checks, deterministic fixtures,
backend authorization tests, frontend component tests, immutable-pinned CI/CodeQL, and
wheel-content validation. See [`docs/architecture.md`](docs/architecture.md),
[`CONTRIBUTING.md`](CONTRIBUTING.md), and [`SECURITY.md`](SECURITY.md).

## References

[1] [NIST SP 800-137 — Information Security Continuous Monitoring](https://csrc.nist.gov/pubs/sp/800/137/final)

[2] [NIST SP 800-37 Rev. 2 — Risk Management Framework](https://csrc.nist.gov/pubs/sp/800/37/r2/final)

[3] [OWASP API Security Project — API Security Top 10](https://owasp.org/www-project-api-security/)
