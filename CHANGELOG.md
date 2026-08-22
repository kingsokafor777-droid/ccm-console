# Changelog

## 0.1.2 — hosted workspace bootstrap repair

The hosted Node jobs now invoke Corepack-managed pnpm from `apps/web`, where the pinned
package-manager metadata is visible. This release contains no product-surface, persistence,
authorization, evidence, or workflow semantic change.

## 0.1.1 — hosted CI bootstrap repair

The hosted Node jobs now enable Corepack-managed pnpm before frontend installation. This
release contains no product-surface, persistence, authorization, evidence, or workflow
semantic change.

## 0.1.0 — initial release

- Add tenant-scoped FastAPI API contracts, a PostgreSQL RLS-ready read/workbench schema,
  bearer identity adapter boundary, and structured role checks.
- Add a Next.js/React executive overview, evidence explorer, and remediation workbench
  over deterministic synthetic data.
- Add strict API/frontend tests, fixtures, migration validation, wheel verification, and
  immutable-pinned CI/CodeQL workflows.
