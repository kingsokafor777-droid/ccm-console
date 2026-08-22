.PHONY: fixtures api-quality web-quality quality package-check

fixtures:
	PYTHONPATH=apps/api python scripts/build_fixtures.py

api-quality:
	PYTHONPATH=apps/api ruff check apps/api tests/api scripts
	PYTHONPATH=apps/api ruff format --check apps/api tests/api scripts
	PYTHONPATH=apps/api mypy apps/api
	PYTHONPATH=apps/api pytest

web-quality:
	pnpm --dir apps/web lint
	pnpm --dir apps/web typecheck
	pnpm --dir apps/web test
	NODE_ENV=production pnpm --dir apps/web build

quality: api-quality web-quality

package-check:
	python3 -m pip wheel --no-deps --wheel-dir dist .
	python3 scripts/check_package.py
