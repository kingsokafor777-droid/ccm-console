"""Lightweight fail-closed structural check for the reviewed ccm-console PostgreSQL migration."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "db" / "migrations" / "0001_console.sql"


def main() -> None:
    content = MIGRATION.read_text(encoding="utf-8")
    required = (
        "BEGIN;",
        "COMMIT;",
        "ENABLE ROW LEVEL SECURITY",
        "FORCE ROW LEVEL SECURITY",
        "current_setting('app.tenant_id', true)",
        "ccm_console_work_updates are append-only",
        "ccm_assessment_views",
        "ccm_evidence_reference_views",
        "ccm_casework_views",
    )
    missing = [value for value in required if value not in content]
    if missing:
        raise SystemExit(f"migration is missing required protections: {', '.join(missing)}")
    forbidden = ("raw_payload", "credential", "password", "access_token")
    present = [value for value in forbidden if value in content]
    if present:
        raise SystemExit(f"migration contains forbidden sensitive columns: {', '.join(present)}")
    print("VALID migration=0001_console.sql tenant_rls=enabled raw_evidence=absent")


if __name__ == "__main__":
    main()
