"""Fail closed if the ccm-console wheel omits API code or includes repository artifacts."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    wheels = sorted((ROOT / "dist").glob("ccm_console-*.whl"))
    if len(wheels) != 1:
        raise SystemExit("expected exactly one ccm_console wheel")
    with ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
    required = {
        "ccm_console/__init__.py",
        "ccm_console/app.py",
        "ccm_console/auth.py",
        "ccm_console/main.py",
        "ccm_console/models.py",
        "ccm_console/postgres.py",
        "ccm_console/repository.py",
    }
    missing = sorted(required - names)
    if missing:
        raise SystemExit(f"wheel missing expected files: {', '.join(missing)}")
    forbidden = sorted(
        name
        for name in names
        if name.startswith(("tests/", "fixtures/", "db/", "apps/web/", ".github/"))
    )
    if forbidden:
        raise SystemExit(f"wheel contains non-package artifacts: {', '.join(forbidden)}")
    print(f"VALID wheel={wheels[0].name} files={len(names)}")


if __name__ == "__main__":
    main()
