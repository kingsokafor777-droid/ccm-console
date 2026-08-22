.PHONY: fixtures api-quality web-quality quality package-check

fixtures:
	PYTHONPATH=apps/api python scripts/build_fixtures.py

api-quality:
	PYTHONPATH=apps/api ruff check apps/api tests/api scripts
	PYTHONPATH=apps/api ruff format --check apps/api tests/api scripts
	PYTHONPATH=apps/api mypy apps/api
	PYTHONPATH=apps/api pytest

web-quality:
	cd apps/web && pnpm lint
	cd apps/web && pnpm typecheck
	cd apps/web && pnpm test
	cd apps/web && NODE_ENV=production pnpm build

quality: api-quality web-quality

package-check:
	python3 -m pip wheel --no-deps --wheel-dir dist .
	python3 scripts/check_package.py
